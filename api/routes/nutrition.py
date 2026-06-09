import json
from datetime import date as dt_date
from fastapi import APIRouter, HTTPException
from api.database import get_conn
from api.models import SweatOutputRequest
from api.services import nutrition_calc, weather as weather_svc, meal_timing

router = APIRouter()


@router.get("/targets/{athlete_id}")
def get_targets(athlete_id: int, date: str = None, event_type: str = None):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        athlete = dict(row)
        target_date = date or str(dt_date.today())

        if not event_type:
            events = conn.execute(
                "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time",
                (athlete_id, target_date),
            ).fetchall()
            event_type = dict(events[0])["event_type"] if events else "rest"

        targets = nutrition_calc.calc_daily_targets(athlete, event_type)
        targets["athlete_id"] = athlete_id
        targets["target_date"] = target_date

        conn.execute(
            """INSERT OR REPLACE INTO daily_targets
               (athlete_id, target_date, event_type, total_calories,
                carbs_g_min, carbs_g_max, protein_g_min, protein_g_max,
                fat_g_min, fat_g_max, iron_mg, calcium_mg,
                hydration_oz_min, hydration_oz_max, lea_alert, targets_raw)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (athlete_id, target_date, targets["event_type"], targets["total_calories"],
             targets["carbs_g_min"], targets["carbs_g_max"],
             targets["protein_g_min"], targets["protein_g_max"],
             targets["fat_g_min"], targets["fat_g_max"],
             targets["iron_mg"], targets["calcium_mg"],
             targets["hydration_oz_min"], targets["hydration_oz_max"],
             targets["lea_alert"], json.dumps(targets)),
        )
        conn.commit()
        return targets
    finally:
        conn.close()


@router.post("/sweat")
def calculate_sweat(req: SweatOutputRequest):
    conn = get_conn()
    try:
        athlete = conn.execute("SELECT * FROM athletes WHERE id = ?", (req.athlete_id,)).fetchone()
        if not athlete:
            raise HTTPException(404, "Athlete not found.")
        event = conn.execute("SELECT * FROM events WHERE id = ?", (req.event_id,)).fetchone()
        if not event:
            raise HTTPException(404, "Event not found.")
        weather = weather_svc.get_weather(req.city)
        return weather_svc.calc_sweat_output(dict(athlete), dict(event), weather)
    finally:
        conn.close()


@router.get("/timing/{athlete_id}")
def get_meal_timing(athlete_id: int, date: str = None, event_type: str = None):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM athletes WHERE id = ?", (athlete_id,)).fetchone():
            raise HTTPException(404, "Athlete not found.")
        target_date = date or str(dt_date.today())
        start_time = None

        if not event_type:
            events = conn.execute(
                "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time",
                (athlete_id, target_date),
            ).fetchall()
            if events:
                e = dict(events[0])
                event_type = e["event_type"]
                start_time = e.get("start_time")
            else:
                event_type = "rest"
        else:
            events = conn.execute(
                "SELECT start_time FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time",
                (athlete_id, target_date),
            ).fetchall()
            if events:
                start_time = dict(events[0]).get("start_time")

        return meal_timing.get_meal_timing_protocol(event_type, target_date, start_time)
    finally:
        conn.close()


from pydantic import BaseModel
from api.services import claude_ai

class MacroEstimateRequest(BaseModel):
    athlete_id: int
    description: str

@router.post("/estimate")
def estimate_macros(data: MacroEstimateRequest):
    if not data.description or len(data.description.strip()) < 3:
        raise HTTPException(400, "Please provide a meal description.")
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (data.athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        athlete = dict(row)
    finally:
        conn.close()
    return claude_ai.prompt7_estimate_macros(data.description.strip(), athlete)
