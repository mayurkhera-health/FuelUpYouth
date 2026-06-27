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


def _as_wev2_event(ev: dict):
    """Adapt a plain event dict to the attribute access wev2 timing helpers expect."""
    return wev2.Event(
        id=ev.get("id", 0), athlete_id=ev.get("athlete_id", 0),
        event_type=ev["event_type"], event_date=ev["event_date"],
        start_time=ev["start_time"], duration_hours=ev.get("duration_hours"),
    )


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


def _standard_single_event_cards(ev: dict, start_dt: datetime, end_dt: datetime) -> list:
    """Spec order for a single non-tournament event. everyday_meal placement flips
    on the 11:00 boundary; keep_going only when duration > 75 min."""
    dur_min = int(round((ev.get("duration_hours") or 1.5) * 60))
    morning = start_dt.hour < 11

    def card(key, kind, sort_dt, label, is_event=False, duration_min=None):
        return {"key": key, "card": kind, "label": label,
                "is_event": is_event, "is_tappable": not is_event,
                "sort_time": wev2._hhmm(sort_dt), "time_display": "",
                "game_num": None, "duration_min": duration_min}

    if morning:
        everyday_sort = end_dt + timedelta(hours=2)          # after rebuild → sorts LAST
    else:
        everyday_sort = start_dt.replace(hour=7, minute=30)  # earliest → sorts FIRST
    everyday = card("everyday_meal", "everyday_meal", everyday_sort, "Everyday Meal")

    core = [
        card("fuel_before", "fuel_before", start_dt - timedelta(hours=3), "Fuel Before"),
        card("top_up", "top_up", start_dt - timedelta(minutes=45), "Top-Up"),
        card("event", "event", start_dt,
             ev.get("event_name") or ev["event_type"].capitalize(),
             is_event=True, duration_min=dur_min),
    ]
    if dur_min > 75:
        core.append(card("keep_going", "keep_going", start_dt + timedelta(minutes=dur_min // 2),
                         "Keep Going", duration_min=dur_min))
    core += [
        card("recharge", "recharge", end_dt, "Recharge"),
        card("rebuild", "rebuild", end_dt + timedelta(hours=1), "Rebuild"),
    ]

    # everyday placement: morning -> last, afternoon/evening -> first
    return core + [everyday] if morning else [everyday] + core


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

    # Single non-tournament event -> standard layout.
    primary_ev, _ = resolved[0]
    start_dt = wev2._parse_start(_as_wev2_event(primary_ev))
    end_dt = wev2._event_end(_as_wev2_event(primary_ev), start_dt)
    cards = _standard_single_event_cards(primary_ev, start_dt, end_dt)
    return {"day_type": "standard", "cards": cards}
