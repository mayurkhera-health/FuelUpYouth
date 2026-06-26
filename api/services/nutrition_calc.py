from datetime import date
from typing import Optional

from api.services.activity_engine import get_activity_profile

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

# Lifestyle PAL — non-training daily activity level (onboarding field; default "light")
PAL = {
    "sedentary": 1.3,   # mostly sitting — school desk, homework, screens
    "light":     1.4,   # mix of sitting and moving (DEFAULT)
    "moderate":  1.5,   # on feet most of the day
}

# Maps nutrition_calc normalized event types → activity_engine activity types (Option A)
NORM_TO_ACTIVITY_TYPE = {
    "rest":       "active_recovery",
    "practice":   "practice",
    "training":   "practice",      # speed/agility also maps to practice (Option A)
    "strength":   "strength_cond",
    "game":       "game",
    "tournament": "tournament",
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

HYDRATION_TARGETS = {  # oz/day — legacy fallback only
    "rest": (64, 72),
    "practice": (72, 80),
    "training": (72, 80),
    "strength": (72, 80),
    "game": (80, 88),
    "tournament": (88, 96),
}

# ── Spec-formula tables (getDashboardTargets) ─────────────────────────────────
CHO_FACTOR = {
    "rest":       {"any": 4.0},
    "low":        {"any": 3.5},
    "moderate":   {"lt60": 4.5, "bt6090": 6.0, "gt90": 7.0},
    "hard":       {"lt60": 5.5, "bt6090": 8.0, "gt90": 9.0},
    "tournament": {"any": 10.0},
}

SEASON_CHO  = {"in_season": 1.0, "off_season": 0.90, "post_season": 0.85}
SEASON_PROT = {"in_season": 1.0, "off_season": 1.05, "post_season": 0.95}

SPORT_PROT  = {
    "soccer": 1.6, "basketball": 1.6, "volleyball": 1.6,
    "running": 1.4, "swimming": 1.4, "strength": 1.8,
}


def lbs_to_kg(lbs: float) -> float:
    return lbs * 0.453592


def ft_in_to_cm(ft: int, inches: float) -> float:
    return (ft * 12 + inches) * 2.54


def calc_age(dob_str=None, age_fallback=None):
    """
    Returns decimal age as float.
    Prefers dob_str (ISO format 'YYYY-MM-DD') when available.
    Falls back to age_fallback integer for existing athletes with no DOB.
    # MIGRATION BRIDGE — remove fallback path once DOB capture rate >95%
    """
    if dob_str:
        dob = date.fromisoformat(dob_str)
        today = date.today()
        return float(
            today.year - dob.year -
            ((today.month, today.day) < (dob.month, dob.day))
        )
    if age_fallback is not None:
        return float(age_fallback)  # MIGRATION BRIDGE
    raise ValueError("calc_age requires either dob_str or age_fallback")


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


def _to_activity_type(norm: str) -> str:
    return NORM_TO_ACTIVITY_TYPE.get(norm, "practice")


def calc_tdee(rmr: float, pal: float, activity_aee: float, phv_extra_kcal: float = 0) -> int:
    """TDEE = (RMR × lifestyle PAL) + Activity Energy Expenditure + PHV bonus.

    pal             — from PAL dict, keyed by athlete.lifestyle_activity.
    activity_aee    — from get_activity_profile() in activity_engine.py.
    phv_extra_kcal  — from check_growth_phase(); 0 outside PHV window.
    """
    return round(rmr * pal + activity_aee + phv_extra_kcal)


def _normalize_sex(gender: str) -> str:
    """Map app gender strings to binary 'female'/'male' for RMR formulas.
    'Prefer not to say' defaults to 'male' (higher RMR = avoids underestimating needs)."""
    g = gender.lower().strip()
    if g in ("girl", "female", "f"):
        return "female"
    return "male"


def calc_rmr(wt_kg: float, ht_cm: float, sex: str, age_yr: float) -> float:
    """Age-stratified RMR — dietician-approved (Purvi, 2026-06-26).

    13–19  Reale (2020) — validated for competitive youth athletes.
    <  13  Schofield (1985) — pediatric reference.
    >= 20  Mifflin-St Jeor — adult fallback (edge case only for this app).

    sex must be 'female' or 'male' (use _normalize_sex before calling).
    NEVER use Harris-Benedict for athletes under 18.
    """
    if 13 <= age_yr <= 19:
        return round(11.1 * wt_kg + 8.4 * ht_cm - (537 if sex == "female" else 340))
    if age_yr < 13:
        # Schofield (1985) pediatric
        if sex == "female":
            return round(16.97 * wt_kg + 1.618 * ht_cm + 371)
        return round(19.59 * wt_kg + 1.303 * ht_cm + 414)
    # Mifflin-St Jeor for age 20+
    base = 10 * wt_kg + 6.25 * ht_cm - 5 * age_yr
    return round(base - 161 if sex == "female" else base + 5)


def check_growth_phase(age_yr: float, sex: str) -> dict:
    """Peak Height Velocity window — calories and protein needs elevated.

    Female PHV: ~11–13 yrs.  Male PHV: ~13–15 yrs.
    Source: Domaradzki et al. (2022), ACSM adolescent growth guidelines.
    Returns extra_kcal and extra_prot_g_per_kg to add on top of base RMR targets.
    """
    if sex == "female" and 11 <= age_yr <= 13:
        return {"phv": True, "extra_kcal": 150, "extra_prot_g_per_kg": 0.10}
    if sex == "male" and 13 <= age_yr <= 15:
        return {"phv": True, "extra_kcal": 150, "extra_prot_g_per_kg": 0.10}
    return {"phv": False, "extra_kcal": 0, "extra_prot_g_per_kg": 0.0}


def _cho_intensity_key(norm: str, intensity: Optional[str]) -> str:
    """Map event_type + raw intensity to a CHO_FACTOR key."""
    if norm == "tournament":
        return "tournament"
    if norm == "rest":
        return "rest"
    if intensity == "high":
        return "hard"
    if intensity == "medium":
        return "moderate"
    if intensity == "low":
        return "low"
    return "moderate"


def _duration_bucket(duration_min: float) -> str:
    if duration_min < 60:
        return "lt60"
    if duration_min <= 90:
        return "bt6090"
    return "gt90"


def calc_daily_cho(
    wt_kg: float,
    intensity: str,
    duration_min: float,
    season: str,
    activity_cho_modifier: float = 1.0,
) -> int:
    """Daily carbohydrate target in grams.

    Sources: ACSM/AND Joint Position Statement (Thomas et al. 2016),
             ISSN Nutrient Timing Position Stand (2017).

    activity_cho_modifier from activity_engine.get_activity_profile():
      S&C ×0.85 · speed/game ×1.10 · double-session ×1.25 · others ×1.0
    Two-step rounding matches the dietician spec — base rounded before modifier applied.
    """
    f      = CHO_FACTOR.get(intensity, CHO_FACTOR["moderate"])
    factor = f.get("any") or f.get(_duration_bucket(duration_min), 6.0)
    base   = round(wt_kg * factor * SEASON_CHO.get(season, 1.0))
    return round(base * activity_cho_modifier)


def _sport_type_from_event(norm: str) -> str:
    if norm == "strength":
        return "strength"
    return "soccer"


def _normalize_season(season_phase: Optional[str]) -> str:
    if not season_phase:
        return "in_season"
    s = season_phase.lower().strip()
    if s in ("postseason", "post_season"):
        return "post_season"
    if s == "off_season":
        return "off_season"
    return "in_season"


def calc_daily_targets(
    athlete: dict,
    event_type: str = "rest",
    intensity: Optional[str] = None,
    duration_min: float = 0,
) -> dict:
    wt_kg  = lbs_to_kg(athlete["weight_lbs"])
    ht_cm  = ft_in_to_cm(athlete["height_ft"], athlete["height_in"])
    sex    = _normalize_sex(athlete["gender"])
    age_yr = calc_age(
        dob_str=athlete.get("date_of_birth"),
        age_fallback=athlete.get("age"),
    )

    rmr  = calc_rmr(wt_kg, ht_cm, sex, age_yr)
    phv  = check_growth_phase(age_yr, sex)
    norm = normalize_event_type(event_type)

    pal = PAL.get(athlete.get("lifestyle_activity", "light"), 1.4)
    act = get_activity_profile(_to_activity_type(norm), intensity, duration_min, wt_kg)

    total_calories = calc_tdee(rmr, pal, act["aee_kcal"], phv["extra_kcal"])

    # ── Spec-formula CHO target ───────────────────────────────────────────────
    season = _normalize_season(athlete.get("season_phase"))
    # intensity_override from activity engine takes precedence over caller-supplied intensity
    cho_intensity = (act["intensity_override"] if act["intensity_override"] in CHO_FACTOR
                     else _cho_intensity_key(norm, intensity))
    carbs_g = calc_daily_cho(wt_kg, cho_intensity, duration_min, season, act["cho_modifier"])

    # ── Spec-formula protein target ───────────────────────────────────────────
    # Sport is EVENT-DERIVED by design (soccer-only app): _sport_type_from_event
    # returns "strength" for strength sessions (1.8) and "soccer" (1.6) otherwise.
    # RDN-signed-off 2026-06-24: strength days = 1.8 g/kg (NOT flat 1.6) is intended.
    # The nullable sport_type PROFILE field is intentionally DEFERRED, not missing —
    # revisit only if a second sport is added. Do not "fix" this by adding a field.
    # See docs/decisions/ADR-protein-soccer-only.md.
    sport_type = _sport_type_from_event(norm)
    prot_fac = SPORT_PROT.get(sport_type, 1.6)
    protein_g = round(
        wt_kg * prot_fac * SEASON_PROT.get(season, 1.0)
        + phv["extra_prot_g_per_kg"] * wt_kg,
        1,
    )

    # ── Spec-formula hydration target (oz) ───────────────────────────────────
    during_oz = round((13 * wt_kg * (duration_min / 60)) / 29.6) if duration_min > 0 else 0
    post_oz   = round((4 * wt_kg) / 29.6)
    # The +27 (pre) and +36 (meals) oz are a DELIBERATE deviation from the dietician
    # spec's 500/1000 mL (~12 oz/day higher). RDN-signed-off 2026-06-24: keep 109 oz —
    # do not "correct" to the mL values. See docs/decisions/ADR-protein-soccer-only.md.
    hydration_oz = during_oz + 27 + post_oz + 36

    # ── Legacy range fields (kept for DB schema & other callers) ─────────────
    carb_lo, carb_hi = CARB_TARGETS[norm]
    prot_lo, prot_hi = PROTEIN_TARGETS[norm]
    if intensity:
        carb_lo, carb_hi = _reposition(carb_lo, carb_hi, intensity)
        prot_lo, prot_hi = _reposition(prot_lo, prot_hi, intensity)
    fat_min = int(total_calories * 0.20 / 9)
    fat_max = int(total_calories * 0.35 / 9)

    iron_mg = 15 if sex == "female" else 11
    calcium_mg = 1300

    ffm_kg = wt_kg * 0.85
    lea_alert = total_calories < (30 * ffm_kg)

    return {
        "event_type": norm,
        "intensity": intensity,
        "total_calories": total_calories,
        # Spec single-value targets (used by Today dashboard)
        "carbs_g": carbs_g,
        "protein_g": protein_g,
        "hydration_oz": hydration_oz,
        # Legacy range fields (DB storage, reports)
        "carbs_g_min": carbs_g,
        "carbs_g_max": carbs_g,
        "protein_g_min": protein_g,
        "protein_g_max": protein_g,
        "fat_g_min": fat_min,
        "fat_g_max": fat_max,
        "iron_mg": iron_mg,
        "calcium_mg": calcium_mg,
        "hydration_oz_min": hydration_oz,
        "hydration_oz_max": hydration_oz,
        "lea_alert": lea_alert,
    }
