"""
Window Distribution & CHO:Protein Ratios
========================================
Distributes the daily macro totals (from nutrition_calc.calculate_daily_targets)
across the named fueling windows, with per-window CHO:PRO ratio validation,
protein caps/floors, and an auto-boost that protects the Fuel Before ratio.

Source: Purvi (sports RDN) window-distribution spec, built on IOC/AAP/ACSM
nutrient-timing guidance. Per-window percentages are of the DAILY total.

Window taxonomy note: these 6 windows are a macro-distribution scheme and are
NOT the same set the timing engine (window_engine_v2.py) generates. Mapping the
two is a separate integration decision — see module owner.
"""

from typing import Optional

# Per-window share of the DAILY total (cho / prot / hyd) plus per-window rules.
# Insertion order matters: everyday_meal MUST come before fuel_before so the
# fuel_before auto-boost can pull CHO from an already-computed everyday_meal.
SPLITS = {
    "everyday_meal": {
        "cho": 0.25, "prot": 0.20, "hyd": 0.20,
        "mps": True, "fat_foods": True,
    },
    "fuel_before": {
        "cho": 0.25, "prot": 0.15, "hyd": 0.20,
        "mps": True, "prot_cap_g_per_kg": 0.30,   # GI + nausea risk cap for teens
    },
    "top_up": {
        "cho": 0.15, "prot": 0.05, "hyd": 0.15,
        "mps": False, "prot_hard_cap_g": 10, "cho_floor_g_per_kg": 0.50,
        "gi_filter": "fast_only",                 # not an MPS window
    },
    "keep_going": {
        "cho": 0.08, "prot": 0.00, "hyd": 0.12,
        "mps": False, "per_hour": True, "liquid_only": True,   # additive per hour >60min
    },
    "recharge": {
        "cho": 0.20, "prot": 0.30, "hyd": 0.20,
        "mps": True, "prot_floor_g_per_kg": 0.30, "gi_filter": "fast",  # PRIMARY MPS window
    },
    "rebuild": {
        "cho": 0.15, "prot": 0.30, "hyd": 0.13,
        "mps": True, "prot_floor_g_per_kg": 0.30, "fat_reintroduced": True,
    },
}

# Minimum acceptable CHO:PRO ratio per window. Below this → RATIO_LOW flag.
RATIO_FLOOR = {
    "fuel_before": 3.0, "top_up": 5.0,
    "recharge": 3.0, "rebuild": 1.5, "everyday_meal": 2.0,
}

# S&C-day protein floor for the primary MPS (recharge) window — upper of range.
_SC_RECHARGE_PROT_G_PER_KG = 0.38


def validate_windows(wt_kg: float, daily_cho_g: int, daily_prot_g: int,
                     is_sc_day: bool = False) -> dict:
    """Per-window gram targets + CHO:PRO ratio validation.

    Applies protein caps/floors and CHO floors per window, then computes the
    ratio against RATIO_FLOOR. Fuel Before is auto-boosted (CHO pulled from
    Everyday Meal) when its ratio would fall below 3.0. On S&C days the recharge
    protein floor shifts to the upper range (0.38 g/kg).

    keep_going is intentionally excluded — it's per-hour and conditional on
    session length; use keep_going_window() for it.
    """
    results = {}
    for win, s in SPLITS.items():
        if win == "keep_going":
            continue  # handled by keep_going_window()

        cho_g  = round(daily_cho_g  * s["cho"])
        prot_g = round(daily_prot_g * s["prot"])

        # ── Caps and floors ──────────────────────────────────────────────────
        if win == "fuel_before":
            prot_g = min(prot_g, round(s["prot_cap_g_per_kg"] * wt_kg))
        if win == "top_up":
            cho_g  = max(cho_g,  round(s["cho_floor_g_per_kg"] * wt_kg))
            prot_g = min(prot_g, s["prot_hard_cap_g"])
        if win == "recharge":
            floor  = (_SC_RECHARGE_PROT_G_PER_KG * wt_kg) if is_sc_day \
                     else s["prot_floor_g_per_kg"] * wt_kg
            prot_g = max(prot_g, round(floor))
        if win == "rebuild":
            prot_g = max(prot_g, round(s["prot_floor_g_per_kg"] * wt_kg))

        ratio = round(cho_g / prot_g, 2) if prot_g > 0 else 0
        floor = RATIO_FLOOR.get(win, 0)
        flag  = f"RATIO_LOW: {ratio}:1" if ratio < floor else None

        # ── Auto-boost Fuel Before from Everyday Meal if ratio too low ───────
        if win == "fuel_before" and flag:
            target_cho = round(prot_g * 3.0)
            delta      = target_cho - cho_g
            results["everyday_meal"]["cho_g"] -= delta
            cho_g  += delta
            ratio   = round(cho_g / prot_g, 2) if prot_g > 0 else 0
            flag    = f"RATIO_ADJUSTED to {ratio}:1"

        results[win] = {"cho_g": cho_g, "prot_g": prot_g, "ratio": ratio, "flag": flag}

    return results


def keep_going_window(wt_kg: float, duration_min: float) -> Optional[dict]:
    """Mid-session fuel for sessions > 75 min. Returns None for shorter sessions.

    CHO is liquid/fast only and expressed to the athlete as oz / packets —
    never grams (this is not an MPS window and grams confuse mid-session fueling).
    """
    if duration_min <= 75:
        return None

    extra_hrs    = min((duration_min - 60) / 60, 2.0)
    cho_per_hr   = max(30, min(60, round(0.5 * wt_kg)))
    total_cho    = round(cho_per_hr * extra_hrs)
    extra_blocks = int((duration_min - 60) / 30)

    # Athlete-facing units — never grams
    sports_drink_oz = round(total_cho / 6 * 8)   # ~6 g CHO per 8 oz sports drink
    packets         = round(total_cho / 17)       # ~17 g CHO per applesauce/honey pkt

    return {
        "card":          "keep_going",
        "cho_g":         total_cho,
        "prot_g":        0,
        "fat_g":         0,
        "extra_hyd_oz":  extra_blocks * 12,
        "notify_at_min": 60,
        "athlete_label": (
            f"Grab a sports drink ({sports_drink_oz} oz) "
            f"or {packets} applesauce/honey packet(s). "
            f"No chewing needed — just quick fuel."
        ),
        "color":       "#1565C0",
        "liquid_only": True,
    }


# ── Engine-slot → SPLITS-key mapping ──────────────────────────────────────────
# Maps the variable slot taxonomies produced by meal_timing.compute_meal_slots
# (hyphen keys) and window_engine_v2 (underscore keys) onto Purvi's 6 windows.
# None = no macro split (hydration-only slots, or unknown — caller skips).
# night-fuel / evening-recovery → rebuild is the v1 default (open decision #2).
SLOT_TO_SPLIT = {
    # ── compute_meal_slots hyphen taxonomy (LIVE Today Mission) ───────────────
    "breakfast":                  "everyday_meal",
    "mid-morning-snack":          "everyday_meal",
    "lunch":                      "everyday_meal",
    "afternoon-snack":            "everyday_meal",
    "dinner":                     "everyday_meal",
    "pre-game-fuel":              "fuel_before",
    "pre-training":               "fuel_before",
    "power-snack":                "top_up",
    "halftime-fueling":           "keep_going",
    "recovery-fuel":              "recharge",
    "recovery-dinner":            "rebuild",
    "night-fuel":                 "rebuild",        # bedtime casein — v1 default
    "evening-recovery":           "rebuild",        # bedtime casein — v1 default
    "between-games":              "recharge",
    # hydration-only — no macro split
    "during-game-hydration":      None,
    "during-practice-hydration":  None,
    "daily-hydration":            None,
    # ── window_engine_v2 underscore taxonomy (forward-compat) ─────────────────
    "everyday_breakfast":         "everyday_meal",
    "everyday_lunch":             "everyday_meal",
    "everyday_snack":             "everyday_meal",
    "everyday_dinner":            "everyday_meal",
    "pre_event_meal":             "fuel_before",
    "top_up_snack":               "top_up",
    "quick_morning_snack":        "top_up",
    "fuel_during":                "keep_going",
    "fuel_after_primary":         "recharge",
    "fuel_after_second":          "rebuild",
    "proper_breakfast_after":     "rebuild",
}

# Tournament/double-day variants carry an event-index suffix (e.g.
# "fuel_after_primary_1", "between_games_1_2"). Match by prefix after exact miss.
# NOTE: entries duplicating an exact SLOT_TO_SPLIT key only ever fire for suffixed
# variants (exact names are caught above); keep their values in sync with SLOT_TO_SPLIT.
_SLOT_PREFIX_TO_SPLIT = {
    "pre_event_meal":          "fuel_before",
    "top_up_snack":            "top_up",
    "quick_morning_snack":     "top_up",
    "fuel_during":             "keep_going",
    "fuel_after_primary":      "recharge",
    "fuel_after_second":       "rebuild",
    "proper_breakfast_after":  "rebuild",
    "between_games":           "recharge",
    "refuel_ready":            "recharge",
}


def split_key_for_slot(slot_name: str) -> Optional[str]:
    """Return the SPLITS key for an engine slot_name, or None if it has no
    macro split (hydration-only or unknown). Exact match first, then prefix
    match for event-index-suffixed v2 keys."""
    if slot_name in SLOT_TO_SPLIT:
        return SLOT_TO_SPLIT[slot_name]
    for prefix, key in _SLOT_PREFIX_TO_SPLIT.items():
        if slot_name.startswith(prefix):
            return key
    return None


def on_fueled_press(window_key: str, current: dict, daily: dict,
                    wt_kg: float, duration_min: float, is_sc_day: bool) -> dict:
    """Reference handler for the mobile "Fueled" button.

    Pure function: takes the current logged state + daily totals, returns the
    updated state with refreshed macro-bar percentages. The actual button press
    happens client-side; this is the canonical implementation the app mirrors.
    """
    windows = validate_windows(wt_kg, daily["cho_g"], daily["prot_g"], is_sc_day)

    if window_key == "keep_going":
        kg_win = keep_going_window(wt_kg, duration_min)
        if not kg_win:
            return current
        add = {"cho_g": kg_win["cho_g"], "prot_g": 0, "hyd_oz": kg_win["extra_hyd_oz"]}
    else:
        w   = windows[window_key]
        hyd = round(daily["hyd_oz"] * SPLITS[window_key]["hyd"])
        add = {"cho_g": w["cho_g"], "prot_g": w["prot_g"], "hyd_oz": hyd}

    updated = {
        "cho_g":  current["cho_g"]  + add["cho_g"],
        "prot_g": current["prot_g"] + add["prot_g"],
        "hyd_oz": current["hyd_oz"] + add["hyd_oz"],
        "fueled": [*current["fueled"], window_key],
    }
    updated["pct"] = {
        "cho":  min(100, round(updated["cho_g"]  / daily["cho_g"]  * 100)) if daily["cho_g"]  else 0,
        "prot": min(100, round(updated["prot_g"] / daily["prot_g"] * 100)) if daily["prot_g"] else 0,
        "hyd":  min(100, round(updated["hyd_oz"] / daily["hyd_oz"] * 100)) if daily["hyd_oz"]  else 0,
    }
    return updated
