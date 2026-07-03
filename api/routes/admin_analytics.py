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


def _active_where(conn) -> str:
    """WHERE fragment (on the parents table) that excludes anonymized tombstones
    from the old FuelUp-Admin soft-delete. account_status only exists in prod, so
    this is '1=1' (no-op) on fresh/test DBs."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(parents)").fetchall()]
    return "(account_status IS NULL OR account_status != 'hard_deleted')" if "account_status" in cols else "1=1"


# ── Overview ─────────────────────────────────────────────────────────────────
@router.get("/analytics/overview")
def overview(days: int = 30, force: bool = False, _: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        since_30 = _iso_days_ago(days)
        since_7 = _iso_days_ago(7)

        aw = _active_where(conn)                          # excludes deleted parents
        active_ids = f"SELECT id FROM parents WHERE {aw}"
        active_athletes = f"SELECT id FROM athletes WHERE parent_id IN ({active_ids})"

        families_total = _scalar(conn, f"SELECT COUNT(*) FROM parents WHERE {aw}")
        signups_window = _scalar(
            conn, f"SELECT COUNT(*) FROM parents WHERE created_at >= ? AND {aw}", (since_30,))

        athletes_total = _scalar(conn, f"SELECT COUNT(*) FROM athletes WHERE parent_id IN ({active_ids})")
        athletes_connected = _scalar(
            conn,
            f"SELECT COUNT(*) FROM athletes WHERE (byga_ics_url IS NOT NULL OR playmetrics_ics_url IS NOT NULL) "
            f"AND parent_id IN ({active_ids})")
        sync_pct = round(100 * athletes_connected / athletes_total) if athletes_total else 0

        # DB-derived active users (7d): distinct athletes (of active families) with any activity.
        active_7d = _scalar(conn, f"""
            SELECT COUNT(DISTINCT athlete_id) FROM (
                SELECT athlete_id FROM meal_logs   WHERE logged_at  >= ?
                UNION SELECT athlete_id FROM window_logs WHERE created_at >= ?
                UNION SELECT athlete_id FROM water_logs  WHERE updated_at >= ?
            ) WHERE athlete_id IN ({active_athletes})""", (since_7, since_7, since_7))

        # Signups-over-time from DB (daily). substr() gets the date part for both
        # ISO ('...T...') and CURRENT_TIMESTAMP ('... ...') formats.
        rows = conn.execute(
            f"SELECT substr(created_at,1,10) AS d, COUNT(*) AS n FROM parents "
            f"WHERE created_at >= ? AND {aw} GROUP BY d ORDER BY d", (since_30,)).fetchall()
        db_signup_series = [{"date": r["d"], "count": r["n"]} for r in rows]

        # App health
        problem_7d = _scalar(conn, "SELECT COUNT(*) FROM problem_reports WHERE created_at >= ?", (since_7,)) \
            if _table_exists(conn, "problem_reports") else 0
        ideas_7d = _scalar(conn, "SELECT COUNT(*) FROM feature_requests WHERE submitted_at >= ?", (since_7,)) \
            if _table_exists(conn, "feature_requests") else 0
        src_rows = conn.execute(
            "SELECT COALESCE(source,'manual') AS s, COUNT(*) AS n FROM events GROUP BY s").fetchall()
        event_sources = {r["s"]: r["n"] for r in src_rows}

        # Mixpanel enrichment (optional). One probe query tells us whether the
        # Query API is actually usable (creds valid AND plan allows it).
        mp_signups = mixpanel_client.signups_over_time(days, force=force)
        mp_status = {
            "configured": mixpanel_client.is_configured(),
            "available": bool(mp_signups.get("available")),
            "plan_gated": bool(mp_signups.get("plan_gated")),
            "reason": mp_signups.get("reason"),
        }

        return {
            "as_of": datetime.utcnow().isoformat() + "Z",
            # True only when Mixpanel is configured AND the Query API actually works.
            "mixpanel_available": mp_status["available"],
            "mixpanel_status": mp_status,
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
        aw = _active_where(conn)
        active_ids = f"SELECT id FROM parents WHERE {aw}"

        signed_up = _scalar(conn, f"SELECT COUNT(*) FROM parents WHERE {aw}")
        created_athlete = _scalar(
            conn, f"SELECT COUNT(DISTINCT parent_id) FROM athletes WHERE parent_id IN ({active_ids})")
        # "Connected calendar" = auto-sync URL OR a one-time uploaded .ics file
        # (imported events carry a uid). Matches the Users-page calendar badge, so
        # families who uploaded a file aren't shown as 0.
        connected_calendar = _scalar(conn, f"""
            SELECT COUNT(DISTINCT a.parent_id) FROM athletes a
            WHERE a.parent_id IN ({active_ids})
              AND (a.byga_ics_url IS NOT NULL OR a.playmetrics_ics_url IS NOT NULL
                OR EXISTS(SELECT 1 FROM events e WHERE e.athlete_id = a.id AND e.uid IS NOT NULL AND e.uid != ''))""")
        # "Built a meal plan" — active parents with an athlete that has any meal-plan row.
        planned = _scalar(conn, f"""
            SELECT COUNT(DISTINCT a.parent_id) FROM athletes a
            WHERE a.parent_id IN ({active_ids})
              AND (EXISTS(SELECT 1 FROM meal_plans mp WHERE mp.athlete_id = a.id)
                OR EXISTS(SELECT 1 FROM meal_plan_selections ms WHERE ms.athlete_id = a.id))""")

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

    # Fallback: weekly-active-users trend from our DB (active families only).
    conn = get_conn()
    try:
        active_athletes = f"SELECT id FROM athletes WHERE parent_id IN (SELECT id FROM parents WHERE {_active_where(conn)})"
        points = []
        for w in range(weeks - 1, -1, -1):
            start = _iso_days_ago((w + 1) * 7)
            end = _iso_days_ago(w * 7)
            wau = _scalar(conn, f"""
                SELECT COUNT(DISTINCT athlete_id) FROM (
                    SELECT athlete_id FROM meal_logs   WHERE logged_at  >= ? AND logged_at  < ?
                    UNION SELECT athlete_id FROM window_logs WHERE created_at >= ? AND created_at < ?
                    UNION SELECT athlete_id FROM water_logs  WHERE updated_at >= ? AND updated_at < ?
                ) WHERE athlete_id IN ({active_athletes})""", (start, end, start, end, start, end))
            points.append({"week_start": start[:10], "active": wau})
        note = ("Retention cohorts require a Mixpanel paid plan — showing weekly active users instead."
                if mp.get("plan_gated") else
                "Mixpanel retention unavailable — showing DB weekly-active-users trend instead.")
        return {"source": "db_wau_fallback", "available": True,
                "reason": mp.get("reason"), "plan_gated": bool(mp.get("plan_gated")),
                "points": points, "note": note}
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
