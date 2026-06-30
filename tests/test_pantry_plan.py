from api.services.pantry_plan import compute_slot_plan, fallback_select, fallback_replacement

ATHLETE = {"id": 1, "first_name": "A", "gender": "girl", "age": 15}

def _sched(types):  # types: list of 7 event_type strings
    return [{"date": f"2026-06-{1+i:02d}", "event_type": t, "duration_min": 90 if t!="rest" else 0}
            for i, t in enumerate(types)]

def _targets(n, iron_flag=False):
    return [{"carbs_g": 300, "protein_g": 90, "hydration_oz": 80, "iron_flag": iron_flag} for _ in range(n)]

def test_rest_week_is_lean_no_hydration_must_have():
    plan = compute_slot_plan(_sched(["rest"]*7), _targets(7), ATHLETE)
    slots = {s["meal_context"]: s for s in plan["slots"]}
    assert slots["pre_training_fuel"]["count"] == 2
    assert slots["post_training_recovery"]["count"] == 2
    assert slots["hydration"]["must_have"] is False

def test_game_heavy_week_scales_up_and_hydration_must_have():
    plan = compute_slot_plan(_sched(["game","practice","game","practice","tournament","rest","rest"]), _targets(7), ATHLETE)
    slots = {s["meal_context"]: s for s in plan["slots"]}
    assert slots["pre_training_fuel"]["count"] > 2
    assert slots["post_training_recovery"]["count"] > 2
    assert slots["hydration"]["must_have"] is True
    assert plan["week_summary"]["game_days"] == 2
    assert plan["week_summary"]["tournament_days"] == 1

def test_iron_emphasis_sets_iron_priority():
    plan = compute_slot_plan(_sched(["practice"]*3 + ["rest"]*4), _targets(7, iron_flag=True), ATHLETE)
    slots = {s["meal_context"]: s for s in plan["slots"]}
    assert slots["post_training_recovery"].get("iron_priority") is True
    assert plan["week_summary"]["iron_emphasis"] is True

SAFE = [
    {"food_id": "rice", "name": "Rice", "role": "carb", "gi_tier": "fast", "iron_mg": 1},
    {"food_id": "oats", "name": "Oats", "role": "carb", "gi_tier": "slow", "iron_mg": 2},
    {"food_id": "banana", "name": "Banana", "role": "carb", "gi_tier": "fast", "iron_mg": 0},
    {"food_id": "chicken", "name": "Chicken", "role": "protein", "gi_tier": "slow", "iron_mg": 1},
    {"food_id": "lentils", "name": "Lentils", "role": "protein", "gi_tier": "slow", "iron_mg": 6},
    {"food_id": "spinach", "name": "Spinach", "role": "produce", "gi_tier": "slow", "iron_mg": 3},
    {"food_id": "water", "name": "Water", "role": "hydration", "gi_tier": "slow", "iron_mg": 0},
]

def test_fallback_fills_plan_no_dupes_only_safe():
    plan = {"slots": [
        {"meal_context": "pre_training_fuel", "count": 2, "roles": ["carb"], "gi_tier": "fast", "must_have": True},
        {"meal_context": "post_training_recovery", "count": 1, "roles": ["protein"], "must_have": True, "iron_priority": True},
        {"meal_context": "hydration", "count": 1, "roles": ["hydration"], "must_have": True},
    ]}
    items = fallback_select(plan, SAFE, {})
    ids = [i["food_id"] for i in items]
    assert len(ids) == len(set(ids)), "no duplicate foods"
    assert all(any(f["food_id"] == i["food_id"] for f in SAFE) for i in items)
    pre = [i for i in items if i["meal_context"] == "pre_training_fuel"]
    assert len(pre) == 2 and all(next(f for f in SAFE if f["food_id"] == i["food_id"])["gi_tier"] == "fast" for i in pre)
    post = next(i for i in items if i["meal_context"] == "post_training_recovery")
    assert post["food_id"] == "lentils"  # iron_priority → highest iron_mg protein
    assert all(i["must_have"] for i in items)

def test_fallback_replacement_same_role_not_in_current():
    fid = fallback_replacement("carb", "fast", SAFE, {"rice"})
    assert fid in {"banana"}  # fast carb, not rice
    assert fallback_replacement("hydration", None, SAFE, {"water"}) is None  # none left
