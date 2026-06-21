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


def _freeze_tokens(athlete_id: int, conn) -> int:
    try:
        row = conn.execute(
            "SELECT freeze_tokens FROM streak_state WHERE athlete_id = ?",
            (athlete_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        return DEFAULT_FREEZE_TOKENS
    return int(row["freeze_tokens"]) if row else DEFAULT_FREEZE_TOKENS


def compute_current_streak(athlete_id: int, conn, today=None) -> dict:
    """
    Consecutive qualifying days ending today (or yesterday if today is not yet
    logged — today never breaks the streak). Up to `freeze_tokens` missed days
    that fall within the rolling 7-day window are bridged (auto-freeze). A bridge
    only counts as a 'used' freeze once a qualifying day actually follows it, so a
    streak that simply runs out of history does not report a wasted freeze.
    """
    today_d = _as_date(today)
    qual = _qualifying_dates(athlete_id, conn)
    max_bridges = _freeze_tokens(athlete_id, conn)
    bridges_used = 0
    pending_bridges = 0

    # Today-grace: if today is not yet logged, anchor on yesterday.
    anchor = today_d if today_d.isoformat() in qual else today_d - timedelta(days=1)
    streak = 0
    d = anchor
    while streak <= 3650:  # safety bound (~10y)
        if d.isoformat() in qual:
            streak += 1
            # A qualifying day followed the bridged gap(s): the freeze actually
            # protected the streak, so commit the pending bridges now.
            bridges_used += pending_bridges
            pending_bridges = 0
            d -= timedelta(days=1)
            continue
        within_7 = d >= today_d - timedelta(days=6)
        if (bridges_used + pending_bridges) < max_bridges and within_7:
            pending_bridges += 1
            d -= timedelta(days=1)
            continue
        break

    return {"current": streak, "freeze_used_this_week": bridges_used > 0}


def _ensure_streak_state(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS streak_state (
            athlete_id                INTEGER PRIMARY KEY,
            freeze_tokens             INTEGER NOT NULL DEFAULT 1,
            last_celebrated_milestone INTEGER NOT NULL DEFAULT 0,
            updated_at                TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)


def get_streak(athlete_id: int, conn, today=None) -> dict:
    """Read-path streak block for the Today screen. Never celebrates (that is
    the write path's job), so `just_reached_milestone` is always None here."""
    today_d = _as_date(today)
    qual = _qualifying_dates(athlete_id, conn)
    cur = compute_current_streak(athlete_id, conn, today_d)
    next_m = next((m for m in MILESTONES if m > cur["current"]), None)
    return {
        "current": cur["current"],
        "best": _best_streak(qual),
        "week_strip": _week_strip(qual, today_d),
        "today_done": today_d.isoformat() in qual,
        "freeze_used_this_week": cur["freeze_used_this_week"],
        "next_milestone": next_m,
        "just_reached_milestone": None,
    }


def register_confirmation(athlete_id: int, conn, today=None) -> dict:
    """Write-path hook. Call after a confirmation is recorded. Updates the
    milestone marker and returns the streak block with `just_reached_milestone`
    set when the athlete crosses a new tier."""
    _ensure_streak_state(conn)
    block = get_streak(athlete_id, conn, today)
    cur = block["current"]
    reached = max((m for m in MILESTONES if m <= cur), default=0)

    row = conn.execute(
        "SELECT last_celebrated_milestone FROM streak_state WHERE athlete_id = ?",
        (athlete_id,),
    ).fetchone()
    last = int(row["last_celebrated_milestone"]) if row else 0

    just = None
    if reached != last:
        conn.execute(
            "INSERT INTO streak_state (athlete_id, last_celebrated_milestone) VALUES (?, ?) "
            "ON CONFLICT(athlete_id) DO UPDATE SET "
            "last_celebrated_milestone = excluded.last_celebrated_milestone, "
            "updated_at = datetime('now')",
            (athlete_id, reached),
        )
        conn.commit()
        if reached > last:          # climbing up -> celebrate; dropping -> just reset marker
            just = reached

    block["just_reached_milestone"] = just
    return block
