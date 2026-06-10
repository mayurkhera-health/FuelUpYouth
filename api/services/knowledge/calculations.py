"""
Deterministic nutrition calculation functions for youth athletes.
All numeric values come from peer-reviewed sources (NIH, ACSM, AND).
Claude explains results — these functions produce them.
"""

from datetime import datetime, timedelta

_IRON_RDA = {
    "male":   {(9, 13): 8,  (14, 18): 11},
    "female": {(9, 13): 8,  (14, 18): 15},
}


def iron_rda(age: int, gender: str) -> dict:
    """Return daily iron RDA in mg for a youth athlete."""
    gender_key = "female" if gender.lower() in ("female", "girl", "f") else "male"
    table = _IRON_RDA[gender_key]
    for (low, high), value in table.items():
        if low <= age <= high:
            return {
                "value": value,
                "unit": "mg/day",
                "source": "NIH Office of Dietary Supplements — Iron Fact Sheet",
                "source_url": "https://ods.od.nih.gov/factsheets/Iron-HealthProfessional/",
                "explanation_hint": (
                    f"The RDA for iron for a {age}-year-old {gender_key} is {value}mg per day. "
                    f"{'Female athletes aged 14-18 need almost double males due to menstrual losses.' if gender_key == 'female' and age >= 14 else ''}"
                ),
            }
    return {"value": 8, "unit": "mg/day", "source": "NIH", "source_url": "", "explanation_hint": "Default RDA"}


def calcium_rda(age: int) -> dict:
    """Return daily calcium RDA in mg. Ages 9-18 = 1300mg (NIH)."""
    value = 1300 if 9 <= age <= 18 else 1000
    return {
        "value": value,
        "unit": "mg/day",
        "source": "NIH Office of Dietary Supplements — Calcium Fact Sheet",
        "source_url": "https://ods.od.nih.gov/factsheets/Calcium-HealthProfessional/",
        "explanation_hint": (
            f"The RDA for calcium for athletes aged 9-18 is {value}mg per day. "
            "This is the peak bone mass window — calcium intake now determines bone strength for life."
        ),
    }


_PROTEIN_G_PER_KG = {
    "rest":       (1.2, 1.4),
    "practice":   (1.4, 1.6),
    "training":   (1.4, 1.6),
    "strength":   (1.8, 2.0),
    "game":       (1.6, 1.8),
    "tournament": (1.8, 2.0),
}

_LBS_TO_KG = 0.453592


def protein_range(weight_lbs: float, event_type: str) -> dict:
    """Return daily protein range in grams based on weight and event type."""
    key = event_type.lower() if event_type.lower() in _PROTEIN_G_PER_KG else "rest"
    low_per_kg, high_per_kg = _PROTEIN_G_PER_KG[key]
    weight_kg = weight_lbs * _LBS_TO_KG
    min_g = round(weight_kg * low_per_kg)
    max_g = round(weight_kg * high_per_kg)
    return {
        "min_g": min_g,
        "max_g": max_g,
        "unit": "g/day",
        "per_kg_range": f"{low_per_kg}-{high_per_kg} g/kg",
        "source": "ACSM / Academy of Nutrition and Dietetics / Dietitians of Canada Position Stand",
        "explanation_hint": (
            f"For a {weight_lbs} lb athlete on a {event_type} day, "
            f"the ACSM recommends {min_g}-{max_g}g of protein per day."
        ),
    }


_HYDRATION_OZ = {
    "rest":       (64, 72),
    "practice":   (72, 80),
    "training":   (72, 80),
    "strength":   (72, 80),
    "game":       (80, 88),
    "tournament": (88, 96),
}


def hydration_needs(weight_lbs: float, event_type: str, weather_hot: bool = False) -> dict:
    """Return daily hydration target in oz. Adds 8-16oz for hot weather."""
    key = event_type.lower() if event_type.lower() in _HYDRATION_OZ else "rest"
    min_oz, max_oz = _HYDRATION_OZ[key]
    if weather_hot:
        min_oz += 8
        max_oz += 16
    return {
        "min_oz": min_oz,
        "max_oz": max_oz,
        "cups_min": round(min_oz / 8),
        "cups_max": round(max_oz / 8),
        "unit": "oz/day",
        "weather_hot": weather_hot,
        "source": "ACSM Position Stand on Exercise and Fluid Replacement",
        "explanation_hint": (
            f"On a {event_type} day, the target is {min_oz}-{max_oz}oz of fluid."
        ),
    }


def pre_training_meal_window(start_time: str) -> dict:
    """Given event start time (HH:MM), return full_meal_by and snack_by times."""
    try:
        h, m = map(int, start_time.split(":"))
        event_dt = datetime.today().replace(hour=h, minute=m, second=0, microsecond=0)
        full_meal_dt = event_dt - timedelta(hours=2, minutes=30)
        snack_dt = event_dt - timedelta(hours=1)
        return {
            "start_time": start_time,
            "full_meal_by": full_meal_dt.strftime("%H:%M"),
            "snack_by": snack_dt.strftime("%H:%M"),
            "source": "ACSM / Academy of Nutrition and Dietetics",
            "explanation_hint": (
                f"For an event starting at {start_time}, eat your last full meal by "
                f"{full_meal_dt.strftime('%I:%M %p')}. Snack only by {snack_dt.strftime('%I:%M %p')}."
            ),
        }
    except ValueError:
        return {"error": f"Invalid time format: {start_time}. Use HH:MM."}


def post_training_recovery_window(end_time: str) -> dict:
    """Given event end time (HH:MM), return the 30-min recovery window."""
    try:
        h, m = map(int, end_time.split(":"))
        end_dt = datetime.today().replace(hour=h, minute=m, second=0, microsecond=0)
        close_dt = end_dt + timedelta(minutes=30)
        return {
            "window_opens": end_time,
            "window_closes": close_dt.strftime("%H:%M"),
            "duration_minutes": 30,
            "source": "ACSM — Post-Exercise Recovery Guidelines",
            "explanation_hint": (
                f"The 30-minute recovery window opens at {end_time} and closes at "
                f"{close_dt.strftime('%I:%M %p')}. Eat chocolate milk + banana immediately."
            ),
        }
    except ValueError:
        return {"error": f"Invalid time format: {end_time}. Use HH:MM."}


def calorie_estimate(weight_lbs: float, age: int, gender: str, event_type: str) -> dict:
    """Estimate daily calorie needs using Everett 2025 RMR formula."""
    from api.services.nutrition_calc import calc_daily_targets
    athlete = {
        "weight_lbs": weight_lbs,
        "age": age,
        "gender": gender,
        "height_ft": 5,
        "height_in": 4,
    }
    targets = calc_daily_targets(athlete, event_type)
    total = targets["total_calories"]
    return {
        "value": total,
        "unit": "kcal/day",
        "source": "Everett MD 2025 RMR formula x PAL multiplier (ACSM)",
        "explanation_hint": (
            f"For a {weight_lbs} lb {age}-year-old on a {event_type} day, "
            f"estimated daily calorie need is approximately {total} kcal."
        ),
    }
