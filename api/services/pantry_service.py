# api/services/pantry_service.py
import re

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

# Both allergies and dietary_restrictions are free text ("Red meat", "Egg-Free",
# "lactose intolerant", "wheat"). Recognized keywords map onto allergen exclusions
# and diet_tags; unrecognized text is left for the AI prompt to honor softly —
# a hard filter must never zero out the whole database.
_DIET_TAG_KEYWORDS = [
    ("vegan", "vegan"),
    ("vegetarian", "vegetarian"),
    ("gluten", "gluten_free"),
    ("celiac", "gluten_free"),
    ("wheat", "gluten_free"),
    ("dairy", "dairy_free"),
    ("lactose", "dairy_free"),
]
_ALLERGEN_KEYWORDS = [
    ("shellfish", "shellfish"),
    ("fish", "fish"),
    ("peanut", "peanuts"),
    ("nut", "tree_nuts"),
    ("nut", "peanuts"),
    ("egg", "eggs"),
    ("soy", "soy"),
    ("sesame", "sesame"),
    ("dairy", "dairy"),
    ("milk", "dairy"),
    ("lactose", "dairy"),
    ("wheat", "gluten"),
    ("gluten", "gluten"),
]
_ALLERGEN_KEYS = {a for f in FOOD_DATABASE for a in f.get("allergens", [])}


def _keyword_matches(text: str, pairs: list[tuple[str, str]]) -> set[str]:
    # \b so "shellfish" doesn't trigger "fish" and "peanut" doesn't trigger "nut"
    return {v for kw, v in pairs if re.search(rf"\b{kw}", text)}


def safe_foods_for_athlete(athlete: dict) -> list[dict]:
    """Return FOOD_DATABASE entries that pass allergen + dietary filter for this athlete."""
    avoid_allergens: set[str] = set()

    raw_allergies = (athlete.get("allergies") or "").lower()
    for tok in raw_allergies.split(","):
        tok = tok.strip()
        if not tok or tok in _NO_VALUE:
            continue
        if tok in _ALLERGEN_KEYS:
            avoid_allergens.add(tok)
        else:
            avoid_allergens |= _keyword_matches(tok, _ALLERGEN_KEYWORDS)

    required_tags: set[str] = set()
    raw_diet = (athlete.get("dietary_restrictions") or "").lower().strip()
    if raw_diet not in _NO_VALUE:
        required_tags = _keyword_matches(raw_diet, _DIET_TAG_KEYWORDS)
        avoid_allergens |= _keyword_matches(raw_diet, _ALLERGEN_KEYWORDS)

    return [
        f for f in FOOD_DATABASE
        if not (avoid_allergens & set(f.get("allergens", [])))
        and required_tags <= set(f.get("diet_tags", []))
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


def _strip_paren(name: str) -> str:
    """Normalize a food name for dislike matching — mirrors the mobile's exclude
    normalization (item.name.split('(')[0].trim()) so 'Tuna (5 oz can)' matches 'Tuna'."""
    return (name or "").split("(")[0].strip()


def get_pantry_list(athlete_id: int, week_start: str, conn) -> list[dict]:
    rows = conn.execute(
        """SELECT id, food_id, name, cue_label, purchase_unit, role, meal_context, must_have, checked
           FROM pantry_list_items
           WHERE athlete_id = ? AND week_start = ?
           ORDER BY must_have DESC, meal_context, name""",
        (athlete_id, week_start),
    ).fetchall()
    # Defense in depth: never surface a disliked/allergen food, even if a stored row
    # lingers. Matches the food_name filter used by generate/regenerate, but normalized
    # on BOTH sides so parenthetical unit suffixes don't defeat the match.
    disliked = {
        _strip_paren(r["food_name"])
        for r in conn.execute(
            "SELECT food_name FROM athlete_food_prefs WHERE athlete_id = ? AND preference = 'disliked'",
            (athlete_id,),
        ).fetchall()
    }
    return [dict(r) for r in rows if _strip_paren(r["name"]) not in disliked]


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
