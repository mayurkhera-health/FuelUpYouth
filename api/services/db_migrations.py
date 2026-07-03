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
        _add_venue_location_to_events(conn)
        _add_activity_type_to_events(conn)
        _add_uid_to_events(conn)
        _add_intensity_to_daily_targets(conn)
        _add_season_phase_to_athletes(conn)
        _add_food_preferences_to_athletes(conn)
        _add_date_of_birth_to_athletes(conn)
        _add_lifestyle_activity_to_athletes(conn)
        _add_diet_pref_to_athletes(conn)
        _create_problem_reports(conn)
        _create_coach_feedback(conn)
        _create_pantry_list_items(conn)
        _create_feature_requests(conn)
        _add_calendar_sync_to_athletes(conn)
        _add_source_to_events(conn)
        _create_admin_audit_log(conn)
        _create_health_tables(conn)
        _add_last_login_to_parents(conn)
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


def _add_season_phase_to_athletes(conn):
    """Fuel Gauge: season phase feeds the daily target formula + intensity
    derivation (design §2.4). Nullable; existing athletes default to 'in_season'.
    Idempotent — safe to run on every startup."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(athletes)").fetchall()]
    if "season_phase" not in cols:
        conn.execute("ALTER TABLE athletes ADD COLUMN season_phase TEXT DEFAULT 'in_season'")


def _add_food_preferences_to_athletes(conn):
    """Onboarding wizard: free-text food preferences (textures, likes/dislikes)
    captured in Step 4 and fed to the AI coach context alongside allergies +
    dietary_restrictions. Nullable, no default — absence means 'not provided',
    so the coach omits it cleanly. Idempotent — safe to run on every startup."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(athletes)").fetchall()]
    if "food_preferences" not in cols:
        conn.execute("ALTER TABLE athletes ADD COLUMN food_preferences TEXT DEFAULT NULL")


def _add_date_of_birth_to_athletes(conn):
    """Capture true date of birth (ISO 'YYYY-MM-DD') so age can be derived live
    via nutrition_calc.calc_age() instead of stored as a static integer. Nullable:
    existing athletes have no DOB and fall back to the stored `age` column until
    they re-enter it. Idempotent — safe to run on every startup."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(athletes)").fetchall()]
    if "date_of_birth" not in cols:
        conn.execute("ALTER TABLE athletes ADD COLUMN date_of_birth TEXT NULL")


def _add_diet_pref_to_athletes(conn):
    """Dietary pattern for protein multiplier (ISSN leucine bioavailability).
    Values: omnivore / vegetarian / vegan. Defaults to 'omnivore'.
    Drives DIET_PROT_MULT in calc_daily_protein(). Idempotent."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(athletes)").fetchall()]
    if "diet_pref" not in cols:
        conn.execute("ALTER TABLE athletes ADD COLUMN diet_pref TEXT DEFAULT 'omnivore'")


def _add_lifestyle_activity_to_athletes(conn):
    """Onboarding field 7: athlete's daily non-training lifestyle activity level.
    Drives the lifestyle PAL in calc_tdee(). Defaults to 'light' (PAL 1.4) for all
    existing athletes. Values: sedentary / light / moderate. Idempotent."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(athletes)").fetchall()]
    if "lifestyle_activity" not in cols:
        conn.execute("ALTER TABLE athletes ADD COLUMN lifestyle_activity TEXT DEFAULT 'light'")


def _add_venue_location_to_events(conn):
    """Venue + precise coordinates for an event, captured from Google Places on the
    client. `latitude`/`longitude` feed coordinate-based weather lookup; `city` is
    kept for backward compat + fallback. All nullable (venue stays optional)."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    if "venue_name" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN venue_name TEXT")
    if "address" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN address TEXT")
    if "latitude" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN latitude REAL")
    if "longitude" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN longitude REAL")


def _add_activity_type_to_events(conn):
    """Per-event activity type tagged by the athlete (Calendar Sync & Day Layout).
    One of the 7 activity_engine keys: practice / game / tournament / speed_sprint /
    strength_cond / active_recovery / double_session. Nullable = untagged; the
    2-hour default (activity_type_resolver) resolves untagged events to 'practice'
    on read. Idempotent."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    if "activity_type" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN activity_type TEXT DEFAULT NULL")


def _add_uid_to_events(conn):
    """ICS import dedup: store the source calendar VEVENT UID so re-imports — and
    the onboarding-then-Schedule-tab double import — skip events already on the
    athlete's schedule. Nullable: manually-created events have no uid. A PARTIAL
    unique index on (athlete_id, uid) WHERE uid IS NOT NULL enforces dedup at the
    DB layer (defense-in-depth behind the client-side skip) while letting an
    athlete keep many NULL-uid manual events. Idempotent — safe every startup."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    if "uid" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN uid TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_athlete_uid "
        "ON events(athlete_id, uid) WHERE uid IS NOT NULL"
    )


def _add_intensity_to_daily_targets(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_targets)").fetchall()]
    if "intensity" not in cols:
        conn.execute("ALTER TABLE daily_targets ADD COLUMN intensity TEXT")


def _create_problem_reports(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS problem_reports (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            description    TEXT NOT NULL,
            screenshot_url TEXT,
            app_version    TEXT,
            platform       TEXT,
            role_hint      TEXT,
            created_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _add_calendar_sync_to_athletes(conn):
    """Recurring calendar sync: store the BYGA / PlayMetrics .ics subscription URL
    per athlete. Both nullable — an athlete may connect zero, one, or both feeds.
    SQLite has no `ADD COLUMN IF NOT EXISTS` and only allows ONE column per ALTER,
    so guard each add with a PRAGMA check (same pattern as _add_uid_to_events).
    Idempotent — safe every startup."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(athletes)").fetchall()]
    if "byga_ics_url" not in cols:
        conn.execute("ALTER TABLE athletes ADD COLUMN byga_ics_url TEXT")
    if "playmetrics_ics_url" not in cols:
        conn.execute("ALTER TABLE athletes ADD COLUMN playmetrics_ics_url TEXT")


def _add_source_to_events(conn):
    """Tag each event with its origin so the calendar-sync reconcile can tell
    synced events apart from manually-added ones. `source` defaults to 'manual'
    (existing rows + parent-created events); the sync job writes 'byga' /
    'playmetrics'. `synced_at` records the last time the sync touched the row
    (TEXT ISO, NULL for manual events) — useful for debugging + sync-status UI.
    The delete phase only ever removes rows whose source matches the feed, so a
    manual event is never wiped. Idempotent — safe every startup."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    if "source" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN source TEXT DEFAULT 'manual'")
    if "synced_at" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN synced_at TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_athlete_source "
        "ON events(athlete_id, source)"
    )


def _add_last_login_to_parents(conn):
    """Beta login alerts: track each parent's most recent login so we can tell a
    first-ever login (new signup) from a returning one. Nullable. Existing
    parents at migration time are backfilled to created_at so they're never
    mislabeled as brand-new the first time they sign in post-deploy — only rows
    created afterward start NULL. Idempotent — safe every startup."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(parents)").fetchall()]
    if "last_login_at" not in cols:
        conn.execute("ALTER TABLE parents ADD COLUMN last_login_at TEXT")
        conn.execute("UPDATE parents SET last_login_at = created_at WHERE last_login_at IS NULL")


def _create_admin_audit_log(conn):
    # Admin Module audit trail. This schema intentionally matches the richer table
    # already present in production from the earlier FuelUp-Admin deployment (46
    # historical rows on the volume) so both coexist and CREATE IF NOT EXISTS is a
    # no-op there. actor_*/action/target_type/target_id are NOT NULL; the detail
    # blob (cascade counts, changed fields) is stored as JSON text in after_state.
    # No parent/athlete FK — rows must survive after the target is hard-deleted.
    # Idempotent — safe every startup.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_audit_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id     INTEGER NOT NULL,
            actor_email  TEXT NOT NULL,
            actor_role   TEXT NOT NULL,
            action       TEXT NOT NULL,
            target_type  TEXT NOT NULL,
            target_id    INTEGER NOT NULL,
            target_email TEXT,
            before_state TEXT,
            after_state  TEXT,
            request_ip   TEXT,
            user_agent   TEXT,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_admin_audit_created "
        "ON admin_audit_log(created_at)"
    )


_HEALTH_CHECK_NAMES = [
    "bedrock_ping", "bedrock_inference", "gmail_smtp", "db_writable", "disk_space",
    "scheduler_notifications", "scheduler_calendar_sync", "calendar_sync_systemic",
    "expo_push",
]


def _create_health_tables(conn):
    # System Health monitoring: current state per check, append-only transition
    # history, scheduler heartbeats, expo-send outcomes, and a scratch table the
    # db_writable probe writes/deletes a row in. last_alerted_at powers the alert
    # cooldown (survives restart). Idempotent — safe every startup.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_checks (
            check_name      TEXT PRIMARY KEY,
            status          TEXT NOT NULL DEFAULT 'unknown',
            detail          TEXT,
            metric_value    REAL,
            last_checked_at TEXT,
            last_green_at   TEXT,
            last_red_at     TEXT,
            last_alerted_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_incidents (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            check_name TEXT NOT NULL,
            from_status TEXT,
            to_status  TEXT,
            detail     TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_health_incidents_created ON health_incidents(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_health_incidents_check ON health_incidents(check_name, created_at)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_heartbeats (
            job_name        TEXT PRIMARY KEY,
            last_run_at     TEXT,
            last_success_at TEXT,
            last_error      TEXT,
            meta            TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expo_push_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            success    INTEGER NOT NULL,
            detail     TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_expo_push_log_created ON expo_push_log(created_at)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_scratch (
            id INTEGER PRIMARY KEY,
            v  TEXT
        )
    """)
    # Seed a row per check so the admin shows all 9 as 'unknown' before the first run.
    conn.executemany(
        "INSERT OR IGNORE INTO health_checks (check_name, status) VALUES (?, 'unknown')",
        [(n,) for n in _HEALTH_CHECK_NAMES],
    )


def _create_feature_requests(conn):
    # "What's Coming" → Suggest a Feature submissions. Each row also triggers a
    # best-effort email to the team (see api/routes/feedback.py). reason is
    # nullable — it's an optional field on the form.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feature_requests (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT,
            athlete_id   INTEGER,
            suggestion   TEXT NOT NULL,
            reason       TEXT,
            submitted_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _create_coach_feedback(conn):
    # Thumbs up/down telemetry on coach answers. High-volume, no email. `reason`
    # is nullable now so adding reason chips later is a pure frontend change.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coach_feedback (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            rating         TEXT NOT NULL,
            question       TEXT,
            answer_excerpt TEXT,
            window_key     TEXT,
            recipe_intent  INTEGER,
            role_hint      TEXT,
            reason         TEXT,
            created_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _create_pantry_list_items(conn):
    """Weekly Prep storage. Columns match pantry_service INSERT/SELECT; UNIQUE backs
    the INSERT OR IGNORE dedup. Idempotent."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pantry_list_items (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id    INTEGER NOT NULL,
            week_start    TEXT    NOT NULL,
            food_id       TEXT    NOT NULL,
            name          TEXT    NOT NULL,
            cue_label     TEXT,
            purchase_unit TEXT,
            role          TEXT,
            meal_context  TEXT,
            must_have     INTEGER NOT NULL DEFAULT 0,
            checked       INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (athlete_id, week_start, food_id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pantry_athlete_week "
        "ON pantry_list_items (athlete_id, week_start)"
    )


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
