# tests/test_shopping.py
import os
os.environ["DB_PATH"] = ":memory:"

import sqlite3, pytest
from db.setup import init_db
from api.database import get_conn


@pytest.fixture
def conn():
    init_db()
    c = get_conn()
    yield c
    c.close()


def test_fueling_foods_table_exists(conn):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='fueling_foods'"
    ).fetchone()
    assert row is not None


def test_athlete_food_prefs_table_exists(conn):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='athlete_food_prefs'"
    ).fetchone()
    assert row is not None


def test_shopping_lists_table_exists(conn):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='shopping_lists'"
    ).fetchone()
    assert row is not None


def test_shopping_list_items_table_exists(conn):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='shopping_list_items'"
    ).fetchone()
    assert row is not None


def test_food_submissions_table_exists(conn):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='food_submissions'"
    ).fetchone()
    assert row is not None


def test_seed_loads_all_60_foods(conn):
    from db.setup import seed_fueling_foods
    seed_fueling_foods(conn)
    count = conn.execute("SELECT COUNT(*) FROM fueling_foods").fetchone()[0]
    assert count == 60


def test_seed_is_idempotent(conn):
    from db.setup import seed_fueling_foods
    seed_fueling_foods(conn)
    seed_fueling_foods(conn)
    count = conn.execute("SELECT COUNT(*) FROM fueling_foods").fetchone()[0]
    assert count == 60


def test_seed_allergen_tags_stored_correctly(conn):
    from db.setup import seed_fueling_foods
    seed_fueling_foods(conn)
    # Find any food that has allergen tags in the CSV
    rows = conn.execute(
        "SELECT allergen_tags FROM fueling_foods WHERE allergen_tags != ''"
    ).fetchall()
    # At least some foods have allergen tags
    assert len(rows) > 0
    # All non-empty tags use semicolon format (not comma-separated)
    for row in rows:
        tags = row[0]
        assert "," not in tags or ";" in tags  # semicolon is the separator


def test_seed_soft_hint_empty_string_for_foods_without_hint(conn):
    from db.setup import seed_fueling_foods
    seed_fueling_foods(conn)
    # Any food without a soft_hint column value should be stored as empty string not NULL
    rows = conn.execute(
        "SELECT name, soft_hint FROM fueling_foods WHERE soft_hint IS NULL"
    ).fetchall()
    assert len(rows) == 0  # No NULLs — all should be empty string
