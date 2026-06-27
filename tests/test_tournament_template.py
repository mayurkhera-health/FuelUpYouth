from api.services.tournament_template import get_tournament_template


def test_everyday_meal_before_when_first_game_at_or_after_11am():
    sched = [{"start_time": "11:00", "duration_min": 90}]
    cards = get_tournament_template(sched, 50)
    assert cards[0]["card"] == "everyday_meal"
    assert cards[0]["title"] == "Tournament Base Meal"


def test_everyday_meal_after_when_first_game_before_11am():
    sched = [{"start_time": "09:00", "duration_min": 90}]
    cards = get_tournament_template(sched, 50)
    assert cards[0]["card"] != "everyday_meal"          # not first
    assert cards[-1]["card"] == "everyday_meal"          # last
    assert cards[-1]["title"] == "Wind-Down Meal"


def test_per_game_windows_and_keep_going_over_75():
    sched = [{"start_time": "09:00", "duration_min": 90}]
    cards = get_tournament_template(sched, 50)
    kinds = [c["card"] for c in cards]
    assert "fuel_before" in kinds and "top_up" in kinds and "event" in kinds
    assert "keep_going" in kinds                          # 90 > 75


def test_no_keep_going_under_75():
    sched = [{"start_time": "09:00", "duration_min": 60}]
    cards = get_tournament_template(sched, 50)
    assert "keep_going" not in [c["card"] for c in cards]


def test_between_game_recharge_at_45_rebuild_at_90():
    # game1 09:00-10:30, game2 12:30 -> gap 120 min -> recharge AND rebuild between
    sched = [{"start_time": "09:00", "duration_min": 90},
             {"start_time": "12:30", "duration_min": 90}]
    cards = get_tournament_template(sched, 50)
    labels = [c.get("label", "") for c in cards]
    assert any("Between Games 1 & 2" in l for l in labels)       # recharge
    assert any("Pre-Game 2 Meal" in l for l in labels)           # rebuild


def test_short_gap_recharge_only_no_rebuild():
    # game1 09:00-10:30, game2 11:30 -> gap 60 min -> recharge yes, rebuild no
    sched = [{"start_time": "09:00", "duration_min": 90},
             {"start_time": "11:30", "duration_min": 90}]
    cards = get_tournament_template(sched, 50)
    labels = [c.get("label", "") for c in cards]
    assert any("Between Games 1 & 2" in l for l in labels)
    assert not any("Pre-Game 2 Meal" in l for l in labels)


def test_post_tournament_recharge_and_rebuild_always_present():
    sched = [{"start_time": "09:00", "duration_min": 60}]
    cards = get_tournament_template(sched, 50)
    labels = [c.get("label", "") for c in cards]
    assert any("After Final Game" in l for l in labels)
    assert any("Tournament Recovery Meal" in l for l in labels)
