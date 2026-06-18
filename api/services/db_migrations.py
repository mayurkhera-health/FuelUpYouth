"""
Additive database migrations — CREATE TABLE IF NOT EXISTS and INSERT OR IGNORE only.
Called at FastAPI startup; safe to run multiple times.
"""

from api.database import get_conn


def run_all():
    conn = get_conn()
    try:
        _create_confirmations(conn)
        _create_report_config(conn)
        conn.commit()
    finally:
        conn.close()


def _create_confirmations(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS confirmations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id  INTEGER NOT NULL REFERENCES athletes(id),
            log_date    TEXT    NOT NULL,
            window_key  TEXT    NOT NULL,
            window_type TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (athlete_id, window_key, log_date)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_confirmations_athlete_date
            ON confirmations (athlete_id, log_date)
    """)


_DEFAULT_CONFIG = [
    # key, value, description
    ("load_high_game_days",       3.0, "Game/tournament days per week that qualifies as high load"),
    ("prefuel_rate_low",          0.5, "Pre-fuel confirmation rate below which the safety flag can fire"),
    ("recovery_rate_low",         0.5, "Recovery confirmation rate below which the safety flag can fire"),
    ("hydration_rate_low",        0.5, "Hydration confirmation rate below which the safety flag can fire"),
    ("streak_min_confirms_per_day", 1.0, "Min confirmations in a day to count toward streak"),
]


def _create_report_config(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS report_config (
            key         TEXT PRIMARY KEY,
            value       REAL NOT NULL,
            description TEXT,
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.executemany(
        "INSERT OR IGNORE INTO report_config (key, value, description) VALUES (?, ?, ?)",
        _DEFAULT_CONFIG,
    )
