"""Photo meal analyzer: Bedrock vision food detection + USDA FDC nutrition lookup."""
import json

from api.services.bedrock_client import converse_vision, extract_json
from api.services.fdc_client import (
    best_match,
    macros_for_portion,
    passes_allergen_filter,
)


VISION_PROMPT = """Analyze this meal photo. Identify every unique food item visible.

Return ONLY valid JSON with this exact shape:
{
  "foods": [
    {
      "name": "specific food name suitable for a nutrition database search (e.g. grilled chicken breast, brown rice, steamed broccoli)",
      "bbox": { "x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0 },
      "estimated_portion_g": 0
    }
  ]
}

Rules:
- bbox coordinates are normalized 0–1 relative to image width (x, width) and height (y, height)
- List each distinct food once; do not duplicate
- estimated_portion_g is your best estimate of the visible serving size in grams
- Use generic, searchable food names (not brand names unless clearly visible)
- If no food is visible, return { "foods": [] }"""


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


def detect_foods(image_base64: str, media_type: str = "image/jpeg") -> list:
    text = converse_vision(
        prompt=VISION_PROMPT,
        image_base64=image_base64,
        media_type=media_type,
        max_tokens=1024,
        temperature=0.2,
    )

    parsed = json.loads(extract_json(text))
    foods = parsed.get("foods") or []
    if not isinstance(foods, list):
        raise ValueError("Vision output missing foods array")

    for food in foods:
        if not food.get("name", "").strip():
            raise ValueError("Vision output: food missing name")
        bbox = food.get("bbox") or {}
        for k in ("x", "y", "width", "height"):
            if not isinstance(bbox.get(k), (int, float)):
                raise ValueError(f"Vision output: invalid bbox for '{food['name']}'")
        if not isinstance(food.get("estimated_portion_g"), (int, float)) or food["estimated_portion_g"] <= 0:
            raise ValueError(f"Vision output: invalid portion for '{food['name']}'")

    return _unique_foods(foods)


def lookup_food_nutrition(detection: dict, allergies: list | None = None) -> dict:
    allergies = allergies or []
    name = detection["name"]
    portion = float(detection["estimated_portion_g"])
    bbox = detection["bbox"]

    base = {
        "name": name,
        "bbox": bbox,
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


def analyze_photo(
    image_base64: str,
    media_type: str = "image/jpeg",
    allergies: list | None = None,
) -> dict:
    """
    Returns PhotoMealAnalysis shape: { foods, totals, description }.
    """
    detections = detect_foods(image_base64, media_type)
    if not detections:
        raise ValueError("No foods detected in the image.")

    foods = [lookup_food_nutrition(d, allergies) for d in detections]

    totals = {
        "calories": sum(f["calories"] for f in foods),
        "protein_g": round(sum(f["protein_g"] for f in foods), 1),
        "carbs_g": round(sum(f["carbs_g"] for f in foods), 1),
        "fat_g": round(sum(f["fat_g"] for f in foods), 1),
    }

    description = ", ".join(f"{f['name']} (~{f['estimated_portion_g']}g)" for f in foods)

    return {"foods": foods, "totals": totals, "description": description}
