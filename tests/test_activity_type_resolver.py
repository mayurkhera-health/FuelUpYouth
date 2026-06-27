from datetime import datetime
from api.services.activity_type_resolver import resolve_activity_type

VALID = {"practice", "game", "tournament", "speed_sprint",
         "strength_cond", "active_recovery", "double_session"}


def _ev(activity_type=None, event_date="2026-06-27", start_time="15:00"):
    return {"activity_type": activity_type, "event_date": event_date, "start_time": start_time}


def test_explicit_tag_always_wins():
    ev = _ev(activity_type="game")
    now = datetime(2026, 6, 25, 8, 0)   # days before
    assert resolve_activity_type(ev, now) == "game"


def test_untagged_stays_none_more_than_2h_before_start():
    ev = _ev(activity_type=None, start_time="15:00")
    now = datetime(2026, 6, 27, 12, 0)   # 3h before start
    assert resolve_activity_type(ev, now) is None


def test_untagged_defaults_to_practice_at_exactly_2h_before():
    ev = _ev(activity_type=None, start_time="15:00")
    now = datetime(2026, 6, 27, 13, 0)   # exactly 2h before
    assert resolve_activity_type(ev, now) == "practice"


def test_untagged_defaults_to_practice_after_start():
    ev = _ev(activity_type=None, start_time="15:00")
    now = datetime(2026, 6, 27, 16, 0)   # after start
    assert resolve_activity_type(ev, now) == "practice"


def test_invalid_stored_value_treated_as_untagged():
    ev = _ev(activity_type="bogus", start_time="15:00")
    now = datetime(2026, 6, 27, 10, 0)   # >2h before
    assert resolve_activity_type(ev, now) is None


def test_no_start_time_defaults_to_practice_when_tagged_blank():
    # All-day / no start_time: cannot compute a 2h boundary -> treat as practice
    ev = _ev(activity_type=None, start_time=None)
    now = datetime(2026, 6, 27, 10, 0)
    assert resolve_activity_type(ev, now) == "practice"
