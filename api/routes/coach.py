from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.database import get_conn
from api.services.coach_service import assemble_context, call_coach_api

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
