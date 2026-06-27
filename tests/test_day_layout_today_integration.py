import os
os.environ["DB_PATH"] = ":memory:"
from datetime import datetime
from api.services.day_layout import build_day_layout, day_layout_v2_enabled


def test_flag_helper_reads_env(monkeypatch):
    monkeypatch.setenv("DAY_LAYOUT_V2", "true")
    assert day_layout_v2_enabled() is True
    monkeypatch.delenv("DAY_LAYOUT_V2", raising=False)
    assert day_layout_v2_enabled() is False


def test_to_template_windows_shape():
    from api.services.day_layout import cards_to_template_windows
    ev = {"id": 1, "event_type": "practice", "activity_type": "practice",
          "event_date": "2026-06-27", "start_time": "15:00", "duration_hours": 1.0}
    res = build_day_layout([ev], {"id": 1, "weight_lbs": 120, "height_ft": 5,
                                  "height_in": 4, "gender": "boy", "age": 14},
                           now=datetime(2026, 6, 27, 6, 0))
    tw = cards_to_template_windows(res["cards"])
    assert tw and all({"key", "label", "category", "sort_time"} <= set(w) for w in tw)
    # event marker maps to a nudge-only (non-tappable) window
    ev_win = next(w for w in tw if w["category"] == "event")
    assert ev_win["is_nudge_only"] is True
