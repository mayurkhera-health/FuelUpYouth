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
