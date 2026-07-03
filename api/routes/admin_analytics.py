"""
Admin Analytics dashboard — hybrid Mixpanel + our own SQLite.

Data-source policy (explicit per the spec):
  • Mixpanel Query API  → signups-over-time line, top events, retention.
  • Our SQLite (always available, free) → families total, sync adoption %,
    synced-vs-manual split, problem-report / feature-idea counts, and the whole
    activation funnel (every step is reliably derivable from our tables).
The dashboard NEVER 500s because Mixpanel is down: Mixpanel-sourced cards return
{available: false, reason} and the DB cards always render.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends

from api.database import get_conn
from api.services import mixpanel_client
from api.services.admin_auth import require_admin

router = APIRouter()


def _iso_days_ago(days: int) -> str:
    return (datetime.utcnow() - timedelta(days=days)).isoformat()


def _scalar(conn, sql: str, params=()) -> int:
    row = conn.execute(sql, params).fetchone()
    return (row[0] or 0) if row else 0


# ── Overview ─────────────────────────────────────────────────────────────────
@router.get("/analytics/overview")
def overview(days: int = 30, force: bool = False, _: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        since_30 = _iso_days_ago(days)
        since_7 = _iso_days_ago(7)

        families_total = _scalar(conn, "SELECT COUNT(*) FROM parents")
        signups_window = _scalar(
            conn, "SELECT COUNT(*) FROM parents WHERE created_at >= ?", (since_30,))

        athletes_total = _scalar(conn, "SELECT COUNT(*) FROM athletes")
        athletes_connected = _scalar(
            conn,
            "SELECT COUNT(*) FROM athletes WHERE byga_ics_url IS NOT NULL OR playmetrics_ics_url IS NOT NULL")
        sync_pct = round(100 * athletes_connected / athletes_total) if athletes_total else 0

        # DB-derived active users (7d): distinct athletes with any activity.
        active_7d = _scalar(conn, """
            SELECT COUNT(DISTINCT athlete_id) FROM (
                SELECT athlete_id FROM meal_logs   WHERE logged_at  >= ?
                UNION SELECT athlete_id FROM window_logs WHERE created_at >= ?
                UNION SELECT athlete_id FROM water_logs  WHERE updated_at >= ?
            )""", (since_7, since_7, since_7))

        # Signups-over-time from DB (daily). substr() gets the date part for both
        # ISO ('...T...') and CURRENT_TIMESTAMP ('... ...') formats.
        rows = conn.execute(
            "SELECT substr(created_at,1,10) AS d, COUNT(*) AS n FROM parents "
            "WHERE created_at >= ? GROUP BY d ORDER BY d", (since_30,)).fetchall()
        db_signup_series = [{"date": r["d"], "count": r["n"]} for r in rows]

        # App health
        problem_7d = _scalar(conn, "SELECT COUNT(*) FROM problem_reports WHERE created_at >= ?", (since_7,)) \
            if _table_exists(conn, "problem_reports") else 0
        ideas_7d = _scalar(conn, "SELECT COUNT(*) FROM feature_requests WHERE submitted_at >= ?", (since_7,)) \
            if _table_exists(conn, "feature_requests") else 0
        src_rows = conn.execute(
            "SELECT COALESCE(source,'manual') AS s, COUNT(*) AS n FROM events GROUP BY s").fetchall()
        event_sources = {r["s"]: r["n"] for r in src_rows}

        # Mixpanel enrichment (optional)
        mp_signups = mixpanel_client.signups_over_time(days, force=force)

        return {
            "as_of": datetime.utcnow().isoformat() + "Z",
            "mixpanel_available": mixpanel_client.is_configured(),
            "cards": {
                "signups": {"value": signups_window, "window_days": days, "source": "db"},
                "active_users_7d": {"value": active_7d, "source": "db"},
                "families_total": {"value": families_total, "source": "db"},
                "sync_adoption": {
                    "percent": sync_pct, "connected": athletes_connected,
                    "total": athletes_total, "source": "db",
                },
            },
            "signups_over_time": {
                "source": "db",
                "points": db_signup_series,
                "mixpanel": mp_signups,  # {available, data|reason}
            },
            "app_health": {
                "problem_reports_7d": problem_7d,
                "feature_ideas_7d": ideas_7d,
                "event_sources": event_sources,
            },
        }
    finally:
        conn.close()


# ── Activation funnel (DB-derived, always available) ─────────────────────────
@router.get("/analytics/funnel")
def funnel(days: int = 30, _: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        signed_up = _scalar(conn, "SELECT COUNT(*) FROM parents")
        created_athlete = _scalar(
            conn, "SELECT COUNT(DISTINCT parent_id) FROM athletes")
        connected_calendar = _scalar(conn, """
            SELECT COUNT(DISTINCT parent_id) FROM athletes
            WHERE byga_ics_url IS NOT NULL OR playmetrics_ics_url IS NOT NULL""")
        # "Built a meal plan" — parents with an athlete that has any meal-plan row.
        planned = _scalar(conn, """
            SELECT COUNT(DISTINCT a.parent_id) FROM athletes a
            WHERE EXISTS(SELECT 1 FROM meal_plans mp WHERE mp.athlete_id = a.id)
               OR EXISTS(SELECT 1 FROM meal_plan_selections ms WHERE ms.athlete_id = a.id)""")

        def step(label, value, prev):
            return {
                "label": label, "value": value,
                "pct_of_start": round(100 * value / signed_up) if signed_up else 0,
                "pct_of_prev": round(100 * value / prev) if prev else 0,
            }

        steps = [
            step("Signed up", signed_up, signed_up),
            step("Created athlete", created_athlete, signed_up),
            step("Connected calendar", connected_calendar, created_athlete),
            step("Built meal plan", planned, connected_calendar),
        ]
        return {"source": "db", "steps": steps,
                "note": "All steps derived from our database (most reliable). "
                        "Mixpanel event counts can refine these once event names are mapped."}
    finally:
        conn.close()


# ── Retention (Mixpanel, with DB WAU fallback) ───────────────────────────────
@router.get("/analytics/retention")
def retention(weeks: int = 8, force: bool = False, _: bool = Depends(require_admin)):
    weeks = max(1, min(12, weeks))
    mp = mixpanel_client.retention(weeks, force=force)
    if mp.get("available"):
        return {"source": "mixpanel", **mp}

    # Fallback: weekly-active-users trend from our DB.
    conn = get_conn()
    try:
        points = []
        for w in range(weeks - 1, -1, -1):
            start = _iso_days_ago((w + 1) * 7)
            end = _iso_days_ago(w * 7)
            wau = _scalar(conn, """
                SELECT COUNT(DISTINCT athlete_id) FROM (
                    SELECT athlete_id FROM meal_logs   WHERE logged_at  >= ? AND logged_at  < ?
                    UNION SELECT athlete_id FROM window_logs WHERE created_at >= ? AND created_at < ?
                    UNION SELECT athlete_id FROM water_logs  WHERE updated_at >= ? AND updated_at < ?
                )""", (start, end, start, end, start, end))
            points.append({"week_start": start[:10], "active": wau})
        return {"source": "db_wau_fallback", "available": True,
                "reason": mp.get("reason"), "points": points,
                "note": "Mixpanel retention unavailable — showing DB weekly-active-users trend instead."}
    finally:
        conn.close()


# ── Top events (Mixpanel only) ───────────────────────────────────────────────
@router.get("/analytics/events")
def top_events(days: int = 30, force: bool = False, _: bool = Depends(require_admin)):
    return mixpanel_client.top_events(days, force=force)


# ── Event-name discovery (run once after setting the Mixpanel secret) ─────────
@router.get("/analytics/discover")
def discover(force: bool = False, _: bool = Depends(require_admin)):
    return {
        "discovered": mixpanel_client.discover_event_names(force=force),
        "current_event_map": mixpanel_client.EVENT_MAP,
        "how_to_adjust": "Edit EVENT_MAP at the top of api/services/mixpanel_client.py "
                         "to match the discovered event names.",
    }


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None
