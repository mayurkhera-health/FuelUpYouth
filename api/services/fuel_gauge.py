"""
fuel_gauge.py — Fuel Gauge calculation engine (PURE functions, no DB / no I/O).

Two target sources (Phase 0 core architecture decision):

  • REST DAY  → compute_rest_day_targets(): a thin adapter that DELEGATES to the
                Blueprint calculation (nutrition_calc.calc_daily_targets) so that
                Today and Blueprint can never disagree for the same athlete
                (the T6/T7 credibility guarantee).

  • EVENT DAY → compute_event_day_targets(): Blueprint macros (calc_daily_targets,
                decision D1) + season-phase modifiers + weather-driven fluids and
                sodium (reusing calc_sweat_output — the sweat model is not
                reinvented).

Every coefficient comes from fueling_targets.py ONLY. Macro math is NEVER
reimplemented here — see the explicit calc_daily_targets() calls below (D1).
Units are canonical here: grams, millilitres, milligrams (oz is display-only, D3).
"""

from __future__ import annotations

import logging
from typing import Optional

from api.services.nutrition_calc import (
    calc_daily_targets,
    normalize_event_type,
    derive_intensity,
)
from api.services.weather import calc_sweat_output
from api.services import fueling_targets as ft

log = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────
def _oz_to_ml(oz: Optional[float]) -> Optional[float]:
    return None if oz is None else oz * ft.OZ_TO_ML


def _round_targets(t: dict) -> dict:
    """Round to display-sensible precision over the 5 canonical keys. Preserves
    None (a metric the source does not provide, e.g. rest-day sodium — D4)."""
    def r(key: str, val):
        if val is None:
            return None
        return round(val, 1) if key == "protein_g" else int(round(val))
    return {k: r(k, t.get(k)) for k in ft.NUTRIENT_KEYS}


def _dominant_event(events: list[dict]) -> dict:
    """The day's highest-load event drives the macro base. Ranking is on the
    NORMALIZED event_type so it agrees with what calc_daily_targets will see."""
    def rank(ev: dict) -> int:
        return ft.EVENT_TYPE_LOAD_RANK.get(normalize_event_type(ev.get("event_type") or ""), 0)
    return max(events, key=rank)


def _resolve_intensity(event: dict, athlete: dict) -> str:
    """Use the event's explicit intensity if set; otherwise derive it from the
    athlete's competition level via the existing Blueprint-side helper."""
    iv = (event.get("intensity") or "").strip().lower()
    if iv in ("low", "medium", "high"):
        return iv
    return derive_intensity(event.get("event_type") or "", athlete.get("competition_level"))


# ── rest-day path (delegates to Blueprint) ──────────────────────────────────
def compute_rest_day_targets(athlete: dict, season_phase: Optional[str] = None) -> dict:
    """Rest-day daily targets = the Blueprint baseline, each macro band reduced to
    a single value per D2. NOT a reimplementation — a pure delegate.

    season_phase is accepted for signature symmetry but intentionally NOT applied:
    the rest-day gauge must equal what Blueprint shows for the same athlete
    (T6/T7), and Blueprint does not model season phase. Sodium is None — Blueprint
    computes none (D4); the gauge shows only what Blueprint provides on rest days.
    """
    base = calc_daily_targets(athlete, ft.REST_EVENT_TYPE)  # D1: Blueprint is the source
    return _round_targets({
        "protein_g":  ft.reduce_range(base["protein_g_min"], base["protein_g_max"]),
        "carbs_g":    ft.reduce_range(base["carbs_g_min"], base["carbs_g_max"]),
        "fluids_ml":  _oz_to_ml(ft.reduce_range(base["hydration_oz_min"], base["hydration_oz_max"])),
        "sodium_mg":  None,
        "calcium_mg": base["calcium_mg"],
    })


# ── event-day path (Blueprint macros + modifiers + weather) ─────────────────
def compute_event_day_targets(
    athlete: dict,
    todays_events: list[dict],
    season_phase: Optional[str],
    weather_data: Optional[dict],
) -> dict:
    """Event-day daily targets. Pure: weather is passed in, never fetched here.

    Macros: Blueprint's calc_daily_targets() for the day's dominant event, then a
    season-phase multiplier (D1 — no parallel macro formula).
    Fluids:  rest maintenance baseline + sweat replacement (reuses weather engine).
    Sodium:  baseline + sweat-driven, aggregated across ALL events (load adds up)
             — the only sodium source, since Blueprint computes none.
    Calcium: flat 1300mg, load-independent (D5).
    """
    if not todays_events:
        # Defensive only — the caller selects the path by event count.
        return compute_rest_day_targets(athlete, season_phase)

    sp = ft.normalize_season_phase(season_phase)
    weather = weather_data or {}

    # Training load → the dominant event drives macros (no double-count across events).
    dominant = _dominant_event(todays_events)
    event_type = dominant.get("event_type") or ft.REST_EVENT_TYPE
    intensity = _resolve_intensity(dominant, athlete)

    # ───────────────────────────────────────────────────────────────────────
    # D1: macros come from Blueprint's calc_daily_targets — NOT reimplemented.
    # ───────────────────────────────────────────────────────────────────────
    base = calc_daily_targets(athlete, event_type, intensity)
    protein = ft.reduce_range(base["protein_g_min"], base["protein_g_max"]) * ft.SEASON_PHASE_PROTEIN_MULT[sp]
    carbs = ft.reduce_range(base["carbs_g_min"], base["carbs_g_max"]) * ft.SEASON_PHASE_CARB_MULT[sp]

    # Fluids: rest maintenance baseline (avoids double-counting activity already
    # baked into the event-type hydration band) + measured sweat replacement.
    rest_base = calc_daily_targets(athlete, ft.REST_EVENT_TYPE)
    fluids_ml = _oz_to_ml(ft.reduce_range(rest_base["hydration_oz_min"], rest_base["hydration_oz_max"]))

    # Sodium + sweat fluids: aggregate the sweat model across every event.
    # Also capture the child-safe DECISION boolean (electrolytes_needed) — already
    # computed by calc_sweat_output. We deliberately do NOT capture electrolyte_reason
    # or recommendations (they embed numbers / a researcher name — unsafe for athlete
    # display). The sodium_mg math below is unchanged.
    sodium_mg = ft.SODIUM_BASELINE_MG
    sweat_oz_total = 0.0
    electrolytes_needed = False
    for ev in todays_events:
        sweat = calc_sweat_output(athlete, ev, weather)  # reused, not reinvented
        sodium_mg += (sweat.get("sweat_loss_liters") or 0.0) * ft.SODIUM_MG_PER_L_SWEAT
        sweat_oz_total += (sweat.get("hydration_oz_during") or 0.0)
        if sweat.get("electrolytes_needed"):
            electrolytes_needed = True
    fluids_ml = (fluids_ml or 0.0) + _oz_to_ml(sweat_oz_total) * ft.FLUID_REPLACEMENT_FACTOR

    targets = _round_targets({
        "protein_g":  protein,
        "carbs_g":    carbs,
        "fluids_ml":  fluids_ml * ft.SEASON_PHASE_FLUID_MULT[sp],
        "sodium_mg":  sodium_mg * ft.SEASON_PHASE_SODIUM_MULT[sp],
        "calcium_mg": ft.CALCIUM_MG_FLAT,
    })
    # Additive: day-level decision flag only (no mg / text / reason leaves the engine here).
    targets["electrolytes_needed"] = electrolytes_needed
    return targets


# ── per-window contribution split ───────────────────────────────────────────
# ── per-window macro seed resolution (Phase 5 — Purvi per-slot ratios) ────────
def _slot_for_window(window_key: str) -> Optional[str]:
    """Map an engine window_key (== split slot_name) to a Purvi macro slot.
    Suffix-tolerant (pre_event_meal, pre_event_meal_1, …). Tournament/merge windows
    (between_games_*, refuel_ready_*) return None — OUT OF SCOPE, they keep the
    category_key distribution (no per-slot reseed).

    The day-layout engine (DAY_LAYOUT_V2) uses compact slot names that ARE the
    split key directly (fuel_before, top_up, recharge, rebuild, everyday_meal).
    These are matched first so the prefix checks below still handle the legacy
    window_engine_v2 suffixed variants.
    """
    wk = window_key or ""
    # Day-layout compact names — exact match (no suffix variants in this engine).
    if wk == "fuel_before":                      return "fuel_before"
    if wk == "top_up":                           return "top_up"
    if wk == "recharge":                         return "recharge"
    if wk == "rebuild":                          return "rebuild"
    # Legacy window_engine_v2 prefix variants (suffix-tolerant).
    if wk.startswith("pre_event_meal"):         return "fuel_before"
    if wk.startswith("top_up_snack"):           return "top_up"
    if wk.startswith("fuel_after_primary"):     return "recharge"
    if wk.startswith("fuel_after_second"):      return "rebuild"
    if wk.startswith("proper_breakfast_after"): return "proper_breakfast_after"
    if wk.startswith("quick_morning_snack"):    return "quick_morning_snack"
    if wk.startswith("everyday_"):              return "everyday"
    return None


def _seed_ratio(w: dict, n: str, n_everyday: int) -> float:
    """Per-window seed weight for nutrient ``n`` (used by the normalization below).

    • carbs_g / protein_g → Purvi per-slot ratio. The "everyday" TOTAL is divided
      across the everyday windows actually present that day (not applied per-window).
      Tournament windows (slot None) fall back to the category_key weight — they are
      out of scope for the reseed.
    • fluids_ml / sodium_mg / calcium_mg → UNCHANGED category_key CONTRIBUTION_WEIGHTS
      distribution; hydration is never driven by these ratios.
    """
    cat = w.get("category_key")
    if n in ft.SLOT_SEEDED_NUTRIENTS:
        slot = _slot_for_window(w.get("slot_name") or "")
        if slot == "everyday":
            base = ft.SLOT_MACRO_RATIOS["everyday"].get(n, 0.0)
            return (base / n_everyday) if n_everyday else 0.0
        if slot is not None:
            return ft.SLOT_MACRO_RATIOS.get(slot, {}).get(n, 0.0)
        return ft.CONTRIBUTION_WEIGHTS.get(cat, {}).get(n, 0.0)  # tournament / out-of-scope
    return ft.CONTRIBUTION_WEIGHTS.get(cat, {}).get(n, 0.0)


def split_targets_across_windows(daily_targets: dict, windows: list[dict]) -> list[dict]:
    """Divide each daily target across the day's CREDITABLE windows, normalized PER
    NUTRIENT so the day's windows sum to ~100% of each target (D6, T2).

    Macro split (carbs_g/protein_g) uses Purvi's PER-SLOT seed ratios resolved from
    slot_name (fueling_targets.SLOT_MACRO_RATIOS); fluids_ml/sodium_mg/calcium_mg keep
    the per-category CONTRIBUTION_WEIGHTS distribution (hydration is NOT reseeded).

    • Non-tappable categories (hydrate/fuel_during) are excluded — never confirmable.
    • A None daily target (e.g. rest-day sodium) yields None contributions.
    • Everyday TOTAL macro share is split across the everyday windows present.

    Returns one entry per creditable window: {slot_name, category_key, contribution}.
    """
    creditable = [w for w in windows if ft.is_creditable_category(w.get("category_key"))]

    n_everyday = sum(
        1 for w in creditable if _slot_for_window(w.get("slot_name") or "") == "everyday"
    )

    # Per-nutrient sum of SEED weights across the windows actually present today.
    totals = {
        n: sum(_seed_ratio(w, n, n_everyday) for w in creditable)
        for n in ft.NUTRIENT_KEYS
    }

    result = []
    for w in creditable:
        contribution = {}
        for n in ft.NUTRIENT_KEYS:
            target = daily_targets.get(n)
            tw = totals[n]
            if target is None:
                contribution[n] = None
            elif tw <= 0:
                contribution[n] = 0
            else:
                contribution[n] = _seed_ratio(w, n, n_everyday) / tw * target
        result.append({
            "slot_name": w.get("slot_name"),
            "category_key": w.get("category_key"),
            "contribution": _round_targets(contribution),
        })
    return result
