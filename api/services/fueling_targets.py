"""
fueling_targets.py — Fuel Gauge coefficient & config module.

SINGLE SOURCE OF TRUTH for every tunable number in the Fuel Gauge feature.
When the dietitian supplies real values, THIS is the only file that changes —
no migrations, no engine edits, no redeploy risk beyond this module.

──────────────────────────────────────────────────────────────────────────
CLINICAL GATE
──────────────────────────────────────────────────────────────────────────
Every value tagged ``PENDING_CLINICAL`` is a STRUCTURAL PLACEHOLDER, not a
clinically approved number. Do NOT enable ``FUEL_GAUGE_ENABLED`` for athletes
until the dietitian signs off on both (a) the values here and (b) numeric
display to minors. (design doc §0 clinical gate)

──────────────────────────────────────────────────────────────────────────
ARCHITECTURE (Phase 0 decision D1) — this module does NOT do macro math
──────────────────────────────────────────────────────────────────────────
Protein / carb / calcium / fluid BASELINES come from Blueprint's
``nutrition_calc.calc_daily_targets()`` so that Today and Blueprint can never
disagree on the same athlete (the T6/T7 credibility guarantee — holds on rest
AND event days). This module only holds the *deltas and structure* layered on
top of that baseline:

  • season-phase modifiers          → multipliers on the Blueprint baseline
  • fluid + sodium weather model    → coefficients applied to calc_sweat_output()
                                       (weather.py) — the sweat model is REUSED,
                                       never reinvented here
  • per-category window-split table → how a daily target is shared across windows
  • unit policy + range-reduction   → how Blueprint's min/max band collapses to
                                       one gauge number

The assembly logic (which baseline, how to combine) lives in the engine module
(compute_event_day_targets / compute_rest_day_targets / split_targets_across_windows);
this file is data + trivial pure helpers ONLY.
"""

from __future__ import annotations

import os
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────
# Feature flag — gates the entire fuel_targets payload block.
# When OFF, the Today payload must be byte-identical to current production.
# ──────────────────────────────────────────────────────────────────────────
def fuel_gauge_enabled() -> bool:
    return os.environ.get("FUEL_GAUGE_ENABLED", "false").lower() == "true"


# ──────────────────────────────────────────────────────────────────────────
# Canonical metrics. These five keys are the gauge contract end to end
# (payload, split table, frontend). Order is display order.
#   protein_g   — grams
#   carbs_g     — grams
#   fluids_ml   — millilitres   (D3: ml internally; oz only at US display)
#   sodium_mg   — milligrams
#   calcium_mg  — milligrams
# ──────────────────────────────────────────────────────────────────────────
NUTRIENT_KEYS: tuple[str, ...] = (
    "protein_g",
    "carbs_g",
    "fluids_ml",
    "sodium_mg",
    "calcium_mg",
)

# Unit conversion. Blueprint hydration & calc_sweat_output are in US fluid oz;
# we canonicalise to ml internally and convert back only for display.
OZ_TO_ML: float = 29.5735


# ──────────────────────────────────────────────────────────────────────────
# D2 — Blueprint returns macro BANDS (min/max). The gauge needs one number.
# Policy is centralised here so the dietitian flips one switch.
# PENDING_CLINICAL — founder default = "midpoint".  Options: "min"|"midpoint"|"max".
# ──────────────────────────────────────────────────────────────────────────
MACRO_RANGE_REDUCER: str = "midpoint"  # PENDING_CLINICAL


def reduce_range(lo: Optional[float], hi: Optional[float]) -> Optional[float]:
    """Collapse a Blueprint min/max band to a single working target per policy."""
    if lo is None or hi is None:
        return None
    if MACRO_RANGE_REDUCER == "min":
        return float(lo)
    if MACRO_RANGE_REDUCER == "max":
        return float(hi)
    return (float(lo) + float(hi)) / 2.0  # midpoint (default)


# ──────────────────────────────────────────────────────────────────────────
# Season phase (new athlete-profile field). Modifiers multiply the Blueprint
# baseline — they do NOT recompute macros (D1). in_season == 1.0 because the
# Blueprint baseline is already an in-season number.
# ──────────────────────────────────────────────────────────────────────────
VALID_SEASON_PHASES: tuple[str, ...] = ("in_season", "off_season", "postseason")
DEFAULT_SEASON_PHASE: str = "in_season"


def normalize_season_phase(value: Optional[str]) -> str:
    v = (value or "").strip().lower()
    return v if v in VALID_SEASON_PHASES else DEFAULT_SEASON_PHASE


# PENDING_CLINICAL — placeholder multipliers. Shapes only, per design §2.4:
#   off_season  → building: protein up, carbs down (no games)
#   postseason  → recovery: protein near-maintenance, carbs down
SEASON_PHASE_PROTEIN_MULT: dict[str, float] = {
    "in_season": 1.00,
    "off_season": 1.10,   # PENDING_CLINICAL
    "postseason": 0.95,   # PENDING_CLINICAL
}
SEASON_PHASE_CARB_MULT: dict[str, float] = {
    "in_season": 1.00,
    "off_season": 0.90,   # PENDING_CLINICAL
    "postseason": 0.85,   # PENDING_CLINICAL
}
# Fluids, sodium and calcium are not season-phase driven (PENDING_CLINICAL).
# Kept as explicit 1.0 tables so the dietitian has one obvious place to change it.
SEASON_PHASE_FLUID_MULT: dict[str, float] = {p: 1.00 for p in VALID_SEASON_PHASES}
SEASON_PHASE_SODIUM_MULT: dict[str, float] = {p: 1.00 for p in VALID_SEASON_PHASES}


# ──────────────────────────────────────────────────────────────────────────
# Training load (event day). We do NOT invent a load→macro formula; instead we
# pick the day's dominant event_type and feed it (with intensity) to Blueprint's
# calc_daily_targets(). This rank only decides which event "wins" on multi-event
# days, so load aggregates without double-counting (T1 boundary tests).
# game/tournament > practice/strength/training > conditioning > rest
# ──────────────────────────────────────────────────────────────────────────
EVENT_TYPE_LOAD_RANK: dict[str, int] = {
    "tournament": 5,
    "game": 4,
    "strength": 3,
    "practice": 3,
    "training": 3,
    "conditioning": 2,
    "rest": 0,
}
REST_EVENT_TYPE: str = "rest"

# If an event has no explicit intensity, fall back by competition level.
# PENDING_CLINICAL — placeholder mapping.
DEFAULT_INTENSITY_BY_LEVEL: dict[str, str] = {
    "recreational": "low",
    "competitive_club": "medium",
    "elite_club": "high",
}
DEFAULT_INTENSITY: str = "medium"  # PENDING_CLINICAL


# ──────────────────────────────────────────────────────────────────────────
# Fluid model (event day). fluids_ml = maintenance baseline + sweat replacement.
#   • maintenance baseline = Blueprint REST hydration (ml) — the non-activity need
#   • sweat replacement     = calc_sweat_output()["hydration_oz_during"] (oz→ml)
# Using the REST band as baseline avoids double-counting the activity that the
# event-type hydration band already bakes in. PENDING_CLINICAL: the replacement
# factor scales how much of measured sweat loss we target replacing.
# ──────────────────────────────────────────────────────────────────────────
FLUID_REPLACEMENT_FACTOR: float = 1.00  # PENDING_CLINICAL


# ──────────────────────────────────────────────────────────────────────────
# Sodium model (event day). Blueprint computes NO sodium (Audit 1), so this is
# the only sodium source. Reuses calc_sweat_output()["sweat_loss_liters"].
#   sodium_mg = SODIUM_BASELINE_MG + sweat_loss_liters × SODIUM_MG_PER_L_SWEAT
# Rest day → sodium_mg = None (D4): no fabricated number, gauge hidden/greyed.
# ──────────────────────────────────────────────────────────────────────────
SODIUM_BASELINE_MG: float = 1500.0       # PENDING_CLINICAL — youth daily baseline
SODIUM_MG_PER_L_SWEAT: float = 1000.0    # PENDING_CLINICAL — sweat [Na+] ≈ 1 g/L


# ──────────────────────────────────────────────────────────────────────────
# Calcium (D5). FLAT 1300 mg/day for ages 9–17 (AAP) — independent of age band,
# training load, intensity, and day type. Matches Blueprint
# (calc_daily_targets returns calcium_mg=1300); the event-day path reuses it.
# Age-banding is deferred until the dietitian supplies bands.
# ──────────────────────────────────────────────────────────────────────────
CALCIUM_MG_FLAT: int = 1300  # keep in sync with nutrition_calc.calc_daily_targets


# ──────────────────────────────────────────────────────────────────────────
# Per-window contribution weights — one row per REAL category_key (Audit 4).
# D6: TAPPABLE categories only. ``hydrate`` (fuel_during) is nudge-only and can
# never be confirmed, so it carries NO creditable weight and is excluded; its
# fluid/sodium share is folded into ``recovery``.
#
# Weights are RELATIVE. split_targets_across_windows() normalises them PER
# NUTRIENT across the categories actually present on the day, so confirming all
# tappable windows fills each gauge to ~100% (T2).
# PENDING_CLINICAL — placeholder shares.
# ──────────────────────────────────────────────────────────────────────────
CONTRIBUTION_WEIGHTS: dict[str, dict[str, float]] = {
    # category_key:  protein  carbs   fluids  sodium  calcium
    "carb":     {"protein_g": 0.25, "carbs_g": 0.35, "fluids_ml": 0.30, "sodium_mg": 0.30, "calcium_mg": 0.20},
    "recovery": {"protein_g": 0.45, "carbs_g": 0.40, "fluids_ml": 0.40, "sodium_mg": 0.45, "calcium_mg": 0.30},
    "balanced": {"protein_g": 0.30, "carbs_g": 0.25, "fluids_ml": 0.30, "sodium_mg": 0.25, "calcium_mg": 0.50},
}

# Categories that never carry creditable weight (nudge-only). Excluded from the
# split (D6). split_targets_across_windows() must skip windows in these categories.
NON_TAPPABLE_CATEGORIES: tuple[str, ...] = ("hydrate",)


def is_creditable_category(category_key: Optional[str]) -> bool:
    """True if a window in this category can be confirmed and credit a gauge."""
    return bool(category_key) and category_key not in NON_TAPPABLE_CATEGORIES


# ──────────────────────────────────────────────────────────────────────────
# Phase 5 — Purvi's signed-off PER-SLOT macro seed ratios. Fractions of the
# DAILY target; split_targets_across_windows normalizes them across whatever
# windows are present (so the day still reconciles to ~100%). Only carbs_g and
# protein_g are slot-seeded — fluids_ml/sodium_mg/calcium_mg keep the category
# CONTRIBUTION_WEIGHTS distribution, so HYDRATION is never driven by these.
#   • "everyday" is the COMBINED total for all everyday windows; the split
#     divides it across the everyday windows actually present (not 7% each).
#   • tournament/merge windows (between_games/refuel_ready) are OUT OF SCOPE —
#     they have no entry here and keep the category_key distribution.
# proper_breakfast_after / quick_morning_snack values are midpoints of Purvi's
# stated ranges (25-30% and 5-10% CHO / 0-2% protein).
# ──────────────────────────────────────────────────────────────────────────
SLOT_MACRO_RATIOS: dict[str, dict[str, float]] = {
    #  slot:                     carbs_g  protein_g
    "fuel_before":             {"carbs_g": 0.35,  "protein_g": 0.20},
    "top_up":                  {"carbs_g": 0.10,  "protein_g": 0.10},
    "recharge":                {"carbs_g": 0.20,  "protein_g": 0.25},
    "rebuild":                 {"carbs_g": 0.25,  "protein_g": 0.30},
    "proper_breakfast_after":  {"carbs_g": 0.275, "protein_g": 0.275},
    "quick_morning_snack":     {"carbs_g": 0.075, "protein_g": 0.01},
    "everyday":                {"carbs_g": 0.07,  "protein_g": 0.10},   # TOTAL, split across present everyday windows
}

# Nutrients driven by the per-slot ratios above. Everything else stays on the
# category_key CONTRIBUTION_WEIGHTS path (hydration unchanged).
SLOT_SEEDED_NUTRIENTS: tuple[str, ...] = ("carbs_g", "protein_g")
