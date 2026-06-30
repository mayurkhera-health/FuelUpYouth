"""Deterministic 'nutritional plan' for Weekly Prep. Decides HOW MANY foods of each
kind the week needs, scaled to schedule + targets. No LLM — pure, testable rules.
The AI layer (claude_ai.prompt8_pantry_plan) fills these slots; fallback_select fills
them deterministically when the AI fails."""

_INTENSE = {"game", "tournament"}
_ACTIVE = {"game", "tournament", "practice", "training", "strength"}


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def summarize_week(week_schedule, targets_by_day):
    game = sum(1 for d in week_schedule if d.get("event_type") == "game")
    tourn = sum(1 for d in week_schedule if d.get("event_type") == "tournament")
    practice = sum(1 for d in week_schedule if d.get("event_type") in {"practice", "training", "strength"})
    rest = sum(1 for d in week_schedule if d.get("event_type") == "rest")
    n = max(1, len(targets_by_day))
    return {
        "game_days": game,
        "tournament_days": tourn,
        "practice_days": practice,
        "rest_days": rest,
        "avg_carbs_g": round(sum(t.get("carbs_g", 0) for t in targets_by_day) / n),
        "avg_protein_g": round(sum(t.get("protein_g", 0) for t in targets_by_day) / n),
        "avg_hydration_oz": round(sum(t.get("hydration_oz", 0) for t in targets_by_day) / n),
        "iron_emphasis": any(t.get("iron_flag") for t in targets_by_day),
    }


def compute_slot_plan(week_schedule, targets_by_day, athlete):
    s = summarize_week(week_schedule, targets_by_day)
    intense = s["game_days"] + s["tournament_days"]
    active = s["practice_days"] + intense
    c_pre = _clamp(2 + intense, 2, 5)
    c_post = _clamp(2 + intense, 2, 5)
    c_hyd = 2 if intense >= 1 else 1
    hyd_must = intense >= 1
    if active <= 1:                      # rest-heavy week → minimum everyday list
        c_pre, c_post, c_hyd, hyd_must = 2, 2, 1, False
    iron = s["iron_emphasis"]
    slots = [
        {"meal_context": "breakfast_foundations", "count": 2, "roles": ["carb", "protein"], "must_have": False},
        {"meal_context": "lunch_dinner_builders", "count": 3, "roles": ["protein", "carb", "produce"], "must_have": True, "iron_priority": iron},
        {"meal_context": "pre_training_fuel", "count": c_pre, "roles": ["carb"], "gi_tier": "fast", "must_have": True},
        {"meal_context": "post_training_recovery", "count": c_post, "roles": ["protein"], "must_have": True, "iron_priority": iron},
        {"meal_context": "snacks_everyday", "count": 3, "roles": ["carb", "fat", "produce"], "must_have": False},
        {"meal_context": "hydration", "count": c_hyd, "roles": ["hydration"], "must_have": hyd_must},
    ]
    return {"week_summary": s, "slots": slots}


def fallback_select(slot_plan, safe_foods, athlete):
    """Deterministically fill each slot's count from safe_foods. Returns the same
    item shape the AI returns: [{food_id, meal_context, must_have}]. Never duplicates."""
    chosen = set()
    items = []
    for slot in slot_plan["slots"]:
        roles = set(slot.get("roles", []))
        gi = slot.get("gi_tier")
        cands = [
            f for f in safe_foods
            if f["food_id"] not in chosen
            and f.get("role") in roles
            and (gi is None or f.get("gi_tier") == gi)
        ]
        if slot.get("iron_priority"):
            cands.sort(key=lambda f: f.get("iron_mg", 0), reverse=True)
        else:
            cands.sort(key=lambda f: (f.get("role", ""), f.get("name", "")))
        for f in cands[: slot.get("count", 0)]:
            chosen.add(f["food_id"])
            items.append({
                "food_id": f["food_id"],
                "meal_context": slot["meal_context"],
                "must_have": bool(slot.get("must_have", False)),
            })
    return items


def fallback_replacement(role, gi_tier, safe_foods, current_food_ids):
    """Pick one safe food of the same role (and gi_tier if given) not already listed."""
    for f in safe_foods:
        if (f["food_id"] not in current_food_ids
                and f.get("role") == role
                and (gi_tier is None or f.get("gi_tier") == gi_tier)):
            return f["food_id"]
    return None
