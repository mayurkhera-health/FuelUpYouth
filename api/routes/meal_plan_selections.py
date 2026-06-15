from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from api.database import get_conn

router = APIRouter()


class ItemIn(BaseModel):
    athlete_id: int
    plan_date: str
    text: str
    added_by: str = "parent"

    @field_validator("added_by")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("parent", "athlete"):
            raise ValueError("added_by must be 'parent' or 'athlete'")
        return v

    @field_validator("text")
    @classmethod
    def non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text cannot be empty")
        return v


@router.post("/windows/{window_key}/items", status_code=201)
def add_item(window_key: str, body: ItemIn):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO meal_plan_selections (athlete_id, plan_date, window_key, item_text, added_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (body.athlete_id, body.plan_date, window_key, body.text, body.added_by),
        )
        conn.commit()
        item_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {"id": item_id, "text": body.text, "added_by": body.added_by}
    finally:
        conn.close()


@router.delete("/windows/{window_key}/items/{item_id}", status_code=204)
def remove_item(window_key: str, item_id: int):
    conn = get_conn()
    try:
        if not conn.execute(
            "SELECT id FROM meal_plan_selections WHERE id = ?", (item_id,)
        ).fetchone():
            raise HTTPException(404, "Item not found")
        conn.execute("DELETE FROM meal_plan_selections WHERE id = ?", (item_id,))
        conn.commit()
        return None
    finally:
        conn.close()
