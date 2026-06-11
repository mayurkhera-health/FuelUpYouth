from datetime import datetime, timedelta


def _offset(event_date: str, start_time: str, hours: float) -> str:
    if not start_time:
        return event_date
    try:
        dt = datetime.strptime(f"{event_date} {start_time}", "%Y-%m-%d %H:%M")
        return (dt + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return event_date


def get_meal_timing_protocol(event_type: str, event_date: str, start_time: str = None) -> dict:
    norm = event_type.lower()
    if "tournament" in norm:
        steps = _tournament(event_date, start_time)
    elif "game" in norm:
        steps = _game_day(event_date, start_time)
    elif "strength" in norm or "conditioning" in norm:
        steps = _strength(event_date, start_time)
    elif "practice" in norm or "training" in norm or "agility" in norm:
        steps = _practice(event_date, start_time)
    elif "pre-game" in norm:
        steps = _pre_game_day(event_date)
    elif "recovery" in norm or "yoga" in norm:
        steps = _recovery(event_date)
    else:
        steps = _rest_day(event_date)

    return {"event_type": event_type, "event_date": event_date, "protocol": steps}


def _game_day(event_date: str, start_time: str) -> list:
    return [
        {"timing": "Night before (7pm)", "when": f"{event_date} (night before 19:00)", "what": "High carb dinner — pasta/rice + protein + milk", "why": "Glycogen loading begins 24-48hrs before kickoff (Everett MD 2025)", "recipe": "Power Pasta Bowl (R001)", "recipient": "parent", "critical": True},
        {"timing": "3hrs before kickoff", "when": _offset(event_date, start_time, -3), "what": "Pre-game breakfast — carbs + protein + OJ", "why": "3hr fuel window opens — no GI distress risk", "recipe": "Tournament Morning Plate (R023)", "recipient": "both"},
        {"timing": "45min before kickoff", "when": _offset(event_date, start_time, -0.75), "what": "Pre-game snack — banana + PB or toast + honey", "why": "Fast glucose for warm-up energy", "recipe": "Banana + PB (R006) or Toast + Honey (R007)", "recipient": "teen"},
        {"timing": "Halftime", "when": _offset(event_date, start_time, 0.75), "what": "Orange slices + 16oz water OR banana + natural sports drink", "why": "Fast glucose for second half + rehydration", "recipe": "Orange Slices (R010) or Banana + Sports Drink (R011)", "recipient": "teen"},
        {"timing": "Within 30min after final whistle", "when": _offset(event_date, start_time, 2.0), "what": "Recovery snack — chocolate milk + banana", "why": "30min window is non-negotiable for glycogen + protein synthesis", "recipe": "Choc Milk Recovery (R013)", "recipient": "both", "critical": True},
        {"timing": "1-2hrs after game", "when": _offset(event_date, start_time, 3.0), "what": "Recovery meal — protein + carbs + veg + milk", "why": "Continue glycogen restoration for 4-6hrs post game", "recipe": "Post-Practice Rebuild Plate (R019)", "recipient": "both"},
        {"timing": "Bedtime", "when": f"{event_date} 21:00", "what": "Casein snack — cottage cheese or Greek yogurt", "why": "Overnight muscle repair — critical on game days", "recipe": "Cottage Cheese + Pineapple (R017)", "recipient": "teen"},
    ]


def _strength(event_date: str, start_time: str) -> list:
    return [
        {"timing": "2hrs before", "when": _offset(event_date, start_time, -2), "what": "Carb + protein meal — rice/pasta + chicken", "why": "Fuel glycogen + prime amino acid availability", "recipe": "Strength Day Protein Plate (R022)", "recipient": "both"},
        {"timing": "30min before", "when": _offset(event_date, start_time, -0.5), "what": "Fast carb snack — banana or rice cakes", "why": "Immediate glucose for lifting performance", "recipe": "Rice Cakes + Almond Butter (R009)", "recipient": "teen"},
        {"timing": "During (if >45min)", "when": "During session", "what": "Water — electrolytes if >45min or hot", "why": "Prevent dehydration-induced strength loss", "recipe": None, "recipient": "teen"},
        {"timing": "Within 30min after", "when": _offset(event_date, start_time, 1.5), "what": "0.25-0.30g protein/kg body weight", "why": "mTORC1 activation window for muscle protein synthesis (Everett 2025)", "recipe": "Post-Practice Rebuild Plate (R019)", "recipient": "both", "critical": True},
        {"timing": "Bedtime — MANDATORY", "when": f"{event_date} 21:00", "what": "30-40g casein — cottage cheese or Greek yogurt", "why": "Overnight muscle repair proven in adolescent athletes (Everett 2025)", "recipe": "Cottage Cheese + Pineapple (R017)", "recipient": "teen", "critical": True},
    ]


def _practice(event_date: str, start_time: str) -> list:
    return [
        {"timing": "3-4hrs before practice", "when": _offset(event_date, start_time, -3.5), "what": "Pre-practice meal — carbs + protein", "why": "Fuel tank filled before high-intensity session", "recipe": "Pre-Practice Oatmeal Bowl (R018)", "recipient": "both"},
        {"timing": "30-60min before practice", "when": _offset(event_date, start_time, -0.5), "what": "Fast carb snack — banana or toast", "why": "Top up blood glucose for practice intensity", "recipe": "Banana + PB (R006)", "recipient": "teen"},
        {"timing": "Within 30min after practice", "when": _offset(event_date, start_time, 2.0), "what": "Recovery dinner — protein + carbs + veg + milk", "why": "Glycogen restoration + muscle repair window", "recipe": "Post-Practice Rebuild Plate (R019)", "recipient": "both", "critical": True},
    ]


def _pre_game_day(event_date: str) -> list:
    return [
        {"timing": "Breakfast", "when": f"{event_date} 08:00", "what": "Carb-rich breakfast", "why": "Pre-game day carb loading begins at breakfast", "recipe": "Pre-Practice Oatmeal Bowl (R018)", "recipient": "both"},
        {"timing": "Lunch", "when": f"{event_date} 12:00", "what": "Large carb + protein meal", "why": "Filling muscle glycogen — takes 24-48hrs to replenish (Everett 2025)", "recipe": "Brown Rice Salmon Bowl (R002)", "recipient": "both"},
        {"timing": "Dinner — MOST IMPORTANT MEAL OF THE WEEK", "when": f"{event_date} 19:00", "what": "HIGH CARB dinner — pasta/rice + lean protein + milk", "why": "This dinner = tomorrow's game performance. Cannot be skipped.", "recipe": "Power Pasta Bowl (R001)", "recipient": "both", "critical": True},
        {"timing": "Bedtime snack", "when": f"{event_date} 21:00", "what": "Greek yogurt or cottage cheese", "why": "Overnight casein + keeps glycogen topped", "recipe": "Cottage Cheese + Pineapple (R017)", "recipient": "teen"},
    ]


def _tournament(event_date: str, start_time: str) -> list:
    return [
        {"timing": "2-3hrs before first game", "when": _offset(event_date, start_time, -2.5), "what": "High carb breakfast — oatmeal/pancakes + protein + OJ", "why": "Multi-game day requires maximum glycogen stores", "recipe": "Tournament Morning Plate (R023)", "recipient": "both"},
        {"timing": "Between games — MANDATORY", "when": "Between each game", "what": "Banana + natural sports drink + whole grain crackers", "why": "Glycogen partially depleted after each game — must refuel immediately", "recipe": "Between-Games Refuel (R024)", "recipient": "both", "critical": True},
        {"timing": "Every 20min during each game", "when": "Throughout tournament", "what": "6-8oz natural sports drink", "why": "Electrolytes MANDATORY on tournament day — sodium critical", "recipe": None, "recipient": "teen", "critical": True},
        {"timing": "Tournament recovery dinner", "when": f"{event_date} 19:00", "what": "High protein + carb dinner + extra hydration", "why": "Multi-game glycogen depletion requires aggressive recovery", "recipe": "Tournament Recovery Dinner (R025)", "recipient": "both"},
        {"timing": "Bedtime — MANDATORY", "when": f"{event_date} 21:00", "what": "Casein protein + carbs", "why": "Multiple games = maximum muscle damage — overnight repair critical", "recipe": "Bedtime Casein Snack (R026)", "recipient": "teen", "critical": True},
    ]


def _recovery(event_date: str) -> list:
    return [
        {"timing": "All day", "when": event_date, "what": "Light carb + anti-inflammatory foods — berries, salmon, turmeric, leafy greens", "why": "Continued glycogen restoration + reduce inflammation from training load", "recipe": "Iron-Boost Hummus Plate (R020)", "recipient": "both"},
        {"timing": "Hydration focus", "when": event_date, "what": "64-72oz water — add electrolytes if previous day was a game", "why": "Rehydration continues 24-48hrs after heavy exercise", "recipe": None, "recipient": "both"},
    ]


def _rest_day(event_date: str) -> list:
    return [
        {"timing": "All meals", "when": event_date, "what": "Slightly lower carbs, maintain protein and micronutrients", "why": "Lower energy expenditure — maintain muscle protein synthesis without surplus", "recipe": None, "recipient": "both"},
        {"timing": "Iron focus (girls)", "when": event_date, "what": "Iron-rich foods — lean red meat, spinach, lentils, fortified cereal", "why": "52% of female adolescent athletes are iron deficient. Daily target: 15mg (Everett 2025)", "recipe": "Iron-Boost Hummus Plate (R020)", "recipient": "both"},
        {"timing": "Calcium — every day", "when": event_date, "what": "3 servings dairy or fortified alternatives", "why": "1,300mg/day during peak bone mass window — cannot recover later (AAP)", "recipe": None, "recipient": "both"},
    ]


# ── compute_meal_slots ─────────────────────────────────────────────────────────

def _time_from_str(t: str) -> datetime:
    return datetime.strptime(t, "%H:%M")


def _add(t: str, hours: float) -> str:
    """Return HH:MM 24h string offset by hours from t."""
    dt = _time_from_str(t) + timedelta(hours=hours)
    return dt.strftime("%H:%M")


def _fmt(t: str) -> str:
    """Format HH:MM 24h string as '4:30 PM' or '1:00 PM'."""
    dt = _time_from_str(t)
    h = dt.hour % 12 or 12
    period = "AM" if dt.hour < 12 else "PM"
    return f"{h}:{dt.minute:02d} {period}"


def _hour(t: str) -> float:
    """Return hour as float (e.g. '19:30' -> 19.5)."""
    dt = _time_from_str(t)
    return dt.hour + dt.minute / 60


_REST_SLOTS = [
    {"slot_name": "breakfast",         "display_label": "Breakfast",                          "eat_by_time": "8:30 AM",  "time_note": "Morning meal",             "tags": ["Complex Carbs", "Protein", "Healthy Fats"],     "icon": "🍳", "is_hydration": False, "is_merged": False, "note": "", "recipe_category": "practice",          "double_day_alert": False},
    {"slot_name": "mid-morning-snack", "display_label": "Mid-Morning Snack",                  "eat_by_time": "11:00 AM", "time_note": "~10-11 AM",                "tags": ["Quick Carbs", "Light"],                         "icon": "🍎", "is_hydration": False, "is_merged": False, "note": "", "recipe_category": "pre-game-snack",    "double_day_alert": False},
    {"slot_name": "lunch",             "display_label": "Lunch",                              "eat_by_time": "1:30 PM",  "time_note": "Midday meal",              "tags": ["High Protein", "Complex Carbs", "Iron-Rich"],   "icon": "🥗", "is_hydration": False, "is_merged": False, "note": "", "recipe_category": "meal-prep",          "double_day_alert": False},
    {"slot_name": "afternoon-snack",   "display_label": "Afternoon Snack",                    "eat_by_time": "4:00 PM",  "time_note": "~2-4 PM",                  "tags": ["Protein", "Healthy Fats"],                      "icon": "🥜", "is_hydration": False, "is_merged": False, "note": "", "recipe_category": "pre-game-snack",    "double_day_alert": False},
    {"slot_name": "dinner",            "display_label": "Dinner",                             "eat_by_time": "7:00 PM",  "time_note": "Evening meal",             "tags": ["High Protein", "Complex Carbs", "Healthy Fats"], "icon": "🍽️", "is_hydration": False, "is_merged": False, "note": "", "recipe_category": "practice",          "double_day_alert": False},
    {"slot_name": "evening-recovery",  "display_label": "Evening Recovery / Pre-Bed Fueling", "eat_by_time": "9:30 PM",  "time_note": "Before bed",               "tags": ["Casein Protein", "Light"],                      "icon": "🌙", "is_hydration": False, "is_merged": False, "note": "", "recipe_category": "post-game-recovery", "double_day_alert": False},
    {"slot_name": "daily-hydration",   "display_label": "Daily Hydration",                    "eat_by_time": "All day",  "time_note": "Water target for the day", "tags": [],                                               "icon": "💧", "is_hydration": True,  "is_merged": False, "note": "", "recipe_category": None,               "double_day_alert": False},
]


def _make_slot(slot_name, display_label, eat_by_time, time_note, tags, icon,
               is_hydration=False, is_merged=False, note="",
               recipe_category=None, double_day_alert=False):
    return {
        "slot_name": slot_name, "display_label": display_label,
        "eat_by_time": eat_by_time, "time_note": time_note,
        "tags": tags, "icon": icon, "is_hydration": is_hydration,
        "is_merged": is_merged, "note": note,
        "recipe_category": recipe_category, "double_day_alert": double_day_alert,
    }


def compute_meal_slots(
    event_type,
    start_time,
    duration_hours,
    double_day=False,
    second_start_time=None,
):
    """
    Return ordered list of meal slot dicts for a given day.
    All slot dicts have keys: slot_name, display_label, eat_by_time, time_note,
    tags, icon, is_hydration, is_merged, note, recipe_category, double_day_alert.
    """
    import copy

    if not event_type or event_type.lower() == "rest":
        return [copy.copy(s) for s in _REST_SLOTS]

    norm = event_type.lower()
    is_game = "game" in norm or "tournament" in norm

    if not start_time:
        return [copy.copy(s) for s in _REST_SLOTS]

    dur = duration_hours or 1.5
    event_end = _add(start_time, dur)

    pre_event_time   = _add(start_time, -3.0)
    power_snack_time = _add(start_time, -0.75)
    halftime_time    = _add(start_time, 0.75)
    recovery_time    = _add(event_end,  0.5)

    is_early_event = _hour(pre_event_time) < 6.0
    is_late_event  = _hour(event_end) >= 19.0

    slots = []

    if double_day:
        slots.append(_make_slot(
            "double-day-alert", "⚡ Double Event Day",
            "", "Two events today — +15% calories",
            [], "⚡", double_day_alert=True,
        ))

    slots.append(_make_slot("breakfast", "Breakfast", "8:30 AM", "Morning meal",
        ["Complex Carbs", "Protein", "Healthy Fats"], "🍳", recipe_category="practice"))
    slots.append(_make_slot("mid-morning-snack", "Mid-Morning Snack", "11:00 AM", "~10-11 AM",
        ["Quick Carbs", "Light"], "🍎", recipe_category="pre-game-snack"))
    slots.append(_make_slot("lunch", "Lunch", "1:30 PM", "Midday meal",
        ["High Protein", "Complex Carbs", "Iron-Rich"], "🥗", recipe_category="meal-prep"))

    if is_early_event:
        slots.append(_make_slot(
            "power-snack", "Power Snack",
            _fmt(power_snack_time),
            f"45 min before {'kick-off' if is_game else 'training'}",
            ["Quick Carbs"], "🍌",
            note="Early event — light snack only before kick-off",
            recipe_category="pre-game-snack",
        ))
    else:
        label    = "Pre-Game Fuel" if is_game else "Pre-Training Fuel"
        note_str = "3 hrs before kick-off" if is_game else "3 hrs before training"
        slots.append(_make_slot(
            "pre-game-fuel" if is_game else "pre-training",
            label, _fmt(pre_event_time), note_str,
            ["Complex Carbs", "Light Protein"], "⚡",
            recipe_category="pre-game",
        ))
        slots.append(_make_slot(
            "power-snack", "Power Snack",
            _fmt(power_snack_time),
            f"45 min before {'kick-off' if is_game else 'training'}",
            ["Quick Carbs"], "🍌",
            recipe_category="pre-game-snack",
        ))

    hydration_label = "During Game Hydration" if is_game else "During Practice Hydration"
    slots.append(_make_slot(
        "during-game-hydration" if is_game else "during-practice-hydration",
        hydration_label,
        f"{_fmt(start_time)} – {_fmt(event_end)}",
        "Electrolytes + fluids",
        ["Electrolytes", "Fluids"], "💦",
        is_hydration=True,
    ))

    if is_game:
        slots.append(_make_slot(
            "halftime-fueling", "Halftime Fueling",
            _fmt(halftime_time), "At halftime",
            ["Quick Carbs", "Light"], "🍊",
            recipe_category="halftime",
        ))

    if is_late_event:
        slots.append(_make_slot(
            "recovery-dinner", "Recovery Dinner",
            f"After {_fmt(event_end)}",
            "Post-event dinner = recovery meal",
            ["High Protein", "Complex Carbs", "Fast Carbs"], "🍽️🔋",
            is_merged=True,
            note="Post-event dinner doubles as your recovery meal tonight",
            recipe_category="post-game-recovery",
        ))
    else:
        slots.append(_make_slot(
            "recovery-fuel", "Recovery Fuel",
            _fmt(recovery_time), "Within 30 min after event",
            ["Protein", "Fast Carbs"], "🔋",
            recipe_category="post-game-recovery",
        ))
        slots.append(_make_slot(
            "dinner", "Dinner", "7:00 PM", "Evening meal",
            ["High Protein", "Complex Carbs", "Healthy Fats"], "🍽️",
            recipe_category="practice",
        ))
        slots.append(_make_slot(
            "night-fuel", "Night Fuel", "9:00 PM", "Before bed",
            ["Casein Protein", "Light"], "🌙",
            recipe_category="post-game-recovery",
        ))

    if double_day and second_start_time:
        between_time = f"After {_fmt(event_end)} – Before {_fmt(second_start_time)}"
        slots.append(_make_slot(
            "between-games", "Between Games Recovery + Refuel",
            between_time, "Recovery window between games",
            ["Protein", "Fast Carbs", "Electrolytes"], "🔄",
            is_merged=True,
            recipe_category="post-game-recovery",
        ))

    slots.append(_make_slot(
        "daily-hydration", "Daily Hydration", "All day",
        "Water target for the day", [], "💧",
        is_hydration=True,
    ))

    return slots
