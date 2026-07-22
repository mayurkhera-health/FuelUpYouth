"""Daily engagement snapshot generator for TeamCoach.

Reads fueling_window_log to compute per-athlete completion rate for a week,
then upserts a summary to team_engagement_snapshot.

Called by:
  - APScheduler: daily at 11pm PT (api/main.py lifespan)
  - /api/admin/team-coach/teams/{id}/snapshot (manual trigger / backfill)

TeamCoach request handlers NEVER call this — they read team_engagement_snapshot.
window_slot valid values: everyday | fuel_before | top_up | during | recharge | rebuild
"""
from api.database import get_conn

DEFAULT_THRESHOLD_PCT = 80

# All possible window slots — used as the fixed denominator for completion %.
# An athlete with 0 logged slots scores 0%; logging n completed out of TOTAL_SLOTS
# gives n/TOTAL_SLOTS * 100. This matches the spec comment "1/6 = 17%".
WINDOW_SLOTS = ("everyday", "fuel_before", "top_up", "during", "recharge", "rebuild")
TOTAL_SLOTS = len(WINDOW_SLOTS)  # 6


def _current_week_start() -> str:
    from datetime import date, timedelta
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def generate_snapshot(team_id: int, week_start: str | None = None) -> dict:
    """Compute and upsert snapshot for one team for the given week.
    week_start defaults to the current Monday (ISO format YYYY-MM-DD).
    Returns the computed row as a dict.
    """
    if week_start is None:
        week_start = _current_week_start()

    conn = get_conn()
    try:
        team = conn.execute(
            "SELECT threshold_pct FROM teams WHERE id = ?", (team_id,)
        ).fetchone()
        if not team:
            return {"team_id": team_id, "status": "team_not_found"}

        threshold_pct = team["threshold_pct"]

        roster = conn.execute(
            "SELECT athlete_id FROM roster_membership WHERE team_id = ?",
            (team_id,),
        ).fetchall()
        roster_count = len(roster)

        if roster_count == 0:
            _upsert(conn, team_id, week_start, threshold_pct, 0, 0)
            return {
                "team_id": team_id, "week_start": week_start,
                "threshold_pct": threshold_pct,
                "roster_count": 0, "players_above_threshold": 0,
            }

        athlete_ids = [r["athlete_id"] for r in roster]
        placeholders = ",".join("?" * len(athlete_ids))
        logs = conn.execute(
            f"""SELECT athlete_id,
                       SUM(CASE WHEN completed=1 THEN 1 ELSE 0 END) AS total_completed
                FROM fueling_window_log
                WHERE athlete_id IN ({placeholders})
                  AND date >= ?
                  AND date <= date(?, '+6 days')
                GROUP BY athlete_id""",
            (*athlete_ids, week_start, week_start),
        ).fetchall()

        log_map = {r["athlete_id"]: r for r in logs}
        above = 0
        for aid in athlete_ids:
            row = log_map.get(aid)
            completed = row["total_completed"] if row else 0
            if TOTAL_SLOTS > 0:
                pct = 100 * completed / TOTAL_SLOTS
                if pct >= threshold_pct:
                    above += 1

        _upsert(conn, team_id, week_start, threshold_pct, above, roster_count)
        return {
            "team_id": team_id,
            "week_start": week_start,
            "threshold_pct": threshold_pct,
            "roster_count": roster_count,
            "players_above_threshold": above,
        }
    finally:
        conn.close()


def _upsert(conn, team_id, week_start, threshold_pct, above, roster_count):
    conn.execute(
        """INSERT INTO team_engagement_snapshot
               (team_id, week_start, threshold_pct, players_above_threshold, roster_count)
           VALUES (?,?,?,?,?)
           ON CONFLICT(team_id, week_start) DO UPDATE SET
               threshold_pct=excluded.threshold_pct,
               players_above_threshold=excluded.players_above_threshold,
               roster_count=excluded.roster_count,
               generated_at=datetime('now')""",
        (team_id, week_start, threshold_pct, above, roster_count),
    )
    conn.commit()


def generate_all_snapshots() -> None:
    """Regenerate snapshot for every team. Called by daily APScheduler job."""
    conn = get_conn()
    try:
        team_ids = [r["id"] for r in conn.execute("SELECT id FROM teams").fetchall()]
    finally:
        conn.close()
    for tid in team_ids:
        generate_snapshot(tid)
