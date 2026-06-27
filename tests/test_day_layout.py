from datetime import datetime
from api.services.day_layout import build_day_layout


def _athlete():
    return {"id": 1, "weight_lbs": 120, "height_ft": 5, "height_in": 4,
            "gender": "boy", "age": 14}


def test_rest_day_three_meals_3334():
    # No events -> rest day -> breakfast/lunch/dinner
    res = build_day_layout([], _athlete(), now=datetime(2026, 6, 27, 7, 0))
    assert res["day_type"] == "rest"
    kinds = [c["card"] for c in res["cards"]]
    assert kinds == ["breakfast", "lunch", "dinner"]
    assert all(c["is_tappable"] for c in res["cards"])


def test_active_recovery_uses_rest_style_three_meals():
    ev = {"id": 9, "event_type": "practice", "activity_type": "active_recovery",
          "event_date": "2026-06-27", "start_time": "10:00", "duration_hours": 1.0}
    res = build_day_layout([ev], _athlete(), now=datetime(2026, 6, 27, 6, 0))
    assert res["day_type"] == "active_recovery"
    kinds = [c["card"] for c in res["cards"]]
    assert kinds == ["breakfast", "lunch", "dinner"]


def test_morning_event_order_everyday_last():
    # Practice starting 09:00 (<11:00) -> fuel_before -> top_up -> event -> recharge -> rebuild -> everyday_meal
    ev = {"id": 1, "event_type": "practice", "activity_type": "practice",
          "event_date": "2026-06-27", "start_time": "09:00", "duration_hours": 1.0}
    res = build_day_layout([ev], _athlete(), now=datetime(2026, 6, 27, 6, 0))
    kinds = [c["card"] for c in res["cards"]]
    assert kinds == ["fuel_before", "top_up", "event", "recharge", "rebuild", "everyday_meal"]
    # event marker is visible, non-tappable
    event_card = next(c for c in res["cards"] if c["card"] == "event")
    assert event_card["is_event"] is True and event_card["is_tappable"] is False


def test_afternoon_event_order_everyday_first():
    # Practice starting 15:00 (>=11:00) -> everyday_meal -> fuel_before -> top_up -> event -> recharge -> rebuild
    ev = {"id": 1, "event_type": "practice", "activity_type": "practice",
          "event_date": "2026-06-27", "start_time": "15:00", "duration_hours": 1.0}
    res = build_day_layout([ev], _athlete(), now=datetime(2026, 6, 27, 6, 0))
    kinds = [c["card"] for c in res["cards"]]
    assert kinds == ["everyday_meal", "fuel_before", "top_up", "event", "recharge", "rebuild"]


def test_keep_going_appears_only_over_75min():
    long_ev = {"id": 1, "event_type": "game", "activity_type": "game",
               "event_date": "2026-06-27", "start_time": "15:00", "duration_hours": 1.5}  # 90 min
    res = build_day_layout([long_ev], _athlete(), now=datetime(2026, 6, 27, 6, 0))
    assert "keep_going" in [c["card"] for c in res["cards"]]

    short_ev = {**long_ev, "duration_hours": 1.0}  # 60 min
    res2 = build_day_layout([short_ev], _athlete(), now=datetime(2026, 6, 27, 6, 0))
    assert "keep_going" not in [c["card"] for c in res2["cards"]]
