from fastapi import APIRouter, HTTPException
from typing import List
from api.models import MealLogCreate, MealLogResponse
from api.database import get_conn

router = APIRouter()


@router.post("/", response_model=MealLogResponse, status_code=201)
def log_meal(data: MealLogCreate):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM athletes WHERE id = ?", (data.athlete_id,)).fetchone():
            raise HTTPException(404, "Athlete not found.")
        conn.execute(
            """INSERT INTO meal_logs
               (athlete_id, log_method, description, calories, carbs_g, protein_g,
                fat_g, iron_mg, calcium_mg, water_oz, edamam_raw)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data.athlete_id, data.log_method, data.description, data.calories,
             data.carbs_g, data.protein_g, data.fat_g, data.iron_mg,
             data.calcium_mg, data.water_oz, data.edamam_raw),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM meal_logs WHERE rowid = last_insert_rowid()").fetchone()
        return dict(row)
    finally:
        conn.close()


@router.get("/athlete/{athlete_id}", response_model=List[MealLogResponse])
def get_meals(athlete_id: int, date: str = None):
    conn = get_conn()
    try:
        if date:
            rows = conn.execute(
                "SELECT * FROM meal_logs WHERE athlete_id = ? AND DATE(logged_at) = ? ORDER BY logged_at",
                (athlete_id, date),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM meal_logs WHERE athlete_id = ? ORDER BY logged_at DESC LIMIT 50",
                (athlete_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.delete("/{meal_id}")
def delete_meal(meal_id: int):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM meal_logs WHERE id = ?", (meal_id,)).fetchone():
            raise HTTPException(404, "Meal log not found.")
        conn.execute("DELETE FROM meal_logs WHERE id = ?", (meal_id,))
        conn.commit()
        return {"message": "Meal log deleted.", "meal_id": meal_id}
    finally:
        conn.close()
