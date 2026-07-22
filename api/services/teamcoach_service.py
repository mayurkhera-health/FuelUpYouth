"""TeamCoach dashboard data assembly.

All DB reads use get_read_conn() — read-only connection, 3s timeout (decision #3).
Never queries fueling_window_log from a request handler (non-negotiable constraint).
Engagement data comes exclusively from team_engagement_snapshot.
"""
from api.database import get_read_conn

# Decision #1 — Deliberate product decision, not a technical default.
# Decided Mayur Khera, 2026-07-21: consent not enforced for MVP pilot —
# TeamCoach accounts see full roster status regardless of parent opt-in.
# Revisit before scaling beyond pilot.
ENFORCE_CONSENT = False


def get_coach_teams(coach_id: int) -> list[dict]:
    conn = get_read_conn()
    try:
        rows = conn.execute(
            """SELECT t.id, t.name, t.season, t.threshold_pct
               FROM teams t
               JOIN coach_team_access cta ON cta.team_id = t.id
               WHERE cta.coach_id = ?
               ORDER BY t.name""",
            (coach_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def assert_coach_owns_team(coach_id: int, team_id: int) -> None:
    """Raise 403 if coach does not have access to this team."""
    from fastapi import HTTPException
    conn = get_read_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM coach_team_access WHERE coach_id=? AND team_id=?",
            (coach_id, team_id),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(403, "Access denied to this team")


def get_roster(team_id: int) -> list[dict]:
    conn = get_read_conn()
    try:
        rows = conn.execute(
            """SELECT a.id AS athlete_id, a.first_name,
                      rm.parent_consent_flag, rm.joined_at
               FROM roster_membership rm
               JOIN athletes a ON a.id = rm.athlete_id
               WHERE rm.team_id = ?
               ORDER BY a.first_name""",
            (team_id,),
        ).fetchall()
        result = []
        for r in rows:
            result.append({
                "athlete_id": r["athlete_id"],
                "first_name": r["first_name"],
                "join_status": "joined",
                "logging_status": _logging_status(conn, r["athlete_id"]),
                "parent_consent_flag": bool(r["parent_consent_flag"]),
                "joined_at": r["joined_at"],
            })
        return result
    finally:
        conn.close()


def _logging_status(conn, athlete_id: int) -> str:
    """Check for completed fueling-window logs in the past 7 days.
    Returns 'active', 'inactive', or 'no_data'.
    'no_data' is the expected state in production until mobile logging ships.
    """
    row = conn.execute(
        """SELECT COUNT(*) AS cnt
           FROM fueling_window_log
           WHERE athlete_id = ?
             AND completed = 1
             AND date >= date('now', '-7 days')""",
        (athlete_id,),
    ).fetchone()
    if row is None or row["cnt"] == 0:
        any_row = conn.execute(
            "SELECT 1 FROM fueling_window_log WHERE athlete_id = ? LIMIT 1",
            (athlete_id,),
        ).fetchone()
        return "inactive" if any_row else "no_data"
    return "active"


def get_engagement(team_id: int) -> dict:
    """Read latest two snapshot rows for current + prior week trend.
    Never queries fueling_window_log — reads team_engagement_snapshot only.
    """
    conn = get_read_conn()
    try:
        rows = conn.execute(
            """SELECT week_start, threshold_pct, players_above_threshold,
                      roster_count, generated_at
               FROM team_engagement_snapshot
               WHERE team_id = ?
               ORDER BY week_start DESC
               LIMIT 2""",
            (team_id,),
        ).fetchall()
        if not rows:
            return {"current_week": None, "prior_week": None, "last_updated": None}
        current = dict(rows[0])
        prior = dict(rows[1]) if len(rows) > 1 else None
        return {
            "current_week": current,
            "prior_week": prior,
            "last_updated": current["generated_at"],
        }
    finally:
        conn.close()
