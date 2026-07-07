"""Unit tests for the Fuel IQ streak (api/services/fueliq_streak.py).

A genuinely separate streak from api/services/streak_service.py's meal-
confirmation streak — "did you log meals" and "did you learn something" are
different behaviors and shouldn't be conflated (see the Fuel IQ plan's Q5).
"""

import sqlite3
from datetime import date, timedelta

import pytest

from api.services.db_migrations import _create_fueliq_tables, _create_report_config
from api.services import fueliq_streak as fs


def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _fueliq_db():
    conn = _mk_conn()
    conn.executescript("""
        CREATE TABLE athletes (id INTEGER PRIMARY KEY, first_name TEXT);
        INSERT INTO athletes (id, first_name) VALUES (1, 'Alex');
    """)
    _create_fueliq_tables(conn)
    _create_report_config(conn)
    conn.commit()
    return conn


def _lesson_completion(conn, athlete_id, completed_at):
    lesson_id = conn.execute(
        "INSERT INTO fueliq_lessons "
        "(level, order_in_level, is_myth, title, hook, fact_body, takeaway, source_citation, review_status) "
        "VALUES (1, 1, 0, 'L', 'hook', 'fact', 'takeaway', 'cite', 'approved')"
    ).lastrowid
    conn.execute(
        "INSERT INTO fueliq_lesson_completions (athlete_id, lesson_id, points_earned, completed_at) "
        "VALUES (?, ?, 10, ?)",
        (athlete_id, lesson_id, completed_at),
    )
    conn.commit()


def _myth_verdict(conn, athlete_id, answered_at):
    lesson_id = conn.execute(
        "INSERT INTO fueliq_lessons "
        "(level, order_in_level, is_myth, title, hook, verdict, science_text, source_citation, review_status) "
        "VALUES (4, 1, 1, 'M', 'hook', 'myth', 'science', 'cite', 'approved')"
    ).lastrowid
    conn.execute(
        "INSERT INTO fueliq_myth_verdicts (athlete_id, lesson_id, guess, correct, answered_at) "
        "VALUES (?, ?, 'myth', 1, ?)",
        (athlete_id, lesson_id, answered_at),
    )
    conn.commit()


def test_qualifying_dates_from_lesson_completions():
    conn = _fueliq_db()
    _lesson_completion(conn, 1, "2026-06-10 10:00:00")
    _lesson_completion(conn, 1, "2026-06-11 10:00:00")
    assert fs._qualifying_dates(1, conn) == {"2026-06-10", "2026-06-11"}
    conn.close()


def test_qualifying_dates_union_with_myth_verdicts():
    conn = _fueliq_db()
    _lesson_completion(conn, 1, "2026-06-10 10:00:00")
    _myth_verdict(conn, 1, "2026-06-12 10:00:00")
    assert fs._qualifying_dates(1, conn) == {"2026-06-10", "2026-06-12"}
    conn.close()


def test_current_streak_counts_consecutive_days():
    conn = _fueliq_db()
    today = date(2026, 6, 17)
    for days_ago in range(3):
        d = (today - timedelta(days=days_ago)).isoformat()
        _lesson_completion(conn, 1, f"{d} 10:00:00")
    assert fs.compute_current_streak(1, conn, today)["current"] == 3
    conn.close()


def test_no_activity_is_zero_streak():
    conn = _fueliq_db()
    assert fs.compute_current_streak(1, conn, date(2026, 6, 17))["current"] == 0
    conn.close()


def test_freeze_bridges_one_missed_day():
    conn = _fueliq_db()
    today = date(2026, 6, 17)
    _lesson_completion(conn, 1, f"{today.isoformat()} 10:00:00")
    # 06-16 missed
    _lesson_completion(conn, 1, f"{(today - timedelta(days=2)).isoformat()} 10:00:00")
    result = fs.compute_current_streak(1, conn, today)
    assert result["current"] == 2
    conn.close()


def test_register_activity_fires_milestone_at_seven_days():
    conn = _fueliq_db()
    today = date(2026, 6, 17)
    for days_ago in range(6, -1, -1):  # 7 consecutive days ending today
        d = (today - timedelta(days=days_ago)).isoformat()
        _lesson_completion(conn, 1, f"{d} 10:00:00")

    result = fs.register_activity(1, conn, today)
    assert result["current"] == 7
    assert result["just_reached_milestone"] == 7
    conn.close()


def test_register_activity_awards_milestone_bonus_points_once():
    conn = _fueliq_db()
    today = date(2026, 6, 17)
    for days_ago in range(6, -1, -1):
        d = (today - timedelta(days=days_ago)).isoformat()
        _lesson_completion(conn, 1, f"{d} 10:00:00")

    from api.services import fueliq_service as fq
    score_before = fq.get_progress(1, conn)["score"]
    fs.register_activity(1, conn, today)
    score_after = fq.get_progress(1, conn)["score"]
    assert score_after == score_before + 15  # fueliq_streak_milestone_bonus

    # Registering again the same day must not re-award the bonus.
    fs.register_activity(1, conn, today)
    assert fq.get_progress(1, conn)["score"] == score_after
    conn.close()


def test_register_activity_updates_progress_streak_columns():
    conn = _fueliq_db()
    today = date(2026, 6, 17)
    _lesson_completion(conn, 1, f"{today.isoformat()} 10:00:00")
    fs.register_activity(1, conn, today)

    from api.services import fueliq_service as fq
    progress = fq.get_progress(1, conn)
    assert progress["current_streak"] == 1
    assert progress["best_streak"] == 1
    conn.close()
