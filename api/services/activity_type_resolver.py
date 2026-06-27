"""
Activity-type resolution with the 2-hour silent default.

An event's activity_type is either explicitly tagged by the athlete (one of the
7 engine keys) or untagged. Untagged events stay None (the UI keeps nudging)
until `now` reaches 2 hours before the event start, at which point they silently
resolve to 'practice' so the fueling plan locks in before the event.
"""

from datetime import datetime, timedelta

VALID_ACTIVITY_TYPES = {
    "practice", "game", "tournament", "speed_sprint",
    "strength_cond", "active_recovery", "double_session",
}

DEFAULT_ACTIVITY_TYPE = "practice"
AUTO_DEFAULT_LEAD_HOURS = 2


def resolve_activity_type(event: dict, now: datetime):
    """Return the effective activity_type, or None if still awaiting a tag.

    event needs: activity_type (str|None), event_date ('YYYY-MM-DD'), start_time ('HH:MM'|None).
    """
    tag = event.get("activity_type")
    if tag in VALID_ACTIVITY_TYPES:
        return tag

    start_time = event.get("start_time")
    event_date = event.get("event_date")
    if not start_time or not event_date:
        # No usable start boundary -> lock in the default immediately.
        return DEFAULT_ACTIVITY_TYPE

    start_dt = datetime.strptime(f"{event_date} {start_time}", "%Y-%m-%d %H:%M")
    deadline = start_dt - timedelta(hours=AUTO_DEFAULT_LEAD_HOURS)
    if now >= deadline:
        return DEFAULT_ACTIVITY_TYPE
    return None
