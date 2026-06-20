"""Voice meal analyzer: parse STT transcript via Bedrock + USDA FDC nutrition lookup."""

from api.services.bedrock_client import converse_text, parse_json_from_llm
from api.services.fdc_client import (
    best_match,
    macros_for_portion,
    passes_allergen_filter,
)

TEXT_PROMPT = """Parse this meal description spoken by a youth athlete. Extract every unique food item mentioned.

Return ONLY valid JSON with this exact shape:
{
  "foods": [
    {
      "name": "specific food name suitable for a nutrition database search (e.g. grilled chicken breast, brown rice, steamed broccoli)",
      "estimated_portion_g": 0
    }
  ]
}

Rules:
- estimated_portion_g is your best estimate of the serving size in grams based on what they said (e.g. "a bowl of rice" ~150g, "two eggs" ~100g)
- List each distinct food once; do not duplicate
- Use generic, searchable food names (not brand names unless clearly stated)
- If no food is mentioned, return { "foods": [] }"""


def _unique_foods(foods: list) -> list:
    seen: set[str] = set()
    result = []
    for f in foods:
        key = f["name"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(f)
    return result


def detect_foods_from_text(transcription: str) -> list:
    trimmed = (transcription or "").strip()
    if not trimmed:
        return []

    text = converse_text(
        system="You extract structured food items from spoken meal descriptions. Return only valid JSON.",
        user=f'{TEXT_PROMPT}\n\nMeal description:\n"{trimmed}"',
        max_tokens=1024,
        temperature=0.2,
    )

    parsed = parse_json_from_llm(text)
    foods = parsed.get("foods") or []
    if not isinstance(foods, list):
        raise ValueError("Text extraction output missing foods array")

    for food in foods:
        if not food.get("name", "").strip():
            raise ValueError("Text extraction output: food missing name")
        if not isinstance(food.get("estimated_portion_g"), (int, float)) or food["estimated_portion_g"] <= 0:
            raise ValueError(f"Text extraction output: invalid portion for '{food['name']}'")

    return _unique_foods(foods)


def lookup_food_nutrition(detection: dict, allergies: list | None = None) -> dict:
    allergies = allergies or []
    name = detection["name"]
    portion = float(detection["estimated_portion_g"])

    base = {
        "name": name,
        "estimated_portion_g": portion,
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0,
    }

    match = best_match(name)
    if not match or not passes_allergen_filter(match.get("description", ""), allergies):
        return base

    macros = macros_for_portion(match, portion)
    return {
        **base,
        "fdc_id": match.get("fdcId"),
        "fdc_description": match.get("description"),
        **macros,
    }


def analyze_voice(
    transcription: str,
    allergies: list | None = None,
) -> dict:
    """
    Returns MealAnalysis shape: { foods, totals, description, transcription }.
    """
    trimmed = (transcription or "").strip()
    if not trimmed:
        raise ValueError("No speech transcription provided.")

    detections = detect_foods_from_text(trimmed)
    if not detections:
        raise ValueError("No foods detected in the description.")

    foods = [lookup_food_nutrition(d, allergies) for d in detections]

    totals = {
        "calories": sum(f["calories"] for f in foods),
        "protein_g": round(sum(f["protein_g"] for f in foods), 1),
        "carbs_g": round(sum(f["carbs_g"] for f in foods), 1),
        "fat_g": round(sum(f["fat_g"] for f in foods), 1),
    }

    description = ", ".join(f"{f['name']} (~{f['estimated_portion_g']}g)" for f in foods)

    return {
        "foods": foods,
        "totals": totals,
        "description": description,
        "transcription": trimmed,
    }
