from datetime import date as _date, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from api.models import RecipeSwapRequest, RecipeGenerateRequest
from api.services import recipe_db, claude_ai, recipe_generator
from api.services.recipe_db import PROFILE_TO_DB_CATEGORIES
from api.database import get_conn

router = APIRouter()


def _parse_allergies(raw) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return [a.strip() for a in raw if a and str(a).strip().lower() != "none"]
    return [a.strip() for a in str(raw).split(",") if a.strip().lower() != "none"]


def _parse_dietary(raw) -> list:
    if not raw:
        return []
    if isinstance(raw, list):
        return [d.strip() for d in raw if d and str(d).strip().lower() != "none"]
    return [d.strip() for d in str(raw).split(",") if d.strip().lower() != "none"]


def _week_start(date_str: str) -> str:
    d = _date.fromisoformat(date_str)
    return (d - timedelta(days=d.weekday())).isoformat()


def _get_or_create_recipe_list(athlete_id: int, week_start: str, conn) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO recipe_lists (athlete_id, week_start) VALUES (?, ?)",
        (athlete_id, week_start),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM recipe_lists WHERE athlete_id = ? AND week_start = ?",
        (athlete_id, week_start),
    ).fetchone()[0]


@router.get("/")
def list_recipes(category: Optional[str] = None, dietary: Optional[str] = None, avoid_allergens: Optional[str] = None):
    dietary_list = dietary.split(",") if dietary else None
    allergen_list = avoid_allergens.split(",") if avoid_allergens else None
    recipes = recipe_db.get_recipes(category=category, dietary=dietary_list, allergens_to_avoid=allergen_list)
    return {"recipes": recipes, "count": len(recipes), "powered_by": "FuelUp Recipe Library"}


@router.get("/categories")
def list_categories():
    from api.services.recipe_categories import RECIPE_CATEGORY_PROFILES, CATEGORY_ALIASES
    keys = sorted(set(RECIPE_CATEGORY_PROFILES.keys()) | set(CATEGORY_ALIASES.keys()))
    return {"categories": keys}


@router.post("/generate")
def generate_recipe(req: RecipeGenerateRequest):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (req.athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        athlete = dict(row)
    finally:
        conn.close()

    allergies = req.allergies or _parse_allergies(athlete.get("allergies"))
    dietary = req.dietary_restrictions or _parse_dietary(athlete.get("dietary_restrictions"))

    try:
        return recipe_generator.generate_recipe(
            req.category,
            allergies=allergies,
            dietary_restrictions=dietary,
            athlete=athlete,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(500, f"Recipe selection failed: {e}")


# Must be registered before /{recipe_id} — FastAPI matches in order and /for-window
# is a single-segment path that would otherwise be caught by the parameterised route.
@router.get("/for-window")
def get_recipes_for_window(athlete_id: int = Query(...), window_key: str = Query(...)):
    if window_key not in PROFILE_TO_DB_CATEGORIES:
        raise HTTPException(400, f"Unrecognised window_key '{window_key}'.")
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        athlete = dict(row)
    finally:
        conn.close()
    allergies = _parse_allergies(athlete.get("allergies"))
    recipes = recipe_db.get_valid_recipes(profile_key=window_key, allergies=allergies)
    return {"recipes": recipes, "window_key": window_key, "count": len(recipes)}


@router.get("/selections/week")
def get_week_selections(athlete_id: int = Query(...), week_start: str = Query(...)):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM recipe_selections WHERE athlete_id = ? AND week_start = ?"
            " ORDER BY selection_date, fueling_window_key",
            (athlete_id, week_start),
        ).fetchall()
        selections = []
        for row in rows:
            s = dict(row)
            s["recipe"] = recipe_db.get_recipe_by_id(s["recipe_id"])
            selections.append(s)
        return {"week_start": week_start, "selections": selections}
    finally:
        conn.close()


class _SelectionCreate(BaseModel):
    athlete_id: int
    selection_date: str
    fueling_window_key: str
    recipe_id: str
    servings: int = 1


@router.post("/selections", status_code=201)
def create_selection(data: _SelectionCreate):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM athletes WHERE id = ?", (data.athlete_id,)).fetchone():
            raise HTTPException(404, "Athlete not found.")
        if not recipe_db.get_recipe_by_id(data.recipe_id.upper()):
            raise HTTPException(404, f"Recipe {data.recipe_id} not found.")
        ws = _week_start(data.selection_date)
        conn.execute(
            """INSERT OR REPLACE INTO recipe_selections
               (athlete_id, week_start, selection_date, fueling_window_key, recipe_id, servings,
                updated_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
            (data.athlete_id, ws, data.selection_date, data.fueling_window_key,
             data.recipe_id.upper(), data.servings),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM recipe_selections WHERE rowid = last_insert_rowid()"
        ).fetchone()
        return {"selection": dict(row)}
    finally:
        conn.close()


@router.delete("/selections/{selection_id}")
def delete_selection(selection_id: int, athlete_id: int = Query(...)):
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM recipe_selections WHERE id = ? AND athlete_id = ?",
            (selection_id, athlete_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Selection not found.")
        conn.execute("DELETE FROM recipe_selections WHERE id = ?", (selection_id,))
        conn.commit()
        return {"deleted": True}
    finally:
        conn.close()


class _SyncGroceryList(BaseModel):
    athlete_id: int
    week_start: str


@router.post("/selections/sync-grocery-list")
def sync_grocery_list(data: _SyncGroceryList):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM recipe_selections WHERE athlete_id = ? AND week_start = ?",
            (data.athlete_id, data.week_start),
        ).fetchall()
        list_id = _get_or_create_recipe_list(data.athlete_id, data.week_start, conn)
        added = 0
        for row in rows:
            recipe = recipe_db.get_recipe_by_id(row["recipe_id"])
            if not recipe:
                continue
            for ingredient in recipe.get("ingredients", []):
                name = ingredient.get("name", "").strip() if isinstance(ingredient, dict) else str(ingredient).strip()
                if not name:
                    continue
                result = conn.execute(
                    "INSERT OR IGNORE INTO recipe_list_items (list_id, name)"
                    " VALUES (?, ?)",
                    (list_id, name),
                )
                added += result.rowcount
        conn.commit()
        return {"synced": True, "items_added": added, "week_start": data.week_start}
    finally:
        conn.close()


@router.get("/{recipe_id}")
def get_recipe(recipe_id: str):
    recipe = recipe_db.get_recipe_by_id(recipe_id.upper())
    if not recipe:
        raise HTTPException(404, f"Recipe {recipe_id} not found.")
    return {**recipe, "powered_by": "FuelUp Recipe Library"}


@router.post("/swap")
def picky_eater_swap(req: RecipeSwapRequest):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (req.athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        allergens = _parse_allergies(dict(row).get("allergies"))
        candidates = recipe_db.get_recipes(
            category=req.meal_timing_category,
            allergens_to_avoid=allergens,
        )
        result = claude_ai.prompt4_recipe_swap(
            dict(row), req.disliked_recipe, req.meal_timing_category, candidates,
        )
        result["attribution"] = "FuelUp curated recipe library"
        return result
    finally:
        conn.close()
