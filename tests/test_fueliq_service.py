"""Unit tests for Fuel IQ (api/services/fueliq_service.py)."""

import sqlite3

import pytest

from api.services.db_migrations import _create_fueliq_tables, _create_report_config
from api.services import fueliq_service as fq


def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _fueliq_db():
    """In-memory DB with athletes + the fueliq_* tables the service reads/writes."""
    conn = _mk_conn()
    conn.executescript("""
        CREATE TABLE athletes (id INTEGER PRIMARY KEY, first_name TEXT);
        INSERT INTO athletes (id, first_name) VALUES (1, 'Alex');
    """)
    _create_fueliq_tables(conn)
    conn.commit()
    return conn


def test_fueliq_tables_are_created():
    conn = _mk_conn()
    conn.executescript("CREATE TABLE athletes (id INTEGER PRIMARY KEY);")
    _create_fueliq_tables(conn)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'fueliq_%'"
        ).fetchall()
    }
    assert tables == {
        "fueliq_lessons",
        "fueliq_questions",
        "fueliq_athlete_progress",
        "fueliq_lesson_completions",
        "fueliq_quiz_attempts",
        "fueliq_myth_verdicts",
        "fueliq_badges_earned",
    }
    conn.close()


@pytest.mark.parametrize(
    "score,expected_rank",
    [
        (50, "Rookie"),
        (99, "Rookie"),
        (100, "Starter"),
        (199, "Starter"),
        (200, "Varsity"),
        (349, "Varsity"),
        (350, "Captain"),
        (549, "Captain"),
        (550, "Pro"),
        (10000, "Pro"),
    ],
)
def test_rank_for_score_bands(score, expected_rank):
    assert fq.rank_for_score(score) == expected_rank


@pytest.mark.parametrize(
    "level,threshold",
    [(1, 0), (2, 100), (3, 200), (4, 300)],
)
def test_level_unlock_threshold(level, threshold):
    assert fq.level_unlocked(threshold, level) is True


@pytest.mark.parametrize(
    "level,threshold",
    [(2, 100), (3, 200), (4, 300)],
)
def test_level_locked_below_threshold(level, threshold):
    assert fq.level_unlocked(threshold - 1, level) is False


def test_level_1_always_unlocked_at_baseline_score():
    assert fq.level_unlocked(50, 1) is True


def test_get_progress_creates_default_row_for_new_athlete():
    conn = _fueliq_db()
    progress = fq.get_progress(1, conn)
    assert progress["score"] == 50
    assert progress["rank"] == "Rookie"
    assert progress["current_streak"] == 0
    assert progress["best_streak"] == 0
    conn.close()


def test_get_progress_is_idempotent():
    conn = _fueliq_db()
    fq.get_progress(1, conn)
    row_count = conn.execute(
        "SELECT COUNT(*) AS c FROM fueliq_athlete_progress WHERE athlete_id = 1"
    ).fetchone()["c"]
    fq.get_progress(1, conn)
    row_count_again = conn.execute(
        "SELECT COUNT(*) AS c FROM fueliq_athlete_progress WHERE athlete_id = 1"
    ).fetchone()["c"]
    assert row_count == 1
    assert row_count_again == 1
    conn.close()


def test_report_config_seeds_fueliq_point_values():
    conn = _mk_conn()
    _create_report_config(conn)
    rows = {
        r["key"]: r["value"]
        for r in conn.execute(
            "SELECT key, value FROM report_config WHERE key LIKE 'fueliq_%'"
        ).fetchall()
    }
    assert rows == {
        "fueliq_lesson_points": 10.0,
        "fueliq_perfect_quiz_bonus": 5.0,
        "fueliq_myth_points": 10.0,
        "fueliq_streak_milestone_bonus": 15.0,
        "fueliq_review_points": 5.0,
    }
    conn.close()


def test_seed_placeholder_content_creates_lessons_and_myth():
    conn = _fueliq_db()
    fq.seed_placeholder_content(conn)
    lessons = conn.execute(
        "SELECT title, level, is_myth, review_status FROM fueliq_lessons WHERE is_myth = 0"
    ).fetchall()
    myths = conn.execute(
        "SELECT title, verdict, review_status FROM fueliq_lessons WHERE is_myth = 1"
    ).fetchall()
    assert len(lessons) == 2
    assert len(myths) == 1
    # Placeholder content is never pre-approved — the RDN sign-off gate (spec §11.1)
    # must be a deliberate, separate action, not an accident of seeding.
    assert all(r["review_status"] == "draft" for r in lessons + myths)
    assert all(r["level"] == 1 for r in lessons)
    conn.close()


def test_seed_placeholder_content_is_idempotent():
    conn = _fueliq_db()
    fq.seed_placeholder_content(conn)
    fq.seed_placeholder_content(conn)
    count = conn.execute("SELECT COUNT(*) AS c FROM fueliq_lessons").fetchone()["c"]
    assert count == 3
    conn.close()
