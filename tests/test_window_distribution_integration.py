from api.services.window_distribution import (
    SLOT_TO_SPLIT,
    split_key_for_slot,
    distribute_to_slots,
    validate_windows,
)


def test_hyphen_taxonomy_maps_to_splits():
    assert split_key_for_slot("pre-game-fuel") == "fuel_before"
    assert split_key_for_slot("pre-training") == "fuel_before"
    assert split_key_for_slot("power-snack") == "top_up"
    assert split_key_for_slot("recovery-fuel") == "recharge"
    assert split_key_for_slot("recovery-dinner") == "rebuild"
    assert split_key_for_slot("breakfast") == "everyday_meal"
    assert split_key_for_slot("lunch") == "everyday_meal"
    assert split_key_for_slot("dinner") == "everyday_meal"
    assert split_key_for_slot("mid-morning-snack") == "everyday_meal"
    assert split_key_for_slot("afternoon-snack") == "everyday_meal"
    assert split_key_for_slot("between-games") == "recharge"
    assert split_key_for_slot("halftime-fueling") == "keep_going"


def test_bedtime_casein_maps_to_rebuild_v1_default():
    # Open decision #2 — v1 default maps casein/night slots to rebuild
    assert split_key_for_slot("night-fuel") == "rebuild"
    assert split_key_for_slot("evening-recovery") == "rebuild"


def test_hydration_only_slots_map_to_none():
    assert split_key_for_slot("daily-hydration") is None
    assert split_key_for_slot("during-game-hydration") is None
    assert split_key_for_slot("during-practice-hydration") is None


def test_unknown_slot_maps_to_none():
    assert split_key_for_slot("totally-unknown-slot") is None


def test_v2_underscore_and_suffixed_variants():
    # v2 underscore exact-match keys
    assert split_key_for_slot("everyday_breakfast") == "everyday_meal"
    assert split_key_for_slot("fuel_after_primary") == "recharge"
    # suffixed tournament/double-day variants resolve via prefix match
    assert split_key_for_slot("fuel_after_primary_1") == "recharge"
    assert split_key_for_slot("between_games_1_2") == "recharge"
    assert split_key_for_slot("fuel_after_second_2") == "rebuild"
    # refuel_ready is prefix-only (not an exact SLOT_TO_SPLIT key)
    assert split_key_for_slot("refuel_ready_1_2") == "recharge"


def _slots(*names):
    """Minimal slot dicts as compute_meal_slots emits (only keys the adapter reads)."""
    return [{"slot_name": n, "is_hydration": n.endswith("hydration")} for n in names]


def test_distribute_skips_hydration_and_unknown():
    slots = _slots("daily-hydration", "during-game-hydration", "totally-unknown")
    out = distribute_to_slots(slots, daily_cho_g=300, daily_prot_g=100, wt_kg=55)
    assert out == {}  # nothing allocatable


def test_distribute_single_of_each_matches_validate_windows():
    # One slot per window → grams equal validate_windows() exactly (no division)
    slots = _slots("pre-game-fuel", "power-snack", "recovery-fuel", "recovery-dinner", "breakfast")
    out = distribute_to_slots(slots, daily_cho_g=326, daily_prot_g=101, wt_kg=54.4)
    w = validate_windows(54.4, 326, 101, is_sc_day=False)
    assert out["pre-game-fuel"]["cho_g"] == w["fuel_before"]["cho_g"]
    assert out["recovery-fuel"]["prot_g"] == w["recharge"]["prot_g"]
    assert out["breakfast"]["cho_g"] == w["everyday_meal"]["cho_g"]


def test_distribute_even_division_across_duplicate_window():
    # 4 everyday_meal slots split the everyday_meal bucket evenly
    slots = _slots("breakfast", "mid-morning-snack", "lunch", "dinner")
    out = distribute_to_slots(slots, daily_cho_g=320, daily_prot_g=100, wt_kg=55)
    w = validate_windows(55, 320, 100, is_sc_day=False)
    expected_cho = round(w["everyday_meal"]["cho_g"] / 4)
    for n in ("breakfast", "mid-morning-snack", "lunch", "dinner"):
        assert out[n]["cho_g"] == expected_cho


def test_distribute_carries_ratio_flag():
    slots = _slots("recovery-fuel")
    out = distribute_to_slots(slots, daily_cho_g=326, daily_prot_g=101, wt_kg=54.4)
    # recharge ratio ~2.17 < 3.0 floor → RATIO_LOW flag carried through
    assert out["recovery-fuel"]["flag"] is not None
    assert "RATIO_LOW" in out["recovery-fuel"]["flag"]


def test_distribute_sc_day_shifts_recharge_protein():
    slots = _slots("recovery-fuel")
    base = distribute_to_slots(slots, 326, 60, wt_kg=54.4, is_sc_day=False)
    sc   = distribute_to_slots(slots, 326, 60, wt_kg=54.4, is_sc_day=True)
    assert sc["recovery-fuel"]["prot_g"] > base["recovery-fuel"]["prot_g"]


def test_distribute_recomputes_per_slot_ratio_after_division():
    # When N slots share a window, each slot's ratio must reflect its own
    # rounded grams, not the window total's ratio.
    slots = _slots("breakfast", "mid-morning-snack", "lunch")  # 3 everyday_meal
    out = distribute_to_slots(slots, daily_cho_g=320, daily_prot_g=100, wt_kg=55)
    for n in ("breakfast", "mid-morning-snack", "lunch"):
        cho_g, prot_g = out[n]["cho_g"], out[n]["prot_g"]
        expected = round(cho_g / prot_g, 2) if prot_g > 0 else 0
        assert out[n]["ratio"] == expected


import os
from api.services.today_service import build_mission_items_from_slots


def _mission_slots(*names):
    return [{"slot_name": n, "display_label": n.title(), "eat_by_time": "8:00 AM",
             "is_hydration": n.endswith("hydration")} for n in names]


def test_mission_uses_distribution_when_flag_on(monkeypatch):
    monkeypatch.setenv("EVENT_RELATIVE_WINDOWS", "true")
    slots = _mission_slots("recovery-fuel")
    targets = {"carbs_g": 326, "protein_g": 101}
    items = build_mission_items_from_slots(
        slots, {}, targets, wt_kg=54.4, is_sc_day=False, duration_min=75,
    )
    from api.services.window_distribution import validate_windows
    w = validate_windows(54.4, 326, 101, is_sc_day=False)
    assert items[0]["carbs_g"] == w["recharge"]["cho_g"]
    assert items[0]["protein_g"] == w["recharge"]["prot_g"]


def test_mission_falls_back_to_focus_pct_when_flag_off(monkeypatch):
    monkeypatch.delenv("EVENT_RELATIVE_WINDOWS", raising=False)
    slots = _mission_slots("recovery-fuel")
    targets = {"carbs_g": 326, "protein_g": 101}
    items = build_mission_items_from_slots(
        slots, {}, targets, wt_kg=54.4, is_sc_day=False, duration_min=75,
    )
    # Legacy path: recovery-fuel → "Recovery Focus" → carbs_pct 0.15
    assert items[0]["carbs_g"] == round(326 * 0.15)
    assert items[0]["protein_g"] == round(101 * 0.25)


def test_mission_falls_back_when_wt_kg_missing(monkeypatch):
    monkeypatch.setenv("EVENT_RELATIVE_WINDOWS", "true")
    slots = _mission_slots("recovery-fuel")
    targets = {"carbs_g": 326, "protein_g": 101}
    # No wt_kg → cannot run validate_windows → legacy path
    items = build_mission_items_from_slots(slots, {}, targets)
    assert items[0]["carbs_g"] == round(326 * 0.15)
    assert items[0]["protein_g"] == round(101 * 0.25)


# ── End-to-end tests: compute_meal_slots → build_mission_items_from_slots ─────

from api.services.meal_timing import compute_meal_slots


def test_e2e_event_day_totals_stay_within_daily(monkeypatch):
    """Per-slot grams summed across an event day must not exceed the daily total."""
    monkeypatch.setenv("EVENT_RELATIVE_WINDOWS", "true")
    slots = compute_meal_slots("practice", "16:00", 1.5)
    targets = {"carbs_g": 326, "protein_g": 101}
    items = build_mission_items_from_slots(
        slots, {}, targets, wt_kg=54.4, is_sc_day=False, duration_min=90,
    )
    total_cho  = sum(it.get("carbs_g", 0)   for it in items)
    total_prot = sum(it.get("protein_g", 0) for it in items)
    # Even-division preserves totals; allow small rounding drift (±1 per window).
    assert total_cho  <= 326 + 6
    assert total_prot <= 101 + 6
    # And it should allocate a meaningful share (not near-zero)
    assert total_cho  >= 326 * 0.8


def test_e2e_rest_day_everyday_meals_only(monkeypatch):
    monkeypatch.setenv("EVENT_RELATIVE_WINDOWS", "true")
    slots = compute_meal_slots("rest", None, None)
    targets = {"carbs_g": 250, "protein_g": 90}
    items = build_mission_items_from_slots(
        slots, {}, targets, wt_kg=50, is_sc_day=False, duration_min=0,
    )
    # evening-recovery maps to "rebuild" (not everyday_meal) per SLOT_TO_SPLIT;
    # daily-hydration is skipped. So only the 5 everyday_meal slots share one value
    # and evening-recovery (rebuild) may differ -- filter to everyday_meal only.
    everyday_cho = {
        it["carbs_g"] for it in items
        if "carbs_g" in it and split_key_for_slot(it["meal_type"]) == "everyday_meal"
    }
    assert len(everyday_cho) == 1  # all everyday_meal slots share one even-divided value
    assert everyday_cho.pop() > 0
