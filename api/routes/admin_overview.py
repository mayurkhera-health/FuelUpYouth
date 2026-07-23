"""
Plain-language status for a non-technical team member reporting hourly.

Answers "is everything OK, and what are today's numbers" in one screen, zero
jargon. This is a PRESENTATION layer only — it reuses the exact same data
sources as the technical pages (no second source of truth):
  • overall health  → health_service.get_health_snapshot (same aggregate the
                      System Health page's banner uses)
  • families / active / calendar / meal-plan / problems / ideas
                    → admin_analytics.db_metrics + funnel_steps (same queries
                      behind the Analytics stat cards + activation funnel)

All the wording lives here (server-side), so the phrasing exists in one place —
including a paste-ready report_body for the "Copy report for founder" button.
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from api.database import get_conn
from api.routes.admin_analytics import db_metrics, funnel_steps
from api.services import health_service
from api.services.admin_auth import require_admin

router = APIRouter()

# ── Warning thresholds (tune here) ───────────────────────────────────────────
# ⚠️ when athletes active in the last 7 days is at or below this AND families exist.
# 0 = flag only when literally nobody has been active.
ACTIVE_USERS_WARN_AT_OR_BELOW = 0
# ⚠️ when the share of families who connected a calendar is below this fraction.
CALENDAR_WARN_BELOW_RATE = 0.50

# Plain, non-technical name for each health check (bedrock ping+inference collapse
# to one concept). Used only to name a red check in human terms.
HEALTH_PLAIN = {
    "bedrock_ping": "the AI coach",
    "kimi_inference": "the AI coach",
    "gmail_smtp": "email sending",
    "db_writable": "the app database",
    "disk_space": "storage space",
    "scheduler_notifications": "reminder notifications",
    "scheduler_calendar_sync": "calendar syncing",
    "calendar_sync_systemic": "calendar imports",
    "expo_push": "push notifications",
}


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def _metric(icon, label, text, value, total=None, warn=False):
    """One metric tile. When `total` is given (>0) the frontend draws a gauge
    (value/total); otherwise it's a plain stat tile. `text` is the full plain
    sentence (kept for the copyable report). `label` is the short tile caption."""
    pct = round(100 * value / total) if total else None
    return {"icon": icon, "label": label, "text": text, "value": value,
            "total": total, "pct": pct, "warn": warn}


def _health_line(snapshot: dict) -> dict:
    """Reuse the health aggregate: red if any check is red, else fine. Names the
    red checks in plain words."""
    red = [c for c in snapshot.get("checks", []) if c.get("status") == "red"]
    if red:
        names = []
        for c in red:
            name = HEALTH_PLAIN.get(c["check_name"], c["check_name"])
            if name not in names:
                names.append(name)
        joined = names[0] if len(names) == 1 else (", ".join(names[:-1]) + " and " + names[-1])
        return {
            "status": "red", "icon": "🔴",
            "headline": "Something needs attention",
            "detail": f"{joined[0].upper() + joined[1:]} isn't working right now — check the System Health page.",
            "report_icon": "🔴",
        }
    return {
        "status": "green", "icon": "🟢",
        "headline": "App is working normally",
        "detail": "All systems healthy — nothing needs attention.",
        "report_icon": "✅",
    }


@router.get("/overview")
def overview_report(force: bool = False, _: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        m = db_metrics(conn, days=30)
        steps = {s["label"]: s["value"] for s in funnel_steps(conn)}
        health = health_service.get_health_snapshot(conn)
    finally:
        conn.close()

    families = m["families_total"]
    active = m["active_7d"]
    connected = steps.get("Connected calendar", 0)
    planned = steps.get("Built meal plan", 0)
    problems = m["problem_reports_7d"]
    ideas = m["feature_ideas_7d"]

    active_warn = families > 0 and active <= ACTIVE_USERS_WARN_AT_OR_BELOW
    calendar_warn = families > 0 and (connected / families) < CALENDAR_WARN_BELOW_RATE

    hl = _health_line(health)
    new_families = m["signups_window"]

    # Plain sentences (single source of wording) ------------------------------
    families_text = f"{families} {_plural(families, 'family', 'families')} using the app"
    new_families_text = (f"{new_families} new {_plural(new_families, 'family', 'families')} in the last 30 days"
                         if new_families > 0 else "No new families in the last 30 days")
    active_text = (f"{active} {_plural(active, 'athlete', 'athletes')} active in the last 7 days"
                   if active > 0 else "No athletes active in the last 7 days")
    calendar_text = f"{connected} of {families} {_plural(families, 'family', 'families')} connected their team calendar"
    mealplan_text = (f"{planned} {_plural(planned, 'family has', 'families have')} used a meal plan"
                     if planned > 0 else "No families have used a meal plan yet")
    problems_text = (f"{problems} {_plural(problems, 'problem report', 'problem reports')} this week"
                     if problems > 0 else "No problem reports this week")
    ideas_text = (f"{ideas} new {_plural(ideas, 'idea', 'ideas')} suggested this week"
                  if ideas > 0 else "No new ideas suggested this week")

    athletes_total = m["athletes_total"]

    # Grouped into a structured status report (Growth / Engagement / This week).
    # Engagement metrics are ratios → gauges; the rest are plain counts → stats.
    sections = [
        {"title": "Growth", "lines": [
            _metric("👨‍👩‍👧", "Families", families_text, families),
            _metric("📈", "New this month", new_families_text, new_families),
        ]},
        {"title": "Engagement", "lines": [
            _metric("🏃", "Active this week", active_text, active, total=athletes_total, warn=active_warn),
            _metric("📅", "Connected a calendar", calendar_text, connected, total=families, warn=calendar_warn),
            _metric("🍽️", "Used a meal plan", mealplan_text, planned, total=families),
        ]},
        {"title": "This week", "lines": [
            _metric("🐛", "Problem reports", problems_text, problems),
            _metric("💡", "New ideas", ideas_text, ideas),
        ]},
    ]

    # Paste-ready report (no timestamp header — the frontend prepends the reader's
    # local time). Section headers + warnings per the thresholds above.
    def _w(cond, s):
        return f"⚠️ {s}" if cond else s

    health_report = f"{hl['report_icon']} {hl['headline']}"
    if hl["status"] == "red":
        health_report += f" — {hl['detail']}"
    report_body = "\n".join([
        health_report, "",
        "GROWTH",
        families_text,
        new_families_text, "",
        "ENGAGEMENT",
        _w(active_warn, active_text),
        _w(calendar_warn, calendar_text),
        mealplan_text, "",
        "THIS WEEK",
        problems_text,
        ideas_text,
    ])

    return {
        "as_of": datetime.utcnow().isoformat() + "Z",
        "health": hl,
        "sections": sections,
        "report_body": report_body,
    }
