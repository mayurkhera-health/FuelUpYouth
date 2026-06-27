"""
Day Layout Engine — Today-tab fuel-window card ordering (Purvi spec).

Produces the ordered card list for a day from its events + resolved activity
types. Reuses window_engine_v2 timing primitives; grams are overlaid downstream.
Replaces window_engine_v2 as the Today-tab window source (behind DAY_LAYOUT_V2).

Public API: build_day_layout(events, athlete, now) -> {"day_type", "cards"}
"""

from datetime import datetime, time, timedelta

from api.services.activity_type_resolver import resolve_activity_type
from api.services.tournament_template import get_tournament_template
from api.services import window_engine_v2 as wev2

REST_MEAL_TIMES = {"breakfast": "07:30", "lunch": "12:30", "dinner": "18:30"}


def _rest_meal_cards() -> list:
    """Breakfast/Lunch/Dinner rest-style cards (33/34/33 split applied downstream)."""
    cards = []
    for kind in ("breakfast", "lunch", "dinner"):
        t = REST_MEAL_TIMES[kind]
        cards.append({
            "key": kind, "card": kind, "label": kind.capitalize(),
            "is_event": False, "is_tappable": True,
            "sort_time": t, "time_display": "", "game_num": None, "duration_min": None,
        })
    return cards


def build_day_layout(events: list, athlete: dict, now: datetime) -> dict:
    """Return {"day_type": str, "cards": [card, ...]} for the athlete's day.

    events: rows for the target date (each a dict with event_type, activity_type,
            event_date, start_time, duration_hours).
    """
    # Resolve each event's effective activity type (2-hour default).
    resolved = []
    for ev in events:
        at = resolve_activity_type(ev, now)
        resolved.append((ev, at))

    # Rest day — no events at all.
    if not resolved:
        return {"day_type": "rest", "cards": _rest_meal_cards()}

    # Active Recovery / Yoga -> rest-style 3 meals regardless of time.
    if any(at == "active_recovery" for _, at in resolved):
        return {"day_type": "active_recovery", "cards": _rest_meal_cards()}

    # Other day types implemented in later tasks.
    raise NotImplementedError("standard / tournament layouts: Tasks 6-8")
