"""
Shopping / Fueling Essentials service.

Key invariant: schedule classification MUST use determine_day_type() from
window_templates — the single source of truth for event → day-type mapping.
"""
from datetime import date, timedelta
from api.services.window_templates import determine_day_type

# ── Category metadata ─────────────────────────────────────────────────────────

CATEGORY_LABELS: dict[str, str] = {
    "breakfast":     "Breakfast",
    "pre_fuel":      "Pre-Practice & Game Fuel",
    "recovery":      "Recovery",
    "hydration":     "Hydration",
    "dinner_staple": "Dinner Staples",
}

CATEGORY_ORDER = ["breakfast", "pre_fuel", "recovery", "hydration", "dinner_staple"]

_GAME_DAY_TYPES = frozenset({
    "morning_game", "afternoon_game", "evening_event", "early_game", "tournament"
})
_PRACTICE_DAY_TYPES = frozenset({
    "practice_morning", "practice_evening", "double_training"
})


# ── Week classification ───────────────────────────────────────────────────────

def classify_week(events_by_day: dict) -> dict:
    """
    events_by_day: {date_str: [event_dict, ...]} for each of the 7 days.
    Returns a classification dict with counts, flags, and header line.
    """
    practice_count = 0
    game_count = 0
    day_types: list[str] = []

    for date_str, events in events_by_day.items():
        dt = determine_day_type(events, date_str)
        day_types.append(dt)
        if dt in _GAME_DAY_TYPES:
            game_count += 1
        elif dt in _PRACTICE_DAY_TYPES:
            practice_count += 1

    has_game = game_count > 0
    has_any_event = practice_count > 0 or has_game

    parts = []
    if practice_count:
        parts.append(f"{practice_count} practice{'s' if practice_count != 1 else ''}")
    if game_count:
        parts.append(f"{game_count} game{'s' if game_count != 1 else ''}")
    schedule_line = (
        f"{' + '.join(parts)} this week" if parts else "Rest week"
    )

    return {
        "practice_count": practice_count,
        "game_count":     game_count,
        "has_game":       has_game,
        "has_any_event":  has_any_event,
        "day_types":      day_types,
        "schedule_line":  schedule_line,
    }


# ── Active category set ───────────────────────────────────────────────────────

def _active_categories(classification: dict) -> list[str]:
    cats = ["breakfast", "dinner_staple"]
    if classification["has_any_event"]:
        cats.insert(1, "pre_fuel")
        cats.append("recovery")
    if classification["has_game"]:
        cats.append("hydration")
    return cats


# ── Week event fetch ──────────────────────────────────────────────────────────

def fetch_week_events(athlete_id: int, week_start: str, conn) -> dict:
    """Return {date_str: [event_dict, ...]} for the 7 days starting week_start."""
    monday = date.fromisoformat(week_start)
    result: dict = {}
    for i in range(7):
        day = (monday + timedelta(days=i)).isoformat()
        rows = conn.execute(
            "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time",
            (athlete_id, day),
        ).fetchall()
        result[day] = [dict(r) for r in rows]
    return result


# ── Essentials generation ─────────────────────────────────────────────────────

def build_essentials(athlete_id: int, week_start: str, conn) -> dict:
    """
    Main entry point for GET /api/shopping/essentials.
    Returns header + grouped food suggestions, filtered by athlete prefs.
    """
    events_by_day = fetch_week_events(athlete_id, week_start, conn)
    classification = classify_week(events_by_day)
    active_cats = _active_categories(classification)

    # Load athlete preferences
    pref_rows = conn.execute(
        "SELECT food_name, preference, category FROM athlete_food_prefs WHERE athlete_id = ?",
        (athlete_id,),
    ).fetchall()
    excluded = {r["food_name"] for r in pref_rows if r["preference"] in ("disliked", "allergic")}
    liked = [
        {
            "name":          r["food_name"],
            "category":      r["category"],
            "soft_hint":     "",
            "allergen_tags": [],
            "source":        "personal",
        }
        for r in pref_rows
        if r["preference"] == "liked"
    ]

    groups = []
    for cat in CATEGORY_ORDER:
        if cat not in active_cats:
            continue
        foods_rows = conn.execute(
            "SELECT id, name, soft_hint, allergen_tags FROM fueling_foods "
            "WHERE category = ? AND is_active = 1",
            (cat,),
        ).fetchall()

        foods = []
        for r in foods_rows:
            if r["name"] in excluded:
                continue
            foods.append({
                "id":            r["id"],
                "name":          r["name"],
                "soft_hint":     r["soft_hint"] or "",
                "allergen_tags": [t for t in (r["allergen_tags"] or "").split(";") if t],
                "source":        "catalog",
            })

        # Append personal liked foods in this category
        for lf in liked:
            if lf["category"] == cat and lf["name"] not in excluded:
                foods.append(lf)

        groups.append({
            "category": cat,
            "label":    CATEGORY_LABELS[cat],
            "foods":    foods,
        })

    return {
        "week_start": week_start,
        "header": {
            "schedule_line":  classification["schedule_line"],
            "practice_count": classification["practice_count"],
            "game_count":     classification["game_count"],
            "has_game":       classification["has_game"],
        },
        "groups": groups,
    }


# ── Share text generation ─────────────────────────────────────────────────────

def build_share_text(week_start: str, items: list) -> str:
    """Produce plain-text Shopping List for clipboard / share sheet."""
    try:
        monday = date.fromisoformat(week_start)
        header_date = monday.strftime("%-d %b")
    except Exception:
        header_date = week_start

    lines = [f"Fueling2Win Shopping List — Week of {header_date}", ""]

    by_cat: dict = {c: [] for c in CATEGORY_ORDER}
    for item in items:
        cat = item.get("category", "dinner_staple")
        by_cat.setdefault(cat, []).append(item)

    for cat in CATEGORY_ORDER:
        cat_items = by_cat.get(cat, [])
        if not cat_items:
            continue
        lines.append(CATEGORY_LABELS.get(cat, cat.replace("_", " ").title()))
        for item in cat_items:
            checkbox = "☑" if item.get("checked") else "☐"
            lines.append(f"{checkbox} {item['name']}")
        lines.append("")

    return "\n".join(lines).strip()
