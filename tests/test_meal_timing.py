import pytest
from api.services.meal_timing import compute_meal_slots


def slot_names(slots):
    return [s["slot_name"] for s in slots]


def slot_by_name(slots, name):
    return next((s for s in slots if s["slot_name"] == name), None)


def test_rest_day_returns_7_slots():
    slots = compute_meal_slots(None, None, None)
    assert len(slots) == 7


def test_rest_day_slot_names():
    slots = compute_meal_slots(None, None, None)
    assert slot_names(slots) == [
        "breakfast", "mid-morning-snack", "lunch", "afternoon-snack",
        "dinner", "evening-recovery", "daily-hydration",
    ]


def test_rest_day_no_performance_slots():
    slots = compute_meal_slots(None, None, None)
    names = slot_names(slots)
    assert "pre-training" not in names
    assert "power-snack" not in names
    assert "halftime-fueling" not in names


def test_rest_day_hydration_slot_is_informational():
    slots = compute_meal_slots(None, None, None)
    hyd = slot_by_name(slots, "daily-hydration")
    assert hyd["is_hydration"] is True
    assert hyd["recipe_category"] is None


def test_training_pre_event_calculated():
    slots = compute_meal_slots("practice", "16:00", 1.5)
    pre = slot_by_name(slots, "pre-training")
    assert pre is not None
    assert pre["eat_by_time"] == "1:00 PM"


def test_training_power_snack_calculated():
    slots = compute_meal_slots("practice", "16:00", 1.5)
    snack = slot_by_name(slots, "power-snack")
    assert snack is not None
    assert snack["eat_by_time"] == "3:15 PM"


def test_training_recovery_fuel_calculated():
    slots = compute_meal_slots("practice", "16:00", 1.5)
    recovery = slot_by_name(slots, "recovery-fuel")
    assert recovery is not None
    assert recovery["eat_by_time"] == "6:00 PM"


def test_training_separate_dinner_when_ends_before_19():
    slots = compute_meal_slots("practice", "16:00", 1.5)
    dinner = slot_by_name(slots, "dinner")
    assert dinner is not None
    recovery = slot_by_name(slots, "recovery-fuel")
    assert recovery is not None


def test_late_training_merges_recovery_and_dinner():
    slots = compute_meal_slots("practice", "19:30", 1.5)
    assert slot_by_name(slots, "recovery-fuel") is None
    assert slot_by_name(slots, "night-fuel") is None
    merged = slot_by_name(slots, "recovery-dinner")
    assert merged is not None
    assert merged["is_merged"] is True


def test_late_training_merged_slot_has_correct_tags():
    slots = compute_meal_slots("practice", "19:30", 1.5)
    merged = slot_by_name(slots, "recovery-dinner")
    assert "High Protein" in merged["tags"]
    assert "Fast Carbs" in merged["tags"]


def test_late_training_has_note():
    slots = compute_meal_slots("practice", "19:30", 1.5)
    merged = slot_by_name(slots, "recovery-dinner")
    assert "recovery" in merged["note"].lower()


def test_game_has_halftime_slot():
    slots = compute_meal_slots("game", "14:00", 1.5)
    halftime = slot_by_name(slots, "halftime-fueling")
    assert halftime is not None
    assert halftime["eat_by_time"] == "2:45 PM"


def test_game_pre_game_fuel_calculated():
    slots = compute_meal_slots("game", "14:00", 1.5)
    pre = slot_by_name(slots, "pre-game-fuel")
    assert pre["eat_by_time"] == "11:00 AM"


def test_early_game_removes_pre_game_fuel():
    slots = compute_meal_slots("game", "07:00", 1.5)
    assert slot_by_name(slots, "pre-game-fuel") is None


def test_early_game_keeps_power_snack():
    slots = compute_meal_slots("game", "07:00", 1.5)
    snack = slot_by_name(slots, "power-snack")
    assert snack is not None
    assert "Early" in snack["note"]


def test_double_day_adds_between_games_slot():
    slots = compute_meal_slots("game", "10:00", 1.5, double_day=True, second_start_time="14:00")
    between = slot_by_name(slots, "between-games")
    assert between is not None


def test_double_day_calorie_boost_flag():
    slots = compute_meal_slots("game", "10:00", 1.5, double_day=True, second_start_time="14:00")
    assert any(s.get("double_day_alert") for s in slots)
