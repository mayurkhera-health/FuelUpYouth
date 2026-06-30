from api.services.pantry_plan import compute_slot_plan

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
