"""Unit tests for the Fuel Streak service (api/services/streak_service.py)."""

import sqlite3
from datetime import date, timedelta

import pytest

from api.services.db_migrations import _create_streak_state


def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_streak_state_table_is_created():
    conn = _mk_conn()
    _create_streak_state(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(streak_state)").fetchall()}
    assert cols == {
        "athlete_id",
        "freeze_tokens",
        "last_celebrated_milestone",
        "updated_at",
    }
    conn.close()


from api.services import streak_service as ss


def _streak_db():
    """In-memory DB with the tables the streak service reads."""
    conn = _mk_conn()
    conn.executescript("""
        CREATE TABLE confirmations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            log_date TEXT NOT NULL,
            window_key TEXT NOT NULL,
            window_type TEXT NOT NULL
        );
        CREATE TABLE window_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id INTEGER NOT NULL,
            window_id TEXT NOT NULL,
            log_date TEXT NOT NULL
        );
        CREATE TABLE report_config (
            key TEXT PRIMARY KEY,
            value REAL NOT NULL,
            description TEXT,
            updated_at TEXT
        );
        INSERT INTO report_config VALUES ('streak_min_confirms_per_day', 1.0, '', datetime('now'));
    """)
    return conn


def _confirm(conn, athlete_id, log_date, window_key="pre_event_meal", window_type="pre_fuel"):
    conn.execute(
        "INSERT INTO confirmations (athlete_id, log_date, window_key, window_type) VALUES (?, ?, ?, ?)",
        (athlete_id, log_date, window_key, window_type),
    )
    conn.commit()


def test_qualifying_dates_from_confirmations():
    conn = _streak_db()
    _confirm(conn, 1, "2026-06-10")
    _confirm(conn, 1, "2026-06-11")
    assert ss._qualifying_dates(1, conn) == {"2026-06-10", "2026-06-11"}
    conn.close()


def test_qualifying_dates_union_with_window_logs():
    conn = _streak_db()
    _confirm(conn, 1, "2026-06-10")
    conn.execute(
        "INSERT INTO window_logs (athlete_id, window_id, log_date) VALUES (1, 'breakfast', '2026-06-12')"
    )
    conn.commit()
    assert ss._qualifying_dates(1, conn) == {"2026-06-10", "2026-06-12"}
    conn.close()


def test_best_streak_finds_longest_run():
    # 06-01,02,03 (run of 3), gap, 06-05,06 (run of 2) -> best 3
    qual = {"2026-06-01", "2026-06-02", "2026-06-03", "2026-06-05", "2026-06-06"}
    assert ss._best_streak(qual) == 3


def test_week_strip_is_monday_to_sunday():
    # Wednesday 2026-06-17; Monday of that week is 2026-06-15
    qual = {"2026-06-15", "2026-06-17"}
    strip = ss._week_strip(qual, date(2026, 6, 17))
    assert strip == [True, False, True, False, False, False, False]
