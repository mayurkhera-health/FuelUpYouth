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
