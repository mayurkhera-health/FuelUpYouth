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

def test_cho_target_is_single_value():
    # Spec-formula CHO is a single value: the legacy band fields collapse to it.
    t = nc.calc_daily_targets(ATH, "practice")
    assert t["carbs_g_min"] == t["carbs_g"] == t["carbs_g_max"]

def test_low_intensity_is_lower_than_medium():
    low = nc.calc_daily_targets(ATH, "practice", intensity="low")
    med = nc.calc_daily_targets(ATH, "practice", intensity="medium")
    assert low["carbs_g"] < med["carbs_g"]

def test_medium_intensity_matches_no_intensity_baseline():
    med  = nc.calc_daily_targets(ATH, "practice", intensity="medium")
    base = nc.calc_daily_targets(ATH, "practice")  # no intensity
    assert med["carbs_g"] == base["carbs_g"]

def test_high_intensity_is_higher_than_medium():
    med  = nc.calc_daily_targets(ATH, "practice", intensity="medium")
    high = nc.calc_daily_targets(ATH, "practice", intensity="high")
    assert high["carbs_g"] > med["carbs_g"]

def test_game_overrides_intensity_to_hard():
    # Game day forces "hard" CHO intensity via the activity engine, so the
    # caller-supplied intensity must NOT change the carb target on a game day.
    low  = nc.calc_daily_targets(ATH, "game", intensity="low")
    high = nc.calc_daily_targets(ATH, "game", intensity="high")
    assert low["carbs_g"] == high["carbs_g"]

def test_intensity_carbs_stay_within_science_bounds():
    # Across all practice intensities the carb target stays in a sane g/kg range.
    wt_kg = nc.lbs_to_kg(ATH["weight_lbs"])
    for intensity in ("low", "medium", "high"):
        t = nc.calc_daily_targets(ATH, "practice", intensity=intensity)
        g_per_kg = t["carbs_g"] / wt_kg
        assert 2.0 <= g_per_kg <= 12.0


def test_activity_type_override_drives_profile():
    base = nc.calc_daily_targets(ATH, "practice")
    over = nc.calc_daily_targets(ATH, "practice", activity_type="game")
    assert over["carbs_g"] > base["carbs_g"]


def test_activity_type_active_recovery_gives_rest_cho():
    wt = nc.lbs_to_kg(ATH["weight_lbs"])
    t = nc.calc_daily_targets(ATH, "practice", activity_type="active_recovery")
    assert round(t["carbs_g"] / wt) == 4


def test_activity_type_strength_cond_sets_sc_protein_bump():
    practice = nc.calc_daily_targets(ATH, "practice")
    sc = nc.calc_daily_targets(ATH, "practice", activity_type="strength_cond")
    assert sc["protein_g"] >= practice["protein_g"]


def test_invalid_activity_type_falls_back_to_event_type():
    a = nc.calc_daily_targets(ATH, "game", activity_type="bogus")
    b = nc.calc_daily_targets(ATH, "game")
    assert a["carbs_g"] == b["carbs_g"]


def test_no_activity_type_unchanged():
    a = nc.calc_daily_targets(ATH, "game")
    b = nc.calc_daily_targets(ATH, "game", activity_type=None)
    assert a == b
