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
        _create_shopping_tables(conn)
        _create_expo_push_tokens(conn)
        _create_window_logs(conn)
        _create_notification_log(conn)
        _add_timezone_to_tokens(conn)
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


def _create_expo_push_tokens(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expo_push_tokens (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id  INTEGER,
            parent_id   INTEGER,
            token       TEXT NOT NULL UNIQUE,
            platform    TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_expo_tokens_athlete
            ON expo_push_tokens (athlete_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_expo_tokens_parent
            ON expo_push_tokens (parent_id)
    """)


def _create_shopping_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fueling_foods (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL UNIQUE,
            category      TEXT NOT NULL,
            role          TEXT,
            allergen_tags TEXT DEFAULT '',
            soft_hint     TEXT DEFAULT '',
            is_active     INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS athlete_food_prefs (
            athlete_id  INTEGER NOT NULL,
            food_name   TEXT NOT NULL,
            preference  TEXT NOT NULL,
            category    TEXT,
            PRIMARY KEY (athlete_id, food_name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shopping_lists (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id  INTEGER NOT NULL,
            week_start  TEXT NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (athlete_id, week_start)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shopping_list_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            list_id     INTEGER NOT NULL,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL,
            source      TEXT NOT NULL DEFAULT 'suggested',
            checked     INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (list_id) REFERENCES shopping_lists(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS food_submissions (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            name               TEXT NOT NULL,
            suggested_category TEXT,
            submitted_by       INTEGER NOT NULL,
            status             TEXT NOT NULL DEFAULT 'pending',
            created_at         TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)


def _create_window_logs(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS window_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id      INTEGER NOT NULL,
            window_id       TEXT NOT NULL,
            log_date        TEXT NOT NULL,
            method          TEXT NOT NULL DEFAULT 'photo',
            text            TEXT,
            photo_url       TEXT,
            thumb_url       TEXT,
            audio_url       TEXT,
            nutrient_status TEXT NOT NULL DEFAULT 'none',
            logged_by       TEXT,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(athlete_id, window_id, log_date)
        )
    """)
    # Additive column migrations for rows created before these columns existed
    cols = [r[1] for r in conn.execute("PRAGMA table_info(window_logs)").fetchall()]
    if "logged_by" not in cols:
        conn.execute("ALTER TABLE window_logs ADD COLUMN logged_by TEXT")
    if "audio_url" not in cols:
        conn.execute("ALTER TABLE window_logs ADD COLUMN audio_url TEXT")


def _create_notification_log(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            window_key TEXT    NOT NULL,
            send_date  TEXT    NOT NULL,
            recipient  TEXT    NOT NULL,
            token      TEXT    NOT NULL,
            sent_at    TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (athlete_id, window_key, send_date, recipient)
        )
    """)


def _add_timezone_to_tokens(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(expo_push_tokens)").fetchall()]
    if "timezone" not in cols:
        conn.execute("ALTER TABLE expo_push_tokens ADD COLUMN timezone TEXT")
