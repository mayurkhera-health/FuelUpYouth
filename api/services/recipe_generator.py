"""Recipe selection from the FuelUp curated recipe library via agent choice."""

import json

from api.services import claude_ai, recipe_db
from api.services.bedrock_client import converse_text, parse_json_from_llm
from api.services.recipe_categories import resolve_category


def _recipe_db_to_response(db_recipe: dict, profile_key: str) -> dict:
    macros = db_recipe["macros"]
    ingredients = [i.strip() for i in db_recipe["ingredients"].split(",") if i.strip()]
    tags = list(dict.fromkeys([profile_key, *db_recipe.get("dietary", [])]))
    return {
        "name": db_recipe["name"],
        "category": profile_key,
        "calories": macros["calories"],
        "protein_g": macros["protein_g"],
        "carbs_g": macros["carbs_g"],
        "fat_g": macros["fat_g"],
        "ingredients": ingredients,
        "preparation_notes": (
            f"Best timing: {db_recipe['timing']}. "
            "Combine the listed ingredients into a balanced serving."
        ),
        "tags": tags,
    }


def _compact_recipes(recipes: list[dict]) -> list[dict]:
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "category": r["category"],
            "timing": r["timing"],
            "ingredients": r["ingredients"],
            "calories": r["macros"]["calories"],
            "protein_g": r["macros"]["protein_g"],
            "carbs_g": r["macros"]["carbs_g"],
            "fat_g": r["macros"]["fat_g"],
            "dietary": r["dietary"],
            "allergens": r["allergens"],
        }
        for r in recipes
    ]


def _choose_recipe_with_agent(
    candidates: list[dict],
    profile: dict,
    question: str | None,
    allergies: list | None,
    dietary_restrictions: list | None,
    athlete: dict | None,
) -> dict:
    restrictions = []
    if allergies:
        restrictions.append(f"Allergens to avoid: {', '.join(allergies)}")
    if dietary_restrictions:
        restrictions.append(f"Dietary restrictions: {', '.join(dietary_restrictions)}")
    restrictions_text = "\n".join(restrictions) or "None"

    athlete_ctx = ""
    if athlete:
        athlete_ctx = (
            f"Athlete: {athlete.get('first_name', 'athlete')}, "
            f"age {athlete.get('age', 'unknown')}, "
            f"position {athlete.get('position', 'unknown')}."
        )

    user_request = question or f"Suggest a {profile['label'].lower()} recipe."

    prompt = f"""You are FuelUp's recipe selector for youth soccer athletes ages 9-17.

FuelUp provides food education guidance — not medical nutrition therapy.
Never recommend supplements for athletes under 18.

You are selecting an existing recipe from FuelUp's curated recipe library — not writing a new one.

USER REQUEST: {user_request}

CATEGORY: {profile['label']}
REQUIREMENTS: {profile['requirements']}
TARGET CALORIES: {profile['target_calories']['min']}–{profile['target_calories']['max']} kcal
RESTRICTIONS: {restrictions_text}
{athlete_ctx}

AVAILABLE RECIPES — these are the only valid options. You MUST pick exactly ONE recipe_id from this list:
{json.dumps(_compact_recipes(candidates), indent=2)}

RULES:
1. Return only a recipe_id that appears in AVAILABLE RECIPES.
2. Pick the recipe that best matches what the user asked for.
3. If the user has no specific preference, pick the best fit for the fueling window and athlete context.
4. Never invent recipes, ingredients, or IDs.

Return ONLY valid JSON:
{{"recipe_id": "R010"}}"""

    text = converse_text(
        system=claude_ai.SCIENCE_SYSTEM,
        user=prompt,
        max_tokens=256,
        temperature=0.3,
    )
    parsed = parse_json_from_llm(text)
    recipe_id = str(parsed.get("recipe_id", "")).upper()
    by_id = {r["id"]: r for r in candidates}
    if recipe_id in by_id:
        return by_id[recipe_id]
    return candidates[0]


def generate_recipe(
    category: str,
    allergies: list | None = None,
    dietary_restrictions: list | None = None,
    athlete: dict | None = None,
    question: str | None = None,
) -> dict:
    """
    Returns { recipe, source_ingredients, ingredient_source } matching the mobile RecipeGenerateResponse shape.
    Sends all valid library recipes to the agent, which picks the best match for the request.
    """
    profile = resolve_category(category)
    candidates = recipe_db.get_valid_recipes(
        profile["key"],
        allergies=allergies,
        dietary_restrictions=dietary_restrictions,
    )
    if not candidates:
        raise ValueError(
            f"No recipe found for category '{category}' "
            "with the given allergies and dietary restrictions."
        )

    db_recipe = _choose_recipe_with_agent(
        candidates,
        profile,
        question,
        allergies,
        dietary_restrictions,
        athlete,
    )

    ingredients = [i.strip() for i in db_recipe["ingredients"].split(",") if i.strip()]
    return {
        "recipe": _recipe_db_to_response(db_recipe, profile["key"]),
        "source_ingredients": ingredients,
        "ingredient_source": "recipe_library",
    }
