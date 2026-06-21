"""
Fuel Streak — single source of truth for the youth daily streak.

A "qualifying day" is a calendar day on which the athlete completed at least
`streak_min_confirms_per_day` fuel windows. Completion is read from the
`confirmations` table (the Today-screen confirm tap) unioned with `window_logs`
(the photo/voice/text capture path), so a day counts regardless of which path
the athlete used.

current/best streak are ALWAYS computed from those tables — never cached — so
they cannot drift. The streak_state table stores only non-derivable state
(freeze tokens, last-celebrated milestone).
"""

import sqlite3
from datetime import date, timedelta

MILESTONES = [2, 5, 10, 21]
DEFAULT_FREEZE_TOKENS = 1


def _as_date(value) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _min_confirms(conn) -> int:
    row = conn.execute(
        "SELECT value FROM report_config WHERE key = 'streak_min_confirms_per_day'"
    ).fetchone()
    return int(row["value"]) if row else 1


def _qualifying_dates(athlete_id: int, conn) -> set:
    """Set of YYYY-MM-DD strings the athlete qualified on (confirmations ∪ window_logs)."""
    min_c = _min_confirms(conn)
    rows = conn.execute(
        "SELECT log_date, COUNT(*) AS c FROM confirmations WHERE athlete_id = ? GROUP BY log_date",
        (athlete_id,),
    ).fetchall()
    days = {r["log_date"] for r in rows if r["c"] >= min_c}
    try:
        wl = conn.execute(
            "SELECT DISTINCT log_date FROM window_logs WHERE athlete_id = ?",
            (athlete_id,),
        ).fetchall()
        days |= {r["log_date"] for r in wl}
    except sqlite3.OperationalError:
        pass  # window_logs may be absent in minimal/legacy DBs
    return days


def _best_streak(qual: set) -> int:
    """Longest run of consecutive calendar days ever."""
    if not qual:
        return 0
    dates = sorted(date.fromisoformat(d) for d in qual)
    best = cur = 1
    for i in range(1, len(dates)):
        cur = cur + 1 if (dates[i] - dates[i - 1]).days == 1 else 1
        best = max(best, cur)
    return best


def _week_strip(qual: set, today: date) -> list:
    """Mon..Sun booleans for the week containing `today`."""
    monday = today - timedelta(days=today.weekday())
    return [(monday + timedelta(days=i)).isoformat() in qual for i in range(7)]
