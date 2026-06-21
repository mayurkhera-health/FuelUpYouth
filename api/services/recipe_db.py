import json
from pathlib import Path

_RECIPES_PATH = Path(__file__).resolve().parent.parent / "data" / "recipes.json"


def _load_recipes() -> list[dict]:
    with open(_RECIPES_PATH, encoding="utf-8") as f:
        return json.load(f)


RECIPES = _load_recipes()

TIMING_CATEGORIES = sorted({r["category"] for r in RECIPES})


def get_recipes(category: str = None, dietary: list = None, allergens_to_avoid: list = None) -> list:
    results = RECIPES
    if category:
        results = [r for r in results if r["category"] == category]
    if dietary:
        results = [r for r in results if any(d in r["dietary"] for d in dietary)]
    if allergens_to_avoid:
        results = [r for r in results if not any(a in r["allergens"] for a in allergens_to_avoid)]
    return results


def get_recipe_by_id(recipe_id: str) -> dict:
    return next((r for r in RECIPES if r["id"] == recipe_id), None)


# Maps recipe_categories profile keys to recipe_db category values.
PROFILE_TO_DB_CATEGORIES = {
    "pre_game":       ["pre-game", "tournament", "Pre-Game Fueling"],
    "pre_game_snack": ["pre-game-snack", "Mid-Day Snacks"],
    "halftime":       ["halftime", "Mid-Day Snacks"],
    "post_game":      ["post-game-recovery", "Post-Game Recovery"],
    "practice":       ["practice", "Pre-Game Fueling"],
    "strength":       ["strength", "Dinner", "Post-Game Recovery"],
    "tournament":     ["tournament", "Pre-Game Fueling", "Mid-Day Snacks"],
    "meal_prep":      ["meal-prep", "Breakfast", "Lunch", "Dinner"],
    "breakfast":      ["practice", "Breakfast"],
    "lunch":          ["practice", "meal-prep", "Lunch"],
    "dinner":         ["strength", "practice", "Dinner"],
    "hydration":      ["halftime", "Mid-Day Snacks"],
    "recovery":       ["post-game-recovery", "Post-Game Recovery"],
    "snack":          ["pre-game-snack", "Mid-Day Snacks"],
}


def _normalize_restrictions(items: list | None) -> list:
    if not items:
        return []
    return [i.strip().lower() for i in items if i and str(i).strip().lower() != "none"]


def get_valid_recipes(
    profile_key: str,
    allergies: list | None = None,
    dietary_restrictions: list | None = None,
) -> list[dict]:
    """Return all recipes matching category, allergens, and dietary restrictions."""
    db_categories = PROFILE_TO_DB_CATEGORIES.get(profile_key, [profile_key])
    allergens = _normalize_restrictions(allergies)
    dietary = _normalize_restrictions(dietary_restrictions)

    seen: set[str] = set()
    candidates: list[dict] = []
    for cat in db_categories:
        exact_cats = [c for c in TIMING_CATEGORIES if c == cat or c.endswith(cat)]
        for exact_cat in exact_cats:
            for recipe in get_recipes(category=exact_cat, allergens_to_avoid=allergens):
                if recipe["id"] not in seen:
                    seen.add(recipe["id"])
                    candidates.append(recipe)

    if dietary:
        matched = [
            r for r in candidates
            if any(d in [x.lower() for x in r["dietary"]] for d in dietary)
        ]
        if matched:
            candidates = matched

    return candidates
