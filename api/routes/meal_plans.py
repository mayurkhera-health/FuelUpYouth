from fastapi import APIRouter, HTTPException, Query
from datetime import date, timedelta
from api.models import MealPlanSlotUpdate, MealPlanLogSlot, MealPlanGenerateRequest
from api.database import get_conn
from api.services import recipe_db, claude_ai
from api.routes.nutrition import get_targets  # reuse target calculation

router = APIRouter()

SLOTS_BY_EVENT = {
    "rest":       ["breakfast", "lunch", "dinner", "snack"],
    "practice":   ["breakfast", "pre-game", "post-game-recovery", "dinner", "bedtime-snack"],
    "training":   ["breakfast", "pre-game", "post-game-recovery", "dinner", "bedtime-snack"],
    "strength":   ["breakfast", "pre-game", "post-game-recovery", "dinner", "bedtime-snack"],
    "game":       ["pre-game", "pre-game-snack", "halftime", "post-game-recovery", "dinner", "bedtime-snack"],
    "tournament": ["pre-game", "pre-game-snack", "halftime", "between-games", "post-game-recovery", "dinner", "bedtime-snack"],
}

SLOT_TO_CATEGORY = {
    "breakfast":          "practice",
    "lunch":              "meal-prep",
    "dinner":             "practice",
    "snack":              "pre-game-snack",
    "pre-game":           "pre-game",
    "pre-game-snack":     "pre-game-snack",
    "halftime":           "halftime",
    "post-game-recovery": "post-game-recovery",
    "between-games":      "tournament",
    "bedtime-snack":      "tournament",
}

SLOT_LABELS = {
    "breakfast":          "Breakfast",
    "lunch":              "Lunch",
    "dinner":             "Dinner",
    "snack":              "Snack",
    "pre-game":           "Pre-Game Meal",
    "pre-game-snack":     "Pre-Game Snack",
    "halftime":           "Halftime Fuel",
    "post-game-recovery": "Post-Game Recovery",
    "between-games":      "Between Games",
    "bedtime-snack":      "Bedtime Snack",
}

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _get_monday(date_str: str) -> date:
    d = date.fromisoformat(date_str)
    return d - timedelta(days=d.weekday())


def _build_week(athlete_id: int, week_start: date, conn) -> list:
    days = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        date_str = day_date.isoformat()

        # Get event for this day
        event = conn.execute(
            "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time LIMIT 1",
            (athlete_id, date_str),
        ).fetchone()

        event_type = dict(event)["event_type"] if event else "rest"
        event_name = dict(event)["event_name"] if event else None

        # Get calorie target
        target_row = conn.execute(
            "SELECT total_calories FROM daily_targets WHERE athlete_id = ? AND target_date = ?",
            (athlete_id, date_str),
        ).fetchone()
        calorie_target = dict(target_row)["total_calories"] if target_row else None

        # Get filled slots from DB
        rows = conn.execute(
            "SELECT * FROM meal_plans WHERE athlete_id = ? AND plan_date = ?",
            (athlete_id, date_str),
        ).fetchall()
        filled = {dict(r)["slot_name"]: dict(r) for r in rows}

        # Build slot list from event type
        slot_names = SLOTS_BY_EVENT.get(event_type, SLOTS_BY_EVENT["rest"])
        slots = []
        planned_calories = 0
        for slot_name in slot_names:
            f = filled.get(slot_name)
            slot = {
                "slot_name":       slot_name,
                "display_label":   SLOT_LABELS.get(slot_name, slot_name),
                "recipe_category": SLOT_TO_CATEGORY.get(slot_name, "practice"),
                "recipe_id":       f["recipe_id"]   if f else None,
                "recipe_name":     f["recipe_name"] if f else None,
                "calories":        f["calories"]    if f else None,
                "carbs_g":         f["carbs_g"]     if f else None,
                "protein_g":       f["protein_g"]   if f else None,
                "fat_g":           f["fat_g"]       if f else None,
                "is_ai_generated": bool(f["is_ai_generated"]) if f else False,
                "logged":          bool(f["logged"]) if f else False,
            }
            if f and f["calories"]:
                planned_calories += f["calories"]
            slots.append(slot)

        days.append({
            "date":             date_str,
            "day_label":        DAY_LABELS[i],
            "event_type":       event_type,
            "event_name":       event_name,
            "calorie_target":   calorie_target,
            "planned_calories": round(planned_calories),
            "slots":            slots,
        })
    return days


@router.get("/{athlete_id}")
def get_meal_plan(athlete_id: int, week_start: str = Query(None)):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM athletes WHERE id = ?", (athlete_id,)).fetchone():
            raise HTTPException(404, "Athlete not found.")

        if week_start:
            monday = _get_monday(week_start)
        else:
            today = date.today()
            monday = today - timedelta(days=today.weekday())

        days = _build_week(athlete_id, monday, conn)
        return {"athlete_id": athlete_id, "week_start": monday.isoformat(), "days": days}
    finally:
        conn.close()


@router.put("/{athlete_id}/slot")
def set_slot(athlete_id: int, data: MealPlanSlotUpdate):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM athletes WHERE id = ?", (athlete_id,)).fetchone():
            raise HTTPException(404, "Athlete not found.")

        recipe = recipe_db.get_recipe_by_id(data.recipe_id)
        if not recipe:
            raise HTTPException(404, f"Recipe {data.recipe_id} not found.")

        m = recipe["macros"]
        conn.execute(
            """INSERT INTO meal_plans
               (athlete_id, plan_date, slot_name, recipe_id, recipe_name,
                calories, carbs_g, protein_g, fat_g, is_ai_generated, logged)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
               ON CONFLICT(athlete_id, plan_date, slot_name)
               DO UPDATE SET recipe_id=excluded.recipe_id, recipe_name=excluded.recipe_name,
                 calories=excluded.calories, carbs_g=excluded.carbs_g,
                 protein_g=excluded.protein_g, fat_g=excluded.fat_g,
                 is_ai_generated=0, logged=0""",
            (athlete_id, data.plan_date, data.slot_name, data.recipe_id,
             recipe["name"], m["calories"], m["carbs_g"], m["protein_g"], m["fat_g"]),
        )
        conn.commit()
        return {
            "slot_name": data.slot_name, "recipe_id": data.recipe_id,
            "recipe_name": recipe["name"], "calories": m["calories"],
            "carbs_g": m["carbs_g"], "protein_g": m["protein_g"], "fat_g": m["fat_g"],
            "is_ai_generated": False, "logged": False,
        }
    finally:
        conn.close()


@router.delete("/{athlete_id}/slot")
def clear_slot(athlete_id: int, plan_date: str = Query(...), slot_name: str = Query(...)):
    conn = get_conn()
    try:
        conn.execute(
            "DELETE FROM meal_plans WHERE athlete_id = ? AND plan_date = ? AND slot_name = ?",
            (athlete_id, plan_date, slot_name),
        )
        conn.commit()
        return {"cleared": True}
    finally:
        conn.close()


@router.post("/{athlete_id}/log-slot")
def log_slot(athlete_id: int, data: MealPlanLogSlot):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM meal_plans WHERE athlete_id = ? AND plan_date = ? AND slot_name = ?",
            (athlete_id, data.plan_date, data.slot_name),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Planned slot not found.")
        r = dict(row)
        if r["logged"]:
            raise HTTPException(400, "This meal has already been logged.")

        # Insert into meal_logs
        conn.execute(
            """INSERT INTO meal_logs
               (athlete_id, log_method, description, calories, carbs_g, protein_g, fat_g)
               VALUES (?, 'meal-plan', ?, ?, ?, ?, ?)""",
            (athlete_id, r["recipe_name"], r["calories"], r["carbs_g"], r["protein_g"], r["fat_g"]),
        )
        meal_log_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Mark slot as logged
        conn.execute(
            "UPDATE meal_plans SET logged = 1 WHERE athlete_id = ? AND plan_date = ? AND slot_name = ?",
            (athlete_id, data.plan_date, data.slot_name),
        )
        conn.commit()
        return {"logged": True, "meal_log_id": meal_log_id}
    finally:
        conn.close()


@router.post("/generate")
def generate_plan(data: MealPlanGenerateRequest):
    conn = get_conn()
    try:
        athlete_row = conn.execute("SELECT * FROM athletes WHERE id = ?", (data.athlete_id,)).fetchone()
        if not athlete_row:
            raise HTTPException(404, "Athlete not found.")
        athlete = dict(athlete_row)

        monday = _get_monday(data.week_start)

        # Build week schedule context for Claude
        week_schedule = []
        for i in range(7):
            day_date = monday + timedelta(days=i)
            date_str = day_date.isoformat()
            event = conn.execute(
                "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time LIMIT 1",
                (data.athlete_id, date_str),
            ).fetchone()
            event_type = dict(event)["event_type"] if event else "rest"
            target_row = conn.execute(
                "SELECT total_calories FROM daily_targets WHERE athlete_id = ? AND target_date = ?",
                (data.athlete_id, date_str),
            ).fetchone()
            calorie_target = dict(target_row)["total_calories"] if target_row else 2000

            slot_names = SLOTS_BY_EVENT.get(event_type, SLOTS_BY_EVENT["rest"])
            slots = [{"slot_name": s, "recipe_category": SLOT_TO_CATEGORY.get(s, "practice")} for s in slot_names]

            week_schedule.append({
                "date": date_str,
                "day_label": DAY_LABELS[i],
                "event_type": event_type,
                "slots": slots,
                "calorie_target": calorie_target,
            })

        # Filter recipes by athlete restrictions
        athlete_allergens = [a.strip().lower() for a in (athlete.get("allergies") or "").split(",") if a.strip()]
        athlete_diets = [d.strip().lower() for d in (athlete.get("dietary_restrictions") or "").split(",") if d.strip()]
        safe_recipes = [
            r for r in recipe_db.RECIPES
            if not any(a in [x.lower() for x in r["allergens"]] for a in athlete_allergens)
        ]

        # Call Claude AI
        ai_result = claude_ai.prompt6_weekly_meal_plan(athlete, week_schedule, safe_recipes)
        plan = ai_result.get("plan", {})

        # Bulk upsert
        for date_str, slot_map in plan.items():
            for slot_name, recipe_id in slot_map.items():
                if not recipe_id:
                    continue
                recipe = recipe_db.get_recipe_by_id(recipe_id)
                if not recipe:
                    continue
                # Skip if slot occupied and overwrite_existing=False
                if not data.overwrite_existing:
                    existing = conn.execute(
                        "SELECT id FROM meal_plans WHERE athlete_id = ? AND plan_date = ? AND slot_name = ?",
                        (data.athlete_id, date_str, slot_name),
                    ).fetchone()
                    if existing:
                        continue
                m = recipe["macros"]
                conn.execute(
                    """INSERT INTO meal_plans
                       (athlete_id, plan_date, slot_name, recipe_id, recipe_name,
                        calories, carbs_g, protein_g, fat_g, is_ai_generated, logged)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
                       ON CONFLICT(athlete_id, plan_date, slot_name)
                       DO UPDATE SET recipe_id=excluded.recipe_id, recipe_name=excluded.recipe_name,
                         calories=excluded.calories, carbs_g=excluded.carbs_g,
                         protein_g=excluded.protein_g, fat_g=excluded.fat_g,
                         is_ai_generated=1, logged=0""",
                    (data.athlete_id, date_str, slot_name, recipe_id,
                     recipe["name"], m["calories"], m["carbs_g"], m["protein_g"], m["fat_g"]),
                )
        conn.commit()

        # Return full week
        days = _build_week(data.athlete_id, monday, conn)
        return {
            "athlete_id": data.athlete_id,
            "week_start": monday.isoformat(),
            "days": days,
            "ai_reasoning": ai_result.get("reasoning", ""),
        }
    finally:
        conn.close()
