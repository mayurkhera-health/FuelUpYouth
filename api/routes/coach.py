from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.database import get_conn
from api.services.coach_service import assemble_context, call_coach_api, call_general_coach_api

router = APIRouter()


@router.get("/context")
def get_context(
    athlete_id: int,
    window_key: str,
    window_label: str,
    window_time: str,
    category_key: str,
    category_label: str,
    plan_date: str,
):
    conn = get_conn()
    try:
        return assemble_context(
            athlete_id=athlete_id,
            window_key=window_key,
            window_label=window_label,
            window_time=window_time,
            category_key=category_key,
            category_label=category_label,
            plan_date=plan_date,
            conn=conn,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    finally:
        conn.close()


class _Msg(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    athlete_id: int
    window_key: str
    window_label: str
    window_time: str
    category_key: str
    category_label: str
    plan_date: str
    persona: str = "athlete"
    messages: list[_Msg]


@router.post("/chat")
def post_chat(body: ChatRequest):
    conn = get_conn()
    try:
        ctx = assemble_context(
            athlete_id=body.athlete_id,
            window_key=body.window_key,
            window_label=body.window_label,
            window_time=body.window_time,
            category_key=body.category_key,
            category_label=body.category_label,
            plan_date=body.plan_date,
            conn=conn,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    finally:
        conn.close()

    raw_messages = [{"role": m.role, "content": m.content} for m in body.messages]
    response_text = call_coach_api(ctx, raw_messages, body.persona)
    return {"response": response_text}


class GeneralChatRequest(BaseModel):
    athlete_id: int
    persona: str = "parent"
    messages: list[_Msg]


@router.post("/general-chat")
def post_general_chat(body: GeneralChatRequest):
    conn = get_conn()
    try:
        athlete = conn.execute("SELECT * FROM athletes WHERE id = ?", (body.athlete_id,)).fetchone()
        if not athlete:
            raise HTTPException(404, "Athlete not found")
        athlete_dict = dict(athlete)
    finally:
        conn.close()

    raw_messages = [{"role": m.role, "content": m.content} for m in body.messages]
    response_text = call_general_coach_api(athlete_dict, raw_messages, body.persona)
    return {"response": response_text}


class CoachFeedbackRequest(BaseModel):
    rating: str  # "up" | "down"
    question: str | None = None
    answer_excerpt: str | None = None
    window_key: str | None = None
    recipe_intent: int | None = None
    role_hint: str | None = None
    reason: str | None = None  # nullable now; preset reason chips are a later frontend add


@router.post("/feedback", status_code=201)
def post_feedback(body: CoachFeedbackRequest):
    """Log a thumbs up/down on a coach answer. High-volume telemetry — no email."""
    if body.rating not in ("up", "down"):
        raise HTTPException(400, "rating must be 'up' or 'down'.")
    conn = get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO coach_feedback
                   (rating, question, answer_excerpt, window_key, recipe_intent, role_hint, reason)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (body.rating, body.question, body.answer_excerpt, body.window_key,
             body.recipe_intent, body.role_hint, body.reason),
        )
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}
    finally:
        conn.close()
