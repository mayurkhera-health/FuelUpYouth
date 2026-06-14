"""Meal-timing category profiles for USDA FDC ingredient search + LLM recipe composition."""

# Aliases map backend timing categories and mobile keys to profile keys.
CATEGORY_ALIASES = {
    "pre-game": "pre_game",
    "pre_game": "pre_game",
    "post-game-recovery": "post_game",
    "post_game": "post_game",
    "pre-game-snack": "snack",
    "practice": "lunch",
    "strength": "dinner",
    "tournament": "pre_game",
    "meal-prep": "lunch",
}

RECIPE_CATEGORY_PROFILES = {
    "halftime": {
        "label": "Halftime",
        "fdc_search_queries": ["banana", "apple", "orange", "pretzel", "grapes", "watermelon", "rice cake"],
        "nutrient_focus": ["carbohydrates", "lightweight", "fast-digesting"],
        "avoid_nutrients": ["high_fat", "high_fiber"],
        "requirements": (
            "Halftime fuel: lightweight, portable, fast-digesting carbs only. "
            "Must be eaten in under 5 minutes between play. No heavy fats, fiber, or large portions."
        ),
        "target_calories": {"min": 80, "max": 200},
        "tags": ["halftime", "quick", "portable"],
    },
    "pre_game": {
        "label": "Pre-Game",
        "fdc_search_queries": ["oatmeal", "whole wheat bread", "pasta", "brown rice", "chicken breast", "turkey", "sweet potato"],
        "nutrient_focus": ["complex-carbs", "protein", "balanced"],
        "avoid_nutrients": ["high_fat", "high_fiber"],
        "requirements": (
            "Pre-game meal 2–3 hours before competition: complex carbs with moderate lean protein. "
            "Low fat and moderate fiber to avoid stomach upset."
        ),
        "target_calories": {"min": 350, "max": 600},
        "tags": ["pre-game", "energy"],
    },
    "post_game": {
        "label": "Post-Game",
        "fdc_search_queries": ["chocolate milk", "greek yogurt", "turkey sandwich", "chicken", "quinoa", "banana", "cottage cheese"],
        "nutrient_focus": ["recovery", "protein", "carbohydrates"],
        "avoid_nutrients": ["high_fat"],
        "requirements": (
            "Post-game recovery within 30–60 minutes: 3:1 or 4:1 carb-to-protein ratio. "
            "Replenish glycogen and support muscle repair."
        ),
        "target_calories": {"min": 300, "max": 550},
        "tags": ["recovery", "post-game"],
    },
    "breakfast": {
        "label": "Breakfast",
        "fdc_search_queries": ["eggs", "oatmeal", "whole grain cereal", "banana", "berries", "milk", "whole wheat toast"],
        "nutrient_focus": ["balanced", "complex-carbs", "protein"],
        "avoid_nutrients": ["high_sugar"],
        "requirements": "Balanced breakfast to start the day: complex carbs, protein, and fruit.",
        "target_calories": {"min": 400, "max": 650},
        "tags": ["breakfast", "balanced"],
    },
    "lunch": {
        "label": "Lunch",
        "fdc_search_queries": ["chicken breast", "brown rice", "quinoa", "whole wheat wrap", "black beans", "spinach", "avocado"],
        "nutrient_focus": ["balanced", "protein", "complex-carbs"],
        "avoid_nutrients": ["high_sugar"],
        "requirements": "Midday meal: balanced macros with lean protein, whole grains, and vegetables.",
        "target_calories": {"min": 450, "max": 700},
        "tags": ["lunch", "balanced"],
    },
    "dinner": {
        "label": "Dinner",
        "fdc_search_queries": ["salmon", "chicken", "lean beef", "broccoli", "sweet potato", "brown rice", "lentils"],
        "nutrient_focus": ["protein", "balanced", "recovery"],
        "avoid_nutrients": ["high_sugar"],
        "requirements": "Evening meal: lean protein, complex carbs, and vegetables for overnight recovery.",
        "target_calories": {"min": 500, "max": 750},
        "tags": ["dinner", "recovery"],
    },
    "snack": {
        "label": "Snack",
        "fdc_search_queries": ["almonds", "apple", "peanut butter", "hummus", "carrots", "cheese stick", "trail mix"],
        "nutrient_focus": ["balanced", "lightweight"],
        "avoid_nutrients": ["high_sugar"],
        "requirements": "Between-meal snack: portable, moderate calories, mix of carbs and protein.",
        "target_calories": {"min": 150, "max": 300},
        "tags": ["snack", "portable"],
    },
    "hydration": {
        "label": "Hydration",
        "fdc_search_queries": ["watermelon", "cucumber", "orange", "coconut water", "strawberries"],
        "nutrient_focus": ["hydration", "lightweight", "fast-digesting"],
        "avoid_nutrients": ["high_fat", "high_sodium"],
        "requirements": "Hydration-focused fuel: high water-content foods and light carbs.",
        "target_calories": {"min": 50, "max": 150},
        "tags": ["hydration", "lightweight"],
    },
}


def resolve_category(category: str) -> dict:
    key = CATEGORY_ALIASES.get(category, category)
    profile = RECIPE_CATEGORY_PROFILES.get(key)
    if not profile:
        valid = sorted(set(RECIPE_CATEGORY_PROFILES) | set(CATEGORY_ALIASES))
        raise ValueError(f"Unknown category '{category}'. Valid: {', '.join(valid)}")
    return {**profile, "key": key}


def _focus_bonus(focus: str, n: dict) -> float:
    if focus in ("carbohydrates", "fast-digesting", "complex-carbs"):
        return n["carbs"] * 2
    if focus in ("protein", "recovery"):
        return n["protein"] * 3
    if focus == "lightweight":
        return 30 if n["calories"] < 150 else (10 if n["calories"] < 250 else 0)
    if focus == "hydration":
        return 25 if n["calories"] < 80 else 0
    if focus == "balanced":
        return n["protein"] * 1.5 + n["carbs"] * 1.5 - n["fat"] * 0.5
    return 0


def _avoid_penalty(avoid: str, n: dict) -> float:
    if avoid == "high_fat":
        return n["fat"] * 2 if n["fat"] > 10 else 0
    if avoid == "high_fiber":
        return n["fiber"] * 3 if n["fiber"] > 5 else 0
    return 0


def score_food(food: dict, profile: dict) -> float:
    from api.services.fdc_client import FDC_NUTRIENT_IDS, nutrient_value

    calories = nutrient_value(food, FDC_NUTRIENT_IDS["calories"])
    protein = nutrient_value(food, FDC_NUTRIENT_IDS["protein"])
    carbs = nutrient_value(food, FDC_NUTRIENT_IDS["carbs"])
    fat = nutrient_value(food, FDC_NUTRIENT_IDS["fat"])
    fiber = nutrient_value(food, FDC_NUTRIENT_IDS["fiber"])
    n = {"calories": calories, "protein": protein, "carbs": carbs, "fat": fat, "fiber": fiber}

    score = sum(_focus_bonus(f, n) for f in profile["nutrient_focus"])
    score -= sum(_avoid_penalty(a, n) for a in profile["avoid_nutrients"])

    mid = (profile["target_calories"]["min"] + profile["target_calories"]["max"]) / 2
    score -= abs(calories - mid) * 0.05
    return score


def gather_ingredients(
    category: str,
    allergies: list | None = None,
    dietary_restrictions: list | None = None,
    max_ingredients: int = 8,
) -> list:
    from api.services.fdc_client import (
        FDC_NUTRIENT_IDS,
        nutrient_value,
        passes_allergen_filter,
        passes_dietary_filter,
        search_foods,
    )

    profile = resolve_category(category)
    allergies = allergies or []
    dietary_restrictions = dietary_restrictions or []
    seen: set[int] = set()
    candidates = []

    for query in profile["fdc_search_queries"]:
        for food in search_foods(query, page_size=4):
            fdc_id = food.get("fdcId")
            if fdc_id in seen:
                continue
            seen.add(fdc_id)
            desc = food.get("description", "")
            if not passes_allergen_filter(desc, allergies):
                continue
            if not passes_dietary_filter(food, dietary_restrictions):
                continue
            candidates.append({
                "fdc_id": fdc_id,
                "name": desc,
                "calories": nutrient_value(food, FDC_NUTRIENT_IDS["calories"]),
                "protein_g": nutrient_value(food, FDC_NUTRIENT_IDS["protein"]),
                "carbs_g": nutrient_value(food, FDC_NUTRIENT_IDS["carbs"]),
                "fat_g": nutrient_value(food, FDC_NUTRIENT_IDS["fat"]),
                "score": score_food(food, profile),
            })

    if not candidates:
        raise ValueError(f"No ingredients found for category '{category}' after applying restrictions.")

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:max_ingredients]
