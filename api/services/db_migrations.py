"""
Additive database migrations — CREATE TABLE IF NOT EXISTS and INSERT OR IGNORE only.
Called at FastAPI startup; safe to run multiple times.
"""

from api.database import get_conn
from api.services.nutrition_calc import derive_intensity


def run_all():
    conn = get_conn()
    try:
        _create_confirmations(conn)
        _create_report_config(conn)
        _create_shopping_tables(conn)
        _create_expo_push_tokens(conn)
        _create_window_logs(conn)
        _create_notification_log(conn)
        _create_streak_state(conn)
        _add_timezone_to_tokens(conn)
        _add_intensity_to_events(conn)
        _add_intensity_to_daily_targets(conn)
        conn.commit()
    finally:
        conn.close()

    # Table-rebuild migrations run on their OWN connection, AFTER the batch above
    # has committed and closed. A rebuild must toggle PRAGMA foreign_keys, which
    # cannot change inside a transaction — so it owns its full transaction/pragma
    # lifecycle in isolation and must never share the batch connection.
    _migrate_athlete_logins_unique()


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


def _create_streak_state(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS streak_state (
            athlete_id                INTEGER PRIMARY KEY,
            freeze_tokens             INTEGER NOT NULL DEFAULT 1,
            last_celebrated_milestone INTEGER NOT NULL DEFAULT 0,
            updated_at                TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)


def _add_intensity_to_events(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    if "intensity" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN intensity TEXT")
        rows = conn.execute("""
            SELECT e.id AS id, e.event_type AS event_type, a.competition_level AS competition_level
            FROM events e LEFT JOIN athletes a ON a.id = e.athlete_id
        """).fetchall()
        for r in rows:
            intensity = derive_intensity(r["event_type"], r["competition_level"])
            conn.execute("UPDATE events SET intensity = ? WHERE id = ?", (intensity, r["id"]))


def _add_intensity_to_daily_targets(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_targets)").fetchall()]
    if "intensity" not in cols:
        conn.execute("ALTER TABLE daily_targets ADD COLUMN intensity TEXT")


def _migrate_athlete_logins_unique():
    """
    Add UNIQUE(athlete_id) to athlete_logins — defense-in-depth behind the
    code-level already-claimed guard in routes/auth.py (the guard is the primary
    safety; this stops a duplicate athlete login at the DB layer too).

    Production was created from db/setup.py, which lacked the constraint, so this
    rebuilds the table (SQLite can't ALTER ADD CONSTRAINT). Runs on a DEDICATED
    connection with its own transaction + foreign_keys toggle, because PRAGMA
    foreign_keys cannot change inside a transaction and must not collide with
    run_all()'s batch transaction. Idempotent: once the unique index exists it
    returns immediately, so it's safe on every deploy.
    """
    conn = get_conn()
    try:
        # No-op if the table doesn't exist yet (fresh DBs get UNIQUE from setup.py).
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='athlete_logins'"
        ).fetchone():
            return

        # IDEMPOTENCY: skip if a UNIQUE index on exactly (athlete_id) already exists.
        for idx in conn.execute("PRAGMA index_list(athlete_logins)").fetchall():
            if idx[2]:  # unique flag
                cols = [r[2] for r in conn.execute(f"PRAGMA index_info('{idx[1]}')").fetchall()]
                if cols == ["athlete_id"]:
                    return  # constraint already present — nothing to do

        # REBUILD. athlete_logins has an outgoing ON DELETE CASCADE FK to athletes,
        # so disable FK enforcement around the drop/rename. Toggle in autocommit
        # (isolation_level=None), wrap the rebuild in an explicit BEGIN/COMMIT so it
        # stays atomic, ROLLBACK on error, and always restore foreign_keys=ON.
        conn.isolation_level = None
        try:
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("BEGIN")
            conn.execute("""
                CREATE TABLE athlete_logins_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    email       TEXT UNIQUE NOT NULL,
                    athlete_id  INTEGER NOT NULL UNIQUE REFERENCES athletes(id) ON DELETE CASCADE,
                    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Row-preserving + dedup-safe: keep the earliest login per athlete_id.
            conn.execute("""
                INSERT INTO athlete_logins_new (id, email, athlete_id, created_at)
                SELECT id, email, athlete_id, created_at FROM athlete_logins
                WHERE id IN (SELECT MIN(id) FROM athlete_logins GROUP BY athlete_id)
            """)
            conn.execute("DROP TABLE athlete_logins")
            conn.execute("ALTER TABLE athlete_logins_new RENAME TO athlete_logins")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_athlete_logins_email ON athlete_logins(email)"
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.execute("PRAGMA foreign_keys=ON")
    finally:
        conn.close()
