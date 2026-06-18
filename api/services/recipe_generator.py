"""Recipe generator agent: FDC ingredient lookup + Bedrock recipe composition."""
import json

from api.services import claude_ai
from api.services.bedrock_client import converse_text, extract_json
from api.services.recipe_categories import gather_ingredients, resolve_category


def generate_recipe(
    category: str,
    allergies: list | None = None,
    dietary_restrictions: list | None = None,
    athlete: dict | None = None,
) -> dict:
    """
    Returns { recipe, source_ingredients } matching the mobile RecipeGenerateResponse shape.
    """
    profile = resolve_category(category)
    ingredients = gather_ingredients(category, allergies, dietary_restrictions)

    ingredient_lines = "\n".join(
        f"- {i['name']} (per 100g: {round(i['calories'])} kcal, "
        f"P {i['protein_g']:.1f}g, C {i['carbs_g']:.1f}g, F {i['fat_g']:.1f}g)"
        for i in ingredients
    )

    restrictions = []
    if allergies:
        restrictions.append(f"Allergens to avoid: {', '.join(allergies)}")
    if dietary_restrictions:
        restrictions.append(f"Dietary restrictions: {', '.join(dietary_restrictions)}")
    restrictions_text = "\n".join(restrictions)

    athlete_ctx = ""
    if athlete:
        athlete_ctx = (
            f"Athlete: age {athlete.get('age', 'unknown')}, "
            f"position {athlete.get('position', 'unknown')}."
        )

    prompt = f"""You are a youth sports nutrition recipe writer for Fueling2Win.

Fueling2Win provides food education guidance — not medical nutrition therapy.
Never recommend supplements for athletes under 18.

CATEGORY: {profile['label']}
REQUIREMENTS: {profile['requirements']}
TARGET CALORIES: {profile['target_calories']['min']}–{profile['target_calories']['max']} kcal for the full recipe
SUGGESTED TAGS: {', '.join(profile['tags'])}
{restrictions_text}
{athlete_ctx}

USDA-verified ingredients to build from (use a subset — do not invent foods not on this list):
{ingredient_lines}

Write ONE practical recipe for a youth athlete. Use realistic portions.
Return ONLY valid JSON:
{{
  "name": "string",
  "category": "{profile['key']}",
  "calories": number,
  "protein_g": number,
  "carbs_g": number,
  "fat_g": number,
  "ingredients": ["quantity + ingredient", ...],
  "preparation_notes": "step-by-step instructions",
  "tags": ["tag1", "tag2"]
}}"""

    text = converse_text(
        system=claude_ai.SCIENCE_SYSTEM,
        user=prompt,
        max_tokens=1024,
        temperature=0.7,
    )
    llm_recipe = json.loads(extract_json(text))

    recipe = {
        "name": llm_recipe["name"],
        "category": profile["key"],
        "calories": round(llm_recipe["calories"]),
        "protein_g": round(float(llm_recipe["protein_g"]), 1),
        "carbs_g": round(float(llm_recipe["carbs_g"]), 1),
        "fat_g": round(float(llm_recipe["fat_g"]), 1),
        "ingredients": llm_recipe["ingredients"],
        "preparation_notes": llm_recipe["preparation_notes"],
        "tags": llm_recipe.get("tags", profile["tags"]),
    }

    return {
        "recipe": recipe,
        "source_ingredients": [i["name"] for i in ingredients],
    }
