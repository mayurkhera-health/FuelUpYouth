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
