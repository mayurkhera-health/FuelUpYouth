from typing import Optional
from fastapi import APIRouter, HTTPException
from api.models import RecipeSwapRequest
from api.services import recipe_db, claude_ai
from api.database import get_conn

router = APIRouter()


@router.get("/")
def list_recipes(category: Optional[str] = None, dietary: Optional[str] = None, avoid_allergens: Optional[str] = None):
    dietary_list = dietary.split(",") if dietary else None
    allergen_list = avoid_allergens.split(",") if avoid_allergens else None
    recipes = recipe_db.get_recipes(category=category, dietary=dietary_list, allergens_to_avoid=allergen_list)
    return {"recipes": recipes, "count": len(recipes), "powered_by": "Edamam"}


@router.get("/categories")
def list_categories():
    return {"categories": recipe_db.TIMING_CATEGORIES}


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
