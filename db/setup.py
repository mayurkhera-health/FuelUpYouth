# db/setup.py
import os
import sqlite3
from pathlib import Path

def init_db():
    db_path = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "fuelup.db"))
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS parents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            consent_timestamp TEXT NOT NULL,
            consent_confirmed BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS athletes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER REFERENCES parents(id),
            first_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            weight_lbs REAL NOT NULL,
            height_ft INTEGER NOT NULL,
            height_in REAL NOT NULL,
            position TEXT,
            competition_level TEXT,
            sweat_profile TEXT,
            allergies TEXT,
            dietary_restrictions TEXT,
            supplement_use TEXT,
            blueprint_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER REFERENCES athletes(id),
            event_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            start_time TEXT,
            duration_hours REAL,
            city TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS meal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER REFERENCES athletes(id),
            logged_at TEXT DEFAULT CURRENT_TIMESTAMP,
            log_method TEXT NOT NULL,
            description TEXT,
            calories REAL,
            carbs_g REAL,
            protein_g REAL,
            fat_g REAL,
            iron_mg REAL,
            calcium_mg REAL,
            water_oz REAL,
            edamam_raw TEXT
        );

        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER REFERENCES athletes(id),
            endpoint TEXT NOT NULL,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            remind_pregame_meal INTEGER DEFAULT 1,
            remind_pregame_snack INTEGER DEFAULT 1,
            remind_meal_log INTEGER DEFAULT 1,
            remind_hydration INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(athlete_id, endpoint)
        );

        CREATE TABLE IF NOT EXISTS meal_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
            plan_date  TEXT NOT NULL,
            slot_name  TEXT NOT NULL,
            recipe_id  TEXT,
            recipe_name TEXT,
            calories   REAL,
            carbs_g    REAL,
            protein_g  REAL,
            fat_g      REAL,
            is_ai_generated INTEGER DEFAULT 0,
            logged     INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(athlete_id, plan_date, slot_name)
        );

        CREATE INDEX IF NOT EXISTS idx_meal_plans_athlete_date
            ON meal_plans(athlete_id, plan_date);

        CREATE TABLE IF NOT EXISTS daily_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER REFERENCES athletes(id),
            target_date TEXT NOT NULL,
            event_type TEXT,
            total_calories INTEGER,
            carbs_g_min INTEGER,
            carbs_g_max INTEGER,
            protein_g_min INTEGER,
            protein_g_max INTEGER,
            fat_g_min INTEGER,
            fat_g_max INTEGER,
            iron_mg INTEGER,
            calcium_mg INTEGER,
            hydration_oz_min INTEGER,
            hydration_oz_max INTEGER,
            lea_alert BOOLEAN,
            targets_raw TEXT
        );

        CREATE TABLE IF NOT EXISTS otp_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER NOT NULL REFERENCES parents(id) ON DELETE CASCADE,
            code_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_otp_parent
            ON otp_codes(parent_id, used, expires_at);
    """)

    conn.commit()
    conn.close()
    print("FuelUp database initialized.")

if __name__ == "__main__":
    init_db()
