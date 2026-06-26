from api.services.window_distribution import SLOT_TO_SPLIT, split_key_for_slot


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
