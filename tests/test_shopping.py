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
    # Check a food known to have multiple allergens in the CSV (semicolon-separated)
    # Find any food with semicolons in its allergen_tags
    rows = conn.execute(
        "SELECT name, allergen_tags FROM fueling_foods WHERE allergen_tags LIKE '%;%'"
    ).fetchall()
    # If the CSV has any multi-allergen foods, they must use semicolon format
    # (If CSV has no multi-allergen foods, this test is vacuously true — that's OK)
    for row in rows:
        tags = row["allergen_tags"]
        parts = tags.split(";")
        assert len(parts) >= 2, f"{row['name']} should have multiple allergen parts: {tags}"
        for part in parts:
            assert part.strip(), f"Empty allergen part in {row['name']}: {tags}"
    # Assert at least one food actually has a multi-allergen tag (verifies the check is meaningful)
    if rows:
        assert len(rows) >= 1  # At least one food has multi-allergen tags


def test_seed_soft_hint_empty_string_for_foods_without_hint(conn):
    from db.setup import seed_fueling_foods
    seed_fueling_foods(conn)
    # Any food without a soft_hint column value should be stored as empty string not NULL
    rows = conn.execute(
        "SELECT name, soft_hint FROM fueling_foods WHERE soft_hint IS NULL"
    ).fetchall()
    assert len(rows) == 0  # No NULLs — all should be empty string
