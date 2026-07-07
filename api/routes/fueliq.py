"""
Fuel IQ — gamified nutrition-education tab.

GET  /api/{athlete_id}/fueliq/hub
GET  /api/{athlete_id}/fueliq/lessons?level=N
GET  /api/{athlete_id}/fueliq/lessons/{lesson_id}
POST /api/{athlete_id}/fueliq/lessons/{lesson_id}/complete
POST /api/{athlete_id}/fueliq/questions/{question_id}/answer
GET  /api/{athlete_id}/fueliq/myths
POST /api/{athlete_id}/fueliq/myths/{lesson_id}/verdict

Feature-flagged (FUELIQ_ENABLED) — ships dark, mirroring plate.py/fueling_targets.py.
When off, every endpoint returns a minimal `{"enabled": False}`-shaped payload
instead of doing DB work, same convention as the Performance Plate route.
"""

from fastapi import APIRouter, HTTPException, Query

from api.database import get_conn
from api.models import FuelIQLessonComplete, FuelIQMythVerdict, FuelIQQuizAnswer
from api.services import fueliq_service as fq

router = APIRouter()

_LEVELS = (1, 2, 3, 4)


@router.get("/{athlete_id}/hub")
def get_hub(athlete_id: int):
    if not fq.fueliq_enabled():
        return {"enabled": False}

    conn = get_conn()
    try:
        progress = fq.get_progress(athlete_id, conn)
        badges = [
            r["badge_key"]
            for r in conn.execute(
                "SELECT badge_key FROM fueliq_badges_earned WHERE athlete_id = ?",
                (athlete_id,),
            ).fetchall()
        ]
        levels = [
            {"level": lvl, "unlocked": fq.level_unlocked(progress["score"], lvl)}
            for lvl in _LEVELS
        ]
    finally:
        conn.close()

    return {"enabled": True, **progress, "levels": levels, "badges_earned": badges}


@router.get("/{athlete_id}/lessons")
def list_lessons(athlete_id: int, level: int = Query(...)):
    if not fq.fueliq_enabled():
        return {"enabled": False}

    conn = get_conn()
    try:
        progress = fq.get_progress(athlete_id, conn)
        unlocked = fq.level_unlocked(progress["score"], level)
        rows = conn.execute(
            "SELECT id, title, hook, points, order_in_level FROM fueliq_lessons "
            "WHERE level = ? AND is_myth = 0 AND review_status = 'approved' "
            "ORDER BY order_in_level",
            (level,),
        ).fetchall()
        completed_ids = {
            r["lesson_id"]
            for r in conn.execute(
                "SELECT lesson_id FROM fueliq_lesson_completions WHERE athlete_id = ?",
                (athlete_id,),
            ).fetchall()
        }
    finally:
        conn.close()

    lessons = [
        {**dict(r), "completed": r["id"] in completed_ids} for r in rows
    ]
    return {"enabled": True, "level": level, "unlocked": unlocked, "lessons": lessons}


@router.get("/{athlete_id}/lessons/{lesson_id}")
def get_lesson(athlete_id: int, lesson_id: int):
    if not fq.fueliq_enabled():
        return {"enabled": False}

    conn = get_conn()
    try:
        lesson = conn.execute(
            "SELECT id, level, title, hook, fact_body, visual_ref, takeaway, points "
            "FROM fueliq_lessons WHERE id = ? AND is_myth = 0 AND review_status = 'approved'",
            (lesson_id,),
        ).fetchone()
        if not lesson:
            raise HTTPException(404, f"Lesson {lesson_id} not found")

        progress = fq.get_progress(athlete_id, conn)
        if not fq.level_unlocked(progress["score"], lesson["level"]):
            raise HTTPException(403, f"Level {lesson['level']} is not unlocked yet")

        questions = conn.execute(
            "SELECT id, question_text, option_a, option_b, option_c FROM fueliq_questions "
            "WHERE lesson_id = ? ORDER BY order_in_lesson",
            (lesson_id,),
        ).fetchall()
    finally:
        conn.close()

    return {"enabled": True, **dict(lesson), "questions": [dict(q) for q in questions]}


@router.post("/{athlete_id}/lessons/{lesson_id}/complete")
def complete_lesson(athlete_id: int, lesson_id: int, body: FuelIQLessonComplete):
    if not fq.fueliq_enabled():
        return {"enabled": False}

    conn = get_conn()
    try:
        exists = conn.execute(
            "SELECT 1 FROM fueliq_lessons WHERE id = ? AND is_myth = 0", (lesson_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(404, f"Lesson {lesson_id} not found")
        result = fq.complete_lesson(athlete_id, lesson_id, conn, perfect_quiz=body.perfect_quiz)
    finally:
        conn.close()

    return {"enabled": True, **result}


@router.post("/{athlete_id}/questions/{question_id}/answer")
def answer_question(athlete_id: int, question_id: int, body: FuelIQQuizAnswer):
    if not fq.fueliq_enabled():
        return {"enabled": False}

    conn = get_conn()
    try:
        exists = conn.execute(
            "SELECT 1 FROM fueliq_questions WHERE id = ?", (question_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(404, f"Question {question_id} not found")
        result = fq.submit_quiz_answer(athlete_id, question_id, body.selected_option, conn)
    finally:
        conn.close()

    return {"enabled": True, **result}


@router.get("/{athlete_id}/myths")
def list_myths(athlete_id: int):
    if not fq.fueliq_enabled():
        return {"enabled": False}

    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT id, title, hook FROM fueliq_lessons "
            "WHERE is_myth = 1 AND review_status = 'approved' ORDER BY id"
        ).fetchall()
        verdicts = {
            r["lesson_id"]: {"guess": r["guess"], "correct": bool(r["correct"])}
            for r in conn.execute(
                "SELECT lesson_id, guess, correct FROM fueliq_myth_verdicts WHERE athlete_id = ?",
                (athlete_id,),
            ).fetchall()
        }
    finally:
        conn.close()

    myths = [
        {**dict(r), "answered": r["id"] in verdicts, **verdicts.get(r["id"], {})}
        for r in rows
    ]
    return {"enabled": True, "myths": myths}


@router.post("/{athlete_id}/myths/{lesson_id}/verdict")
def submit_myth_verdict(athlete_id: int, lesson_id: int, body: FuelIQMythVerdict):
    if not fq.fueliq_enabled():
        return {"enabled": False}

    conn = get_conn()
    try:
        exists = conn.execute(
            "SELECT 1 FROM fueliq_lessons WHERE id = ? AND is_myth = 1", (lesson_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(404, f"Myth {lesson_id} not found")
        result = fq.submit_myth_verdict(athlete_id, lesson_id, body.guess, conn)
    finally:
        conn.close()

    return {"enabled": True, **result}
