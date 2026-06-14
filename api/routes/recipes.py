from typing import Optional
from fastapi import APIRouter, HTTPException
from api.models import RecipeSwapRequest, RecipeGenerateRequest
from api.services import recipe_db, claude_ai, recipe_generator
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


@router.get("/")
def list_recipes(category: Optional[str] = None, dietary: Optional[str] = None, avoid_allergens: Optional[str] = None):
    dietary_list = dietary.split(",") if dietary else None
    allergen_list = avoid_allergens.split(",") if avoid_allergens else None
    recipes = recipe_db.get_recipes(category=category, dietary=dietary_list, allergens_to_avoid=allergen_list)
    return {"recipes": recipes, "count": len(recipes), "powered_by": "Edamam"}


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
        raise HTTPException(500, f"Recipe generation failed: {e}")


@router.get("/{recipe_id}")
def get_recipe(recipe_id: str):
    recipe = recipe_db.get_recipe_by_id(recipe_id.upper())
    if not recipe:
        raise HTTPException(404, f"Recipe {recipe_id} not found.")
    return {**recipe, "powered_by": "Powered by Edamam — developer.edamam.com"}


@router.post("/swap")
def picky_eater_swap(req: RecipeSwapRequest):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (req.athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        result = claude_ai.prompt4_recipe_swap(dict(row), req.disliked_recipe, req.meal_timing_category)
        result["attribution"] = "Nutrition data — Powered by Edamam (developer.edamam.com)"
        return result
    finally:
        conn.close()
