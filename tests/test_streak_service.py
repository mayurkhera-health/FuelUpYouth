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
