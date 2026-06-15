"""
Nudge engine: rest day is NOT a skip — same window logic, recovery tone.
day_type only changes COPY (tone) and nudge cadence, never whether we fuel.
"""

from datetime import datetime

REST_CADENCE     = ["12:00", "18:00"]                             # 2 gentle nudges on rest day
TRAINING_CADENCE = ["07:00", "11:30", "15:00", "17:30", "19:30"] # 5 nudges on training/practice/game


def _tone_for(day_type: str) -> str:
    return "recovery" if (day_type or "rest").lower() == "rest" else "training"


def _phase_for(window: dict, now: datetime) -> str:
    eat_by = window.get("eat_by_time", "")
    if not eat_by:
        return "upcoming"
    try:
        target = datetime.strptime(eat_by, "%I:%M %p").replace(
            year=now.year, month=now.month, day=now.day
        )
        diff_mins = (target - now).total_seconds() / 60
        if diff_mins > 30:
            return "upcoming"
        if diff_mins >= -15:
            return "now"
        return "between"
    except ValueError:
        return "upcoming"


def _build_window_nudge(athlete: dict, target: dict, phase: str, tone: str) -> dict:
    name = target.get("display_label", "your next window")
    if tone == "recovery":
        if phase == "now":
            headline = f"{name} — this is where you rebuild"
            why = "Rest days are when your body gets stronger. Fuel now, come back faster."
        elif phase == "upcoming":
            headline = f"{name} coming up — keep your recovery going"
            why = "Consistent rest-day fueling is the habit elite athletes build."
        else:
            headline = "Nice work — keep your recovery fueling on track"
            why = "Every window you hit on a rest day builds your base."
    else:
        eat_by = target.get("eat_by_time", "")
        if phase == "now":
            headline = f"Fuel up now — {name}"
            why = "This window keeps your energy dialed in for the rest of the day."
        elif phase == "upcoming":
            headline = f"{name} coming up at {eat_by}" if eat_by else f"{name} coming up"
            why = "Hitting your windows on time locks in your energy levels."
        else:
            headline = f"Next move at {eat_by}" if eat_by else "Your next fuel window is coming up"
            why = "Stay on track — your next window is coming up soon."

    return {
        "phase":         phase,
        "tone":          tone,
        "headline":      headline,
        "why":           why,
        "target_window": target,
    }


def _done_for_day(athlete: dict, tone: str) -> dict:
    name = athlete.get("first_name", "")
    suffix = f", {name}" if name else ""
    if tone == "recovery":
        headline = f"Recovery fuel done{suffix} — body is rebuilding"
        why = "Rest-day fueling is when the gains from the week lock in."
    else:
        headline = f"All windows done{suffix} — great fueling today"
        why = "Consistent logging is how you build real match fitness."
    return {"phase": "done_for_day", "tone": tone, "headline": headline, "why": why, "target_window": None}


def generate_current_nudge(athlete: dict, windows: list, now: datetime, day_type: str) -> dict:
    """
    Rest day is NOT a skip. Same window/move logic as any day.
    day_type only influences tone (copy) and cadence — never whether we fuel.
    """
    tone = _tone_for(day_type)
    pending = [
        w for w in sorted(windows, key=lambda x: x.get("eat_by_time", ""))
        if not w.get("log", {}).get("logged", False)
    ]
    if not pending:
        return _done_for_day(athlete, tone=tone)

    target = pending[0]
    phase  = _phase_for(target, now)
    return _build_window_nudge(athlete, target, phase, tone=tone)


def schedule_day_nudges(day_type: str, windows: list, athlete: dict) -> list[tuple[str, str]]:
    """
    Returns list of (slot_name, headline) pairs to enqueue for push delivery.
    Rest day gets REST_CADENCE (2 nudges) — never zero.
    """
    tone    = _tone_for(day_type)
    cadence = REST_CADENCE if tone == "recovery" else TRAINING_CADENCE
    pending = [w for w in windows if not w.get("log", {}).get("logged", False)]
    now     = datetime.now()

    result = []
    for w in pending[: len(cadence)]:
        nudge = _build_window_nudge(athlete, w, "upcoming", tone)
        result.append((w["slot_name"], nudge["headline"]))
    return result
