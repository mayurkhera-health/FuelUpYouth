from typing import Optional

EVENT_TYPE_MAP = {
    "soccer game": "game",
    "game": "game",
    "soccer tournament": "tournament",
    "tournament": "tournament",
    "club soccer practice": "practice",
    "practice": "practice",
    "private soccer training": "training",
    "training": "training",
    "speed/agility training": "training",
    "agility": "training",
    "strength/conditioning": "strength",
    "strength": "strength",
    "yoga/flexibility/recovery": "rest",
    "yoga": "rest",
    "recovery": "rest",
    "rest": "rest",
    "pre-game day": "practice",
    "post-game recovery day": "rest",
    "double training day": "tournament",
}

PAL_MULTIPLIERS = {
    "rest": 1.55,
    "practice": 1.85,
    "training": 1.85,
    "strength": 1.85,
    "game": 2.00,
    "tournament": 2.05,
}

CARB_TARGETS = {  # g/kg
    "rest": (4, 5),
    "practice": (6, 8),
    "training": (6, 8),
    "strength": (6, 8),
    "game": (8, 10),
    "tournament": (10, 12),
}

PROTEIN_TARGETS = {  # g/kg
    "rest": (1.2, 1.4),
    "practice": (1.4, 1.6),
    "training": (1.4, 1.6),
    "strength": (1.8, 2.0),
    "game": (1.6, 1.8),
    "tournament": (1.8, 2.0),
}

HYDRATION_TARGETS = {  # oz/day
    "rest": (64, 72),
    "practice": (72, 80),
    "training": (72, 80),
    "strength": (72, 80),
    "game": (80, 88),
    "tournament": (88, 96),
}


def lbs_to_kg(lbs: float) -> float:
    return lbs * 0.453592


def ft_in_to_cm(ft: int, inches: float) -> float:
    return (ft * 12 + inches) * 2.54


def normalize_event_type(event_type: str) -> str:
    return EVENT_TYPE_MAP.get(event_type.lower().strip(), "rest")


def derive_intensity(event_type: str, competition_level: Optional[str]) -> str:
    """Derive intensity (low/medium/high) for ICS-imported, legacy, or
    otherwise-unspecified events. Manual events carry an explicit value.

    Rest/recovery events floor to "low" for everyone; all other events map
    from competition level. Tolerant of both the 3 current labels and the
    legacy 4-value labels."""
    if normalize_event_type(event_type) == "rest":
        return "low"
    level = (competition_level or "").strip().lower()
    if level == "":
        return "low"
    if "elite" in level:
        return "high"
    if "recreational" in level:
        return "low"
    if "competitive" in level or "club" in level:
        return "medium"
    return "low"


def _reposition(lo: float, hi: float, intensity: str):
    """Return a sub-band positioned within [lo, hi] by intensity.
    Never exceeds the original scientific bounds."""
    span = hi - lo
    if intensity == "low":
        return lo, lo + 0.5 * span
    if intensity == "high":
        return lo + 0.5 * span, hi
    # medium (and any unexpected value): middle 50%
    return lo + 0.25 * span, hi - 0.25 * span


def calc_rmr(weight_lbs: float, height_ft: int, height_in: float, gender: str) -> float:
    """Everett MD 2025 RMR formula — NEVER use Harris-Benedict for youth."""
    wt_kg = lbs_to_kg(weight_lbs)
    ht_cm = ft_in_to_cm(height_ft, height_in)
    if gender.lower() in ("girl", "female", "f"):
        return 11.1 * wt_kg + 8.4 * ht_cm - 537
    return 11.1 * wt_kg + 8.4 * ht_cm - 340


def calc_daily_targets(athlete: dict, event_type: str = "rest", intensity: Optional[str] = None) -> dict:
    wt_kg = lbs_to_kg(athlete["weight_lbs"])
    rmr = calc_rmr(athlete["weight_lbs"], athlete["height_ft"], athlete["height_in"], athlete["gender"])
    norm = normalize_event_type(event_type)

    total_calories = int(rmr * PAL_MULTIPLIERS.get(norm, 1.55))

    carb_lo, carb_hi = CARB_TARGETS[norm]
    prot_lo, prot_hi = PROTEIN_TARGETS[norm]
    if intensity:
        carb_lo, carb_hi = _reposition(carb_lo, carb_hi, intensity)
        prot_lo, prot_hi = _reposition(prot_lo, prot_hi, intensity)
    carb_min = int(carb_lo * wt_kg)
    carb_max = int(carb_hi * wt_kg)
    protein_min = round(prot_lo * wt_kg, 1)
    protein_max = round(prot_hi * wt_kg, 1)
    fat_min = int(total_calories * 0.20 / 9)
    fat_max = int(total_calories * 0.35 / 9)

    iron_mg = 15 if athlete["gender"].lower() in ("girl", "female", "f") else 11
    calcium_mg = 1300  # AAP — peak bone mass window

    hydration = HYDRATION_TARGETS.get(norm, (64, 72))

    ffm_kg = wt_kg * 0.85
    lea_alert = total_calories < (30 * ffm_kg)

    return {
        "event_type": norm,
        "intensity": intensity,
        "total_calories": total_calories,
        "carbs_g_min": carb_min,
        "carbs_g_max": carb_max,
        "protein_g_min": protein_min,
        "protein_g_max": protein_max,
        "fat_g_min": fat_min,
        "fat_g_max": fat_max,
        "iron_mg": iron_mg,
        "calcium_mg": calcium_mg,
        "hydration_oz_min": hydration[0],
        "hydration_oz_max": hydration[1],
        "lea_alert": lea_alert,
    }
