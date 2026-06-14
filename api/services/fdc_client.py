"""USDA FoodData Central API client — shared by recipe generator and photo meal analyzer."""
import os
import requests

FDC_BASE = "https://api.nal.usda.gov/fdc/v1"

FDC_NUTRIENT_IDS = {
    "calories": 1008,
    "protein": 1003,
    "carbs": 1005,
    "fat": 1004,
    "fiber": 1079,
    "sugar": 2000,
    "sodium": 1093,
}

ALLERGEN_KEYWORDS = {
    "dairy": ["milk", "cheese", "yogurt", "butter", "cream", "whey", "casein", "lactose"],
    "eggs": ["egg"],
    "fish": ["fish", "salmon", "tuna", "cod", "sardine", "anchovy"],
    "shellfish": ["shrimp", "crab", "lobster", "shellfish", "clam", "mussel"],
    "tree_nuts": ["almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut"],
    "peanuts": ["peanut"],
    "wheat": ["wheat", "flour", "bread", "pasta"],
    "soy": ["soy", "tofu", "edamame"],
    "sesame": ["sesame", "tahini"],
    "gluten": ["wheat", "barley", "rye", "gluten"],
}

DIETARY_FILTERS = {
    "Egg-Free": {"blocked_keywords": ["egg"]},
    "Shellfish-Free": {"blocked_keywords": ["shrimp", "crab", "lobster", "shellfish"]},
    "Soy-Free": {"blocked_keywords": ["soy", "tofu", "edamame"]},
    "Low-Sodium": {"max_sodium_mg": 140},
    "Diabetic / Low-Sugar": {"max_sugar_g": 8},
}


def _api_key() -> str:
    key = os.getenv("FDC_API_KEY")
    if not key:
        raise RuntimeError(
            "FDC_API_KEY is required. Sign up at https://fdc.nal.usda.gov/api-key-signup"
        )
    return key


def nutrient_value(food: dict, nutrient_id: int) -> float:
    for n in food.get("foodNutrients") or []:
        if n.get("nutrientId") == nutrient_id:
            return float(n.get("value") or 0)
    return 0.0


def contains_keyword(text: str, keywords: list) -> bool:
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)


def passes_allergen_filter(description: str, allergies: list) -> bool:
    for allergen in allergies or []:
        key = allergen.lower().replace(" ", "_")
        keywords = ALLERGEN_KEYWORDS.get(key) or ALLERGEN_KEYWORDS.get(allergen.lower())
        if keywords and contains_keyword(description, keywords):
            return False
    return True


def passes_dietary_filter(food: dict, restrictions: list) -> bool:
    desc = food.get("description", "")
    for restriction in restrictions or []:
        filt = DIETARY_FILTERS.get(restriction)
        if not filt:
            continue
        if filt.get("blocked_keywords") and contains_keyword(desc, filt["blocked_keywords"]):
            return False
        if filt.get("max_sugar_g") is not None:
            if nutrient_value(food, FDC_NUTRIENT_IDS["sugar"]) > filt["max_sugar_g"]:
                return False
        if filt.get("max_sodium_mg") is not None:
            if nutrient_value(food, FDC_NUTRIENT_IDS["sodium"]) > filt["max_sodium_mg"]:
                return False
    return True


def search_foods(query: str, page_size: int = 5) -> list:
    """Search Foundation + SR Legacy foods via FDC API."""
    url = f"{FDC_BASE}/foods/search"
    resp = requests.post(
        url,
        params={"api_key": _api_key()},
        json={
            "query": query,
            "dataType": ["Foundation", "SR Legacy"],
            "pageSize": page_size,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("foods") or []


def best_match(query: str) -> dict | None:
    foods = search_foods(query, page_size=5)
    return foods[0] if foods else None


def macros_for_portion(food: dict, portion_g: float) -> dict:
    """Scale per-100g FDC values to an estimated portion."""
    scale = portion_g / 100.0
    return {
        "calories": round(nutrient_value(food, FDC_NUTRIENT_IDS["calories"]) * scale),
        "protein_g": round(nutrient_value(food, FDC_NUTRIENT_IDS["protein"]) * scale, 1),
        "carbs_g": round(nutrient_value(food, FDC_NUTRIENT_IDS["carbs"]) * scale, 1),
        "fat_g": round(nutrient_value(food, FDC_NUTRIENT_IDS["fat"]) * scale, 1),
    }
