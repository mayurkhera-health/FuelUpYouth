"""Unit tests for intensity derivation and band repositioning in nutrition_calc."""

from api.services import nutrition_calc as nc


# ---- derive_intensity ----

def test_rest_event_floors_to_low_even_for_elite():
    assert nc.derive_intensity("Yoga/Flexibility/Recovery", "Elite Club") == "low"
    assert nc.derive_intensity("rest", "Elite Club") == "low"

def test_elite_club_competitive_event_is_high():
    assert nc.derive_intensity("game", "Elite Club") == "high"

def test_competitive_club_is_medium():
    assert nc.derive_intensity("game", "Competitive Club") == "medium"

def test_recreational_is_low():
    assert nc.derive_intensity("game", "Recreational") == "low"

def test_legacy_labels_still_map():
    assert nc.derive_intensity("game", "Elite") == "high"
    assert nc.derive_intensity("game", "Club") == "medium"
    assert nc.derive_intensity("game", "Competitive") == "medium"

def test_null_competition_level_defaults_low():
    assert nc.derive_intensity("game", None) == "low"
    assert nc.derive_intensity("game", "") == "low"
    assert nc.derive_intensity("game", "something weird") == "low"


# ---- repositioning in calc_daily_targets ----

ATH = {"weight_lbs": 110.23123, "height_ft": 5, "height_in": 6, "gender": "girl", "age": 14}
# 110.23123 lbs -> ~50 kg, age 14 girl

def test_intensity_none_returns_full_band():
    # carbs_g_min == carbs_g_max == carbs_g (spec-formula single-value target)
    t = nc.calc_daily_targets(ATH, "game")  # no intensity
    assert t["carbs_g_min"] == t["carbs_g"] and t["carbs_g_max"] == t["carbs_g"]

def test_low_intensity_is_lower_half():
    t = nc.calc_daily_targets(ATH, "game", intensity="low")
    assert t["carbs_g_min"] == t["carbs_g"] and t["carbs_g_max"] == t["carbs_g"]

def test_medium_intensity_is_middle():
    t = nc.calc_daily_targets(ATH, "game", intensity="medium")
    assert t["carbs_g_min"] == t["carbs_g"] and t["carbs_g_max"] == t["carbs_g"]

def test_high_intensity_is_upper_half():
    t = nc.calc_daily_targets(ATH, "game", intensity="high")
    assert t["carbs_g_min"] == t["carbs_g"] and t["carbs_g_max"] == t["carbs_g"]

def test_repositioned_band_never_exceeds_science_bounds():
    full = nc.calc_daily_targets(ATH, "game")
    high = nc.calc_daily_targets(ATH, "game", intensity="high")
    assert high["carbs_g_max"] <= full["carbs_g_max"]
    assert high["carbs_g_min"] >= full["carbs_g_min"]
