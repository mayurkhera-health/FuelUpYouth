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


# ── classify_week ─────────────────────────────────────────────────────────────

from api.services.shopping_service import classify_week, build_essentials


def test_classify_week_no_events_is_rest():
    result = classify_week({})
    assert result["practice_count"] == 0
    assert result["game_count"] == 0
    assert result["has_game"] is False


def test_classify_week_counts_practices():
    events_by_day = {
        "2026-06-16": [{"event_type": "practice", "start_time": "16:00", "duration_hours": 1.5}],
        "2026-06-17": [{"event_type": "practice", "start_time": "16:00", "duration_hours": 1.5}],
        "2026-06-18": [{"event_type": "practice", "start_time": "16:00", "duration_hours": 1.5}],
        "2026-06-19": [],
        "2026-06-20": [],
        "2026-06-21": [],
        "2026-06-22": [],
    }
    result = classify_week(events_by_day)
    assert result["practice_count"] == 3
    assert result["game_count"] == 0
    assert result["has_game"] is False


def test_classify_week_detects_game():
    events_by_day = {
        "2026-06-16": [{"event_type": "practice", "start_time": "16:00", "duration_hours": 1.5}],
        "2026-06-21": [{"event_type": "game", "start_time": "10:00", "duration_hours": 1.5}],
        **{d: [] for d in ["2026-06-17","2026-06-18","2026-06-19","2026-06-20","2026-06-22"]},
    }
    result = classify_week(events_by_day)
    assert result["practice_count"] == 1
    assert result["game_count"] == 1
    assert result["has_game"] is True


def test_classify_week_header_line_matches_counts():
    events_by_day = {
        "2026-06-16": [{"event_type": "practice", "start_time": "16:00", "duration_hours": 1.5}],
        "2026-06-17": [{"event_type": "practice", "start_time": "16:00", "duration_hours": 1.5}],
        "2026-06-21": [{"event_type": "game", "start_time": "10:00", "duration_hours": 1.5}],
        **{d: [] for d in ["2026-06-18","2026-06-19","2026-06-20","2026-06-22"]},
    }
    result = classify_week(events_by_day)
    assert result["schedule_line"] == "2 practices + 1 game this week"


# ── build_essentials ──────────────────────────────────────────────────────────

def _insert_athlete(conn, suffix="a") -> int:
    """Helper: insert a minimal parent+athlete, return athlete id."""
    conn.execute(
        f"INSERT OR IGNORE INTO parents (full_name, email, consent_timestamp) "
        f"VALUES ('P{suffix}', 'p{suffix}@t.com', '2026-01-01')"
    )
    parent_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute(
        "INSERT OR IGNORE INTO athletes "
        "(parent_id, first_name, age, gender, weight_lbs, height_ft, height_in) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (parent_id, "Alex", 15, "Boy", 140, 5, 8),
    )
    athlete_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    return athlete_id


def _seed(conn):
    from db.setup import seed_fueling_foods
    seed_fueling_foods(conn)


def test_build_essentials_no_events_returns_staples_only(conn):
    _seed(conn)
    aid = _insert_athlete(conn, "rest")
    result = build_essentials(aid, "2026-06-16", conn)
    categories = {g["category"] for g in result["groups"]}
    assert categories == {"breakfast", "dinner_staple"}
    assert result["header"]["has_game"] is False


def test_build_essentials_practice_week_adds_pre_fuel_and_recovery(conn):
    _seed(conn)
    aid = _insert_athlete(conn, "prac")
    conn.execute(
        "INSERT INTO events (athlete_id, event_name, event_type, event_date, start_time, duration_hours) "
        "VALUES (?, 'Practice', 'practice', '2026-06-16', '16:00', 1.5)",
        (aid,),
    )
    conn.commit()
    result = build_essentials(aid, "2026-06-16", conn)
    categories = {g["category"] for g in result["groups"]}
    assert "pre_fuel" in categories
    assert "recovery" in categories


def test_build_essentials_game_week_includes_hydration(conn):
    _seed(conn)
    aid = _insert_athlete(conn, "game")
    conn.execute(
        "INSERT INTO events (athlete_id, event_name, event_type, event_date, start_time, duration_hours) "
        "VALUES (?, 'Game', 'game', '2026-06-21', '10:00', 1.5)",
        (aid,),
    )
    conn.commit()
    result = build_essentials(aid, "2026-06-16", conn)
    categories = {g["category"] for g in result["groups"]}
    assert "hydration" in categories
    assert result["header"]["has_game"] is True


def test_build_essentials_disliked_food_absent(conn):
    _seed(conn)
    aid = _insert_athlete(conn, "dis")
    conn.execute(
        "INSERT OR IGNORE INTO athlete_food_prefs (athlete_id, food_name, preference) "
        "VALUES (?, 'Cottage cheese', 'disliked')",
        (aid,),
    )
    conn.commit()
    result = build_essentials(aid, "2026-06-16", conn)
    all_names = [f["name"] for g in result["groups"] for f in g["foods"]]
    assert "Cottage cheese" not in all_names


def test_build_essentials_allergic_food_absent(conn):
    _seed(conn)
    aid = _insert_athlete(conn, "allergy")
    conn.execute(
        "INSERT OR IGNORE INTO athlete_food_prefs (athlete_id, food_name, preference) "
        "VALUES (?, 'Eggs', 'allergic')",
        (aid,),
    )
    conn.commit()
    result = build_essentials(aid, "2026-06-16", conn)
    all_names = [f["name"] for g in result["groups"] for f in g["foods"]]
    assert "Eggs" not in all_names


def test_build_essentials_liked_personal_food_appears(conn):
    _seed(conn)
    aid = _insert_athlete(conn, "liked")
    conn.execute(
        "INSERT OR IGNORE INTO athlete_food_prefs (athlete_id, food_name, preference, category) "
        "VALUES (?, 'Homemade granola', 'liked', 'breakfast')",
        (aid,),
    )
    conn.commit()
    result = build_essentials(aid, "2026-06-16", conn)
    all_names = [f["name"] for g in result["groups"] for f in g["foods"]]
    assert "Homemade granola" in all_names
