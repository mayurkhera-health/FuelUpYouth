# api/services/pantry_service.py
from api.services.food_db import FOOD_DATABASE, get_food_by_id

MEAL_CONTEXT_ORDER = [
    "must_haves",  # synthetic — items where must_have=True
    "breakfast_foundations",
    "lunch_dinner_builders",
    "pre_training_fuel",
    "post_training_recovery",
    "snacks_everyday",
    "hydration",
]

MEAL_CONTEXT_LABELS = {
    "must_haves":            "Must-haves this week",
    "breakfast_foundations": "Breakfast foundations",
    "lunch_dinner_builders": "Lunch & dinner builders",
    "pre_training_fuel":     "Pre-training fuel",
    "post_training_recovery":"Post-training recovery",
    "snacks_everyday":       "Snacks & everyday",
    "hydration":             "Hydration",
}


def cue_label_for(food: dict) -> str:
    role = food.get("role", "")
    if role == "protein":   return "High protein"
    if role == "fat":       return "Healthy fat"
    if role == "produce":   return "Micronutrients"
    if role == "hydration": return "Hydration"
    return "Fast energy" if food.get("gi_tier") == "fast" else "Sustained energy"


_NO_VALUE = {"", "none", "n/a", "na", "no", "not specified"}

def safe_foods_for_athlete(athlete: dict) -> list[dict]:
    """Return FOOD_DATABASE entries that pass allergen + dietary filter for this athlete."""
    raw_allergies = athlete.get("allergies") or ""
    allergies = [
        a.lower().strip() for a in raw_allergies.split(",")
        if a.strip() and a.lower().strip() not in _NO_VALUE
    ]
    raw_diet = (athlete.get("dietary_restrictions") or "").lower().strip()
    diet = "omnivore" if raw_diet in _NO_VALUE else raw_diet

    return [
        f for f in FOOD_DATABASE
        if not any(a in f.get("allergens", []) for a in allergies)
        and (diet == "omnivore" or diet in f.get("diet_tags", []))
    ]


def build_pantry_items(
    athlete_id: int, week_start: str, food_item_map: dict, conn
) -> list[dict]:
    """
    Clear previous pantry for this athlete+week, insert new items, return them.
    food_item_map: {food_id: {meal_context: str, must_have: bool}}
    Skips any food_id not found in FOOD_DATABASE.
    """
    conn.execute(
        "DELETE FROM pantry_list_items WHERE athlete_id = ? AND week_start = ?",
        (athlete_id, week_start),
    )
    items = []
    for fid, meta in food_item_map.items():
        food = get_food_by_id(fid)
        if food is None:
            continue
        cue = cue_label_for(food)
        meal_context = meta.get("meal_context", "snacks_everyday")
        must_have = 1 if meta.get("must_have") else 0
        conn.execute(
            """INSERT OR IGNORE INTO pantry_list_items
               (athlete_id, week_start, food_id, name, cue_label, purchase_unit, role, meal_context, must_have)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (athlete_id, week_start, food["food_id"], food["name"],
             cue, food["purchase_unit"], food["role"], meal_context, must_have),
        )
        items.append({
            "id":            None,
            "food_id":       food["food_id"],
            "name":          food["name"],
            "cue_label":     cue,
            "purchase_unit": food["purchase_unit"],
            "role":          food["role"],
            "meal_context":  meal_context,
            "must_have":     bool(must_have),
            "checked":       False,
        })
    conn.commit()

    # Re-fetch to get real DB ids
    rows = conn.execute(
        """SELECT id, food_id, name, cue_label, purchase_unit, role, meal_context, must_have, checked
           FROM pantry_list_items
           WHERE athlete_id = ? AND week_start = ?
           ORDER BY must_have DESC, meal_context, name""",
        (athlete_id, week_start),
    ).fetchall()
    return [dict(r) for r in rows]


def get_pantry_list(athlete_id: int, week_start: str, conn) -> list[dict]:
    rows = conn.execute(
        """SELECT id, food_id, name, cue_label, purchase_unit, role, meal_context, must_have, checked
           FROM pantry_list_items
           WHERE athlete_id = ? AND week_start = ?
           ORDER BY must_have DESC, meal_context, name""",
        (athlete_id, week_start),
    ).fetchall()
    return [dict(r) for r in rows]


def group_pantry_items(items: list[dict]) -> list[dict]:
    """Group items by meal_context. must_have items appear first in their own group."""
    must_haves = [i for i in items if i.get("must_have")]
    non_must = [i for i in items if not i.get("must_have")]

    by_ctx: dict[str, list] = {k: [] for k in MEAL_CONTEXT_ORDER}
    if must_haves:
        by_ctx["must_haves"] = must_haves

    for item in non_must:
        ctx = item.get("meal_context") or "snacks_everyday"
        by_ctx.setdefault(ctx, []).append(item)

    return [
        {
            "role":  ctx,   # keep "role" key for API compat — frontend reads this
            "label": MEAL_CONTEXT_LABELS.get(ctx, ctx.replace("_", " ").title()),
            "items": by_ctx[ctx],
        }
        for ctx in MEAL_CONTEXT_ORDER
        if by_ctx.get(ctx)
    ]
