# Window Distribution Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Purvi's `window_distribution.py` (per-window CHO:PRO gram split + ratio validation) into the live Today Mission so the per-slot `carbs_g`/`protein_g` shown to athletes come from the dietician's `SPLITS`/`validate_windows()` instead of the legacy `_FOCUS_MACRO_PCT` table.

**Architecture:** The live Today Mission flows `today.py` → `compute_meal_slots()` (hyphen-taxonomy slot list) → `build_mission_items_from_slots()` (allocates grams via `_FOCUS_MACRO_PCT`). We insert a new pure adapter `distribute_to_slots()` in `window_distribution.py` that maps each engine slot to one of Purvi's 6 windows, calls `validate_windows()` once, and divides each window's gram target evenly across the slots that map to it (preserving the daily total). `build_mission_items_from_slots()` calls the adapter when `EVENT_RELATIVE_WINDOWS` is set, falling back to `_FOCUS_MACRO_PCT` otherwise. Reversible behind the existing flag.

**Tech Stack:** Python 3.12, pytest, FastAPI, SQLite. No new dependencies.

---

## Background facts (verified against the codebase — read before starting)

**Live Today Mission path:**
- [`api/routes/today.py:239-245`](../../../api/routes/today.py) — builds `mission_items`:
  ```python
  slot_defs = compute_meal_slots(event_type, start_time, duration_hours)
  logged_slots = {r["slot_name"]: bool(r["logged"]) for r in plan_rows}
  mission_items = build_mission_items_from_slots(slot_defs, logged_slots, targets)
  ```
- `compute_meal_slots()` ([`api/services/meal_timing.py:234`](../../../api/services/meal_timing.py)) returns slot dicts with **hyphen** `slot_name`s: `breakfast`, `mid-morning-snack`, `lunch`, `power-snack`, `pre-game-fuel`/`pre-training`, `during-game-hydration`/`during-practice-hydration` (`is_hydration=True`), `halftime-fueling`, `recovery-fuel`, `recovery-dinner`, `dinner`, `night-fuel`, `between-games`, `daily-hydration` (`is_hydration=True`). Rest days use `_REST_SLOTS`: `breakfast`, `mid-morning-snack`, `lunch`, `afternoon-snack`, `dinner`, `evening-recovery`, `daily-hydration`.
- `build_mission_items_from_slots()` ([`api/services/today_service.py:560`](../../../api/services/today_service.py)) currently allocates grams:
  ```python
  focus = get_macro_focus(slot_name)              # slot → focus label
  pcts  = _FOCUS_MACRO_PCT.get(focus, {...})      # focus → {carbs_pct, protein_pct}
  item["carbs_g"]   = round(daily_carbs   * pcts["carbs_pct"])
  item["protein_g"] = round(daily_protein * pcts["protein_pct"])
  ```
  It receives `(slot_defs, logged_slots, targets=None)` — **no `wt_kg`, no `is_sc_day`**. These must be threaded in.

**Purvi's module** ([`api/services/window_distribution.py`](../../../api/services/window_distribution.py)) — already committed:
- `SPLITS` keys: `everyday_meal`, `fuel_before`, `top_up`, `keep_going`, `recharge`, `rebuild`.
- `validate_windows(wt_kg, daily_cho_g, daily_prot_g, is_sc_day=False)` → `{win: {cho_g, prot_g, ratio, flag}}` for the 5 non-`keep_going` windows. CHO/PRO each sum to ~100% of daily.
- `keep_going_window(wt_kg, duration_min)` → oz/packets dict (or `None` ≤ 75 min).

**The reconciliation problem (why this isn't a 1:1 swap):**
Purvi's `SPLITS` models a *canonical 6-window day* (one of each window). The live engine emits a *variable* slot list where **multiple slots map to the same window** — e.g. an event day has `breakfast`, `mid-morning-snack`, `lunch`, AND `dinner`, all of which are `everyday_meal`. Assigning each the full 25% CHO would over-allocate to >100%. The adapter resolves this by **dividing a window's gram target evenly across all slots mapping to it**, which keeps the daily total at 100%. Even-division is mechanically correct (totals preserved) but clinically crude (a snack ≠ a full meal); see "Open decisions for Purvi" — this is the v1 baseline, weighting is a follow-up.

**Test conventions:**
- Tests live in `tests/`, named `test_<module>.py`, run with `python3 -m pytest tests/test_x.py -v` from repo root.
- Pure-function tests import directly: `from api.services.window_distribution import distribute_to_slots`.
- No pytest config file; default discovery. Python 3.12.

---

## Open decisions for Purvi (do NOT let the engineer guess — surface these; v1 ships with the documented defaults below)

1. **Even vs. weighted division** when N slots share a window. v1 = **even** (window grams ÷ N). Weighted (meals > snacks) is a follow-up if Purvi wants it.
2. **`night-fuel` / `evening-recovery` (bedtime casein)** — not in Purvi's `SPLITS`. v1 default = **map to `rebuild`** (protein-priority post-day meal). Alternative: a fixed 30–40 g casein target from `nutrient_timing_rules.WINDOWS["bedtime_casein"]`.
3. **`recharge` RATIO_LOW** fires for most athletes (20% CHO vs 30% PRO ≈ 2.2:1 < 3.0 floor). v1 = **surface the flag to the parent dashboard only**, no auto-boost (matches spec, which auto-boosts `fuel_before` only).
4. **Strategic alternative (out of scope here):** migrate the Today Mission to consume `window_engine_v2` slots (whose labels already match Purvi's taxonomy ~1:1), eliminating the division hack. Bigger migration; note only.

---

## File Structure

- **Modify** `api/services/window_distribution.py` — add `SLOT_TO_SPLIT` mapping + `distribute_to_slots()` adapter (pure, no I/O). Responsibility: translate a variable engine slot list into per-slot gram targets using `validate_windows()`.
- **Modify** `api/services/today_service.py` — `build_mission_items_from_slots()` gains `wt_kg`/`is_sc_day`/`duration_min` params and uses the adapter behind the flag, keeping `_FOCUS_MACRO_PCT` as fallback.
- **Modify** `api/routes/today.py` — pass athlete weight, `is_sc_day`, and duration into `build_mission_items_from_slots()`; add a parent-only `window_ratio_flags` field to the response.
- **Create** `tests/test_window_distribution_integration.py` — covers the mapping, the adapter (total-preservation, even-division), and the flag-gated allocation.

---

## Task 1: Slot → split mapping table

**Files:**
- Modify: `api/services/window_distribution.py` (append after `RATIO_FLOOR`)
- Test: `tests/test_window_distribution_integration.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_window_distribution_integration.py`:

```python
from api.services.window_distribution import SLOT_TO_SPLIT, split_key_for_slot


def test_hyphen_taxonomy_maps_to_splits():
    assert split_key_for_slot("pre-game-fuel") == "fuel_before"
    assert split_key_for_slot("pre-training") == "fuel_before"
    assert split_key_for_slot("power-snack") == "top_up"
    assert split_key_for_slot("recovery-fuel") == "recharge"
    assert split_key_for_slot("recovery-dinner") == "rebuild"
    assert split_key_for_slot("breakfast") == "everyday_meal"
    assert split_key_for_slot("lunch") == "everyday_meal"
    assert split_key_for_slot("dinner") == "everyday_meal"
    assert split_key_for_slot("mid-morning-snack") == "everyday_meal"
    assert split_key_for_slot("afternoon-snack") == "everyday_meal"
    assert split_key_for_slot("between-games") == "recharge"
    assert split_key_for_slot("halftime-fueling") == "keep_going"


def test_bedtime_casein_maps_to_rebuild_v1_default():
    # Open decision #2 — v1 default maps casein/night slots to rebuild
    assert split_key_for_slot("night-fuel") == "rebuild"
    assert split_key_for_slot("evening-recovery") == "rebuild"


def test_hydration_only_slots_map_to_none():
    assert split_key_for_slot("daily-hydration") is None
    assert split_key_for_slot("during-game-hydration") is None
    assert split_key_for_slot("during-practice-hydration") is None


def test_unknown_slot_maps_to_none():
    assert split_key_for_slot("totally-unknown-slot") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_window_distribution_integration.py -v`
Expected: FAIL with `ImportError: cannot import name 'SLOT_TO_SPLIT'`

- [ ] **Step 3: Implement the mapping**

Append to `api/services/window_distribution.py`:

```python
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


def split_key_for_slot(slot_name: str):
    """Return the SPLITS key for an engine slot_name, or None if it has no
    macro split (hydration-only or unknown). Exact match first, then prefix
    match for event-index-suffixed v2 keys."""
    if slot_name in SLOT_TO_SPLIT:
        return SLOT_TO_SPLIT[slot_name]
    for prefix, key in _SLOT_PREFIX_TO_SPLIT.items():
        if slot_name.startswith(prefix):
            return key
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_window_distribution_integration.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add api/services/window_distribution.py tests/test_window_distribution_integration.py
git commit -m "feat: SLOT_TO_SPLIT mapping — engine slots → Purvi window keys"
```

---

## Task 2: `distribute_to_slots()` adapter (even-division, total-preserving)

**Files:**
- Modify: `api/services/window_distribution.py` (append after `split_key_for_slot`)
- Test: `tests/test_window_distribution_integration.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_window_distribution_integration.py`:

```python
from api.services.window_distribution import distribute_to_slots, validate_windows


def _slots(*names):
    """Minimal slot dicts as compute_meal_slots emits (only keys the adapter reads)."""
    return [{"slot_name": n, "is_hydration": n.endswith("hydration")} for n in names]


def test_distribute_skips_hydration_and_unknown():
    slots = _slots("daily-hydration", "during-game-hydration", "totally-unknown")
    out = distribute_to_slots(slots, daily_cho_g=300, daily_prot_g=100, wt_kg=55)
    assert out == {}  # nothing allocatable


def test_distribute_single_of_each_matches_validate_windows():
    # One slot per window → grams equal validate_windows() exactly (no division)
    slots = _slots("pre-game-fuel", "power-snack", "recovery-fuel", "recovery-dinner", "breakfast")
    out = distribute_to_slots(slots, daily_cho_g=326, daily_prot_g=101, wt_kg=54.4)
    w = validate_windows(54.4, 326, 101, is_sc_day=False)
    assert out["pre-game-fuel"]["cho_g"] == w["fuel_before"]["cho_g"]
    assert out["recovery-fuel"]["prot_g"] == w["recharge"]["prot_g"]
    assert out["breakfast"]["cho_g"] == w["everyday_meal"]["cho_g"]


def test_distribute_even_division_across_duplicate_window():
    # 4 everyday_meal slots split the everyday_meal bucket evenly
    slots = _slots("breakfast", "mid-morning-snack", "lunch", "dinner")
    out = distribute_to_slots(slots, daily_cho_g=320, daily_prot_g=100, wt_kg=55)
    w = validate_windows(55, 320, 100, is_sc_day=False)
    expected_cho = round(w["everyday_meal"]["cho_g"] / 4)
    for n in ("breakfast", "mid-morning-snack", "lunch", "dinner"):
        assert out[n]["cho_g"] == expected_cho


def test_distribute_carries_ratio_flag():
    slots = _slots("recovery-fuel")
    out = distribute_to_slots(slots, daily_cho_g=326, daily_prot_g=101, wt_kg=54.4)
    # recharge ratio ~2.17 < 3.0 floor → RATIO_LOW flag carried through
    assert out["recovery-fuel"]["flag"] is not None
    assert "RATIO_LOW" in out["recovery-fuel"]["flag"]


def test_distribute_sc_day_shifts_recharge_protein():
    slots = _slots("recovery-fuel")
    base = distribute_to_slots(slots, 326, 60, wt_kg=54.4, is_sc_day=False)
    sc   = distribute_to_slots(slots, 326, 60, wt_kg=54.4, is_sc_day=True)
    assert sc["recovery-fuel"]["prot_g"] > base["recovery-fuel"]["prot_g"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_window_distribution_integration.py -v`
Expected: FAIL with `ImportError: cannot import name 'distribute_to_slots'`

- [ ] **Step 3: Implement the adapter**

Append to `api/services/window_distribution.py`:

```python
def distribute_to_slots(slot_defs: list, daily_cho_g: int, daily_prot_g: int,
                        wt_kg: float, is_sc_day: bool = False) -> dict:
    """Map a variable engine slot list onto per-slot gram targets.

    Calls validate_windows() once, then divides each window's gram target evenly
    across every slot mapping to that window (preserves the daily total). Hydration
    -only and unknown slots are skipped. keep_going slots get no grams here (they
    are oz/packets — see keep_going_window); they are skipped so they don't dilute
    a macro window.

    Returns {slot_name: {cho_g, prot_g, ratio, flag, split_key}} for allocatable
    slots only.
    """
    windows = validate_windows(wt_kg, daily_cho_g, daily_prot_g, is_sc_day)

    # Resolve each slot to a split key, skipping hydration / keep_going / unknown.
    slot_keys = {}
    for slot in slot_defs:
        if slot.get("is_hydration"):
            continue
        name = slot["slot_name"]
        key  = split_key_for_slot(name)
        if key is None or key == "keep_going":
            continue
        slot_keys[name] = key

    # Count slots per window for even division.
    counts = {}
    for key in slot_keys.values():
        counts[key] = counts.get(key, 0) + 1

    out = {}
    for name, key in slot_keys.items():
        w = windows[key]
        n = counts[key]
        out[name] = {
            "cho_g":     round(w["cho_g"]  / n),
            "prot_g":    round(w["prot_g"] / n),
            "ratio":     w["ratio"],
            "flag":      w["flag"],
            "split_key": key,
        }
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_window_distribution_integration.py -v`
Expected: PASS (9 tests total)

- [ ] **Step 5: Commit**

```bash
git add api/services/window_distribution.py tests/test_window_distribution_integration.py
git commit -m "feat: distribute_to_slots() — even-division adapter over validate_windows"
```

---

## Task 3: Flag-gated allocation in `build_mission_items_from_slots()`

**Files:**
- Modify: `api/services/today_service.py:560-591`
- Test: `tests/test_window_distribution_integration.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_window_distribution_integration.py`:

```python
import os
from api.services.today_service import build_mission_items_from_slots


def _mission_slots(*names):
    return [{"slot_name": n, "display_label": n.title(), "eat_by_time": "8:00 AM",
             "is_hydration": n.endswith("hydration")} for n in names]


def test_mission_uses_distribution_when_flag_on(monkeypatch):
    monkeypatch.setenv("EVENT_RELATIVE_WINDOWS", "true")
    slots = _mission_slots("recovery-fuel")
    targets = {"carbs_g": 326, "protein_g": 101}
    items = build_mission_items_from_slots(
        slots, {}, targets, wt_kg=54.4, is_sc_day=False, duration_min=75,
    )
    from api.services.window_distribution import validate_windows
    w = validate_windows(54.4, 326, 101, is_sc_day=False)
    assert items[0]["carbs_g"] == w["recharge"]["cho_g"]
    assert items[0]["protein_g"] == w["recharge"]["prot_g"]


def test_mission_falls_back_to_focus_pct_when_flag_off(monkeypatch):
    monkeypatch.delenv("EVENT_RELATIVE_WINDOWS", raising=False)
    slots = _mission_slots("recovery-fuel")
    targets = {"carbs_g": 326, "protein_g": 101}
    items = build_mission_items_from_slots(
        slots, {}, targets, wt_kg=54.4, is_sc_day=False, duration_min=75,
    )
    # Legacy path: recovery-fuel → "Recovery Focus" → carbs_pct 0.15
    assert items[0]["carbs_g"] == round(326 * 0.15)
    assert items[0]["protein_g"] == round(101 * 0.25)


def test_mission_falls_back_when_wt_kg_missing(monkeypatch):
    monkeypatch.setenv("EVENT_RELATIVE_WINDOWS", "true")
    slots = _mission_slots("recovery-fuel")
    targets = {"carbs_g": 326, "protein_g": 101}
    # No wt_kg → cannot run validate_windows → legacy path
    items = build_mission_items_from_slots(slots, {}, targets)
    assert items[0]["carbs_g"] == round(326 * 0.15)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_window_distribution_integration.py -v`
Expected: FAIL — `build_mission_items_from_slots()` got an unexpected keyword argument `wt_kg`

- [ ] **Step 3: Implement the flag-gated allocation**

In `api/services/today_service.py`, add the import near the top (with the other `api.services` imports):

```python
from api.services.window_distribution import distribute_to_slots
from api.services.window_engine_v2 import event_relative_windows_enabled
```

Replace `build_mission_items_from_slots()` (currently lines 560-591) with:

```python
def build_mission_items_from_slots(slot_defs: list, logged_slots: dict, targets: dict = None,
                                   wt_kg: float = None, is_sc_day: bool = False,
                                   duration_min: float = 0) -> list:
    """
    Converts compute_meal_slots output into Today's Mission items.
    Skips hydration-only slots and double-day alert banners.
    logged_slots: {slot_name: bool} from the meal_plans table.
    targets: daily nutrition targets dict; when provided, adds per-slot carbs_g/protein_g.

    Macro allocation:
      - When EVENT_RELATIVE_WINDOWS is set AND wt_kg is provided, per-slot grams
        come from window_distribution.distribute_to_slots() (Purvi's SPLITS).
      - Otherwise falls back to the legacy _FOCUS_MACRO_PCT table.
    """
    daily_carbs   = (targets or {}).get("carbs_g")   or (targets or {}).get("carbs_g_max")
    daily_protein = (targets or {}).get("protein_g") or (targets or {}).get("protein_g_max")

    # Try the distribution path; fall back to legacy on any precondition miss.
    distributed = None
    if (event_relative_windows_enabled() and wt_kg and daily_carbs and daily_protein):
        distributed = distribute_to_slots(
            slot_defs, round(daily_carbs), round(daily_protein), wt_kg, is_sc_day,
        )

    missions = []
    i = 0
    for slot in slot_defs:
        if slot.get("is_hydration") or slot.get("double_day_alert"):
            continue
        slot_name  = slot["slot_name"]
        focus      = get_macro_focus(slot_name)
        item = {
            "id":          f"mission_{i}",
            "time":        slot.get("eat_by_time", ""),
            "label":       slot.get("display_label", slot_name),
            "macro_focus": focus,
            "logged":      logged_slots.get(slot_name, False),
            "meal_type":   slot_name,
        }
        if distributed is not None and slot_name in distributed:
            d = distributed[slot_name]
            item["carbs_g"]   = d["cho_g"]
            item["protein_g"] = d["prot_g"]
            item["ratio_flag"] = d["flag"]   # parent-only; surfaced by route
        elif daily_carbs and daily_protein:
            pcts = _FOCUS_MACRO_PCT.get(focus, {"carbs_pct": 0.15, "protein_pct": 0.15})
            item["carbs_g"]   = round(daily_carbs   * pcts["carbs_pct"])
            item["protein_g"] = round(daily_protein * pcts["protein_pct"])
        missions.append(item)
        i += 1
    return missions
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_window_distribution_integration.py -v`
Expected: PASS (12 tests total)

- [ ] **Step 5: Run the existing today_service suite to confirm no regression**

Run: `python3 -m pytest tests/test_today_service.py -v`
Expected: PASS (all existing tests still green — the new params are optional, default behavior unchanged when flag off)

- [ ] **Step 6: Commit**

```bash
git add api/services/today_service.py tests/test_window_distribution_integration.py
git commit -m "feat: Today Mission uses window_distribution behind EVENT_RELATIVE_WINDOWS flag"
```

---

## Task 4: Pass weight/SC-day/duration from the route + parent-only ratio flags

**Files:**
- Modify: `api/routes/today.py:236-276`
- Test: manual smoke (route requires DB + auth; covered by the adapter unit tests)

- [ ] **Step 1: Add the lbs→kg import**

In `api/routes/today.py`, confirm/add to the `nutrition_calc` import line:

```python
from api.services.nutrition_calc import calc_daily_targets, lbs_to_kg
```

- [ ] **Step 2: Compute weight, SC-day, duration and pass them in**

Replace the mission-building block (currently lines 236-245) with:

```python
        # Build mission items from the same slot definitions used by the Meal Plan tab
        start_time     = events[0]["start_time"]     if events else None
        duration_hours = events[0]["duration_hours"] if events else None
        slot_defs = compute_meal_slots(event_type, start_time, duration_hours)
        plan_rows = conn.execute(
            "SELECT slot_name, logged FROM meal_plans WHERE athlete_id = ? AND plan_date = ?",
            (athlete_id, target_date),
        ).fetchall()
        logged_slots = {r["slot_name"]: bool(r["logged"]) for r in plan_rows}

        wt_kg     = lbs_to_kg(athlete["weight_lbs"]) if athlete.get("weight_lbs") else None
        is_sc_day = (event_type or "").lower() in ("strength", "conditioning")
        duration_min = round((duration_hours or 0) * 60)
        mission_items = build_mission_items_from_slots(
            slot_defs, logged_slots, targets,
            wt_kg=wt_kg, is_sc_day=is_sc_day, duration_min=duration_min,
        )

        # Parent-only: collect any per-window ratio flags (never shown to athlete UI)
        window_ratio_flags = [
            {"slot": m["meal_type"], "flag": m["ratio_flag"]}
            for m in mission_items
            if m.get("ratio_flag")
        ]
```

- [ ] **Step 3: Add the parent-only field to the response dict**

In the `return {...}` block (currently ends ~line 276), add one line before the closing brace:

```python
            "mission_items": mission_items,
            "window_ratio_flags": window_ratio_flags,
        }
```

- [ ] **Step 4: Smoke-test the import path compiles**

Run: `python3 -c "import api.routes.today"`
Expected: no output, exit 0 (no syntax/import errors)

- [ ] **Step 5: Run the full backend suite**

Run: `python3 -m pytest tests/ -q`
Expected: all green (no regressions)

- [ ] **Step 6: Commit**

```bash
git add api/routes/today.py
git commit -m "feat: Today route passes weight/SC-day to mission split; parent-only ratio flags"
```

---

## Task 5: End-to-end verification with realistic event days

**Files:**
- Test: `tests/test_window_distribution_integration.py`

- [ ] **Step 1: Write the end-to-end test**

Append to `tests/test_window_distribution_integration.py`:

```python
from api.services.meal_timing import compute_meal_slots


def test_e2e_event_day_totals_stay_within_daily(monkeypatch):
    """Per-slot grams summed across an event day must not exceed the daily total."""
    monkeypatch.setenv("EVENT_RELATIVE_WINDOWS", "true")
    slots = compute_meal_slots("practice", "16:00", 1.5)
    targets = {"carbs_g": 326, "protein_g": 101}
    items = build_mission_items_from_slots(
        slots, {}, targets, wt_kg=54.4, is_sc_day=False, duration_min=90,
    )
    total_cho  = sum(it.get("carbs_g", 0)   for it in items)
    total_prot = sum(it.get("protein_g", 0) for it in items)
    # Even-division preserves totals; allow small rounding drift (±1 per window).
    assert total_cho  <= 326 + 6
    assert total_prot <= 101 + 6
    # And it should allocate a meaningful share (not near-zero)
    assert total_cho  >= 326 * 0.8


def test_e2e_rest_day_everyday_meals_only(monkeypatch):
    monkeypatch.setenv("EVENT_RELATIVE_WINDOWS", "true")
    slots = compute_meal_slots("rest", None, None)
    targets = {"carbs_g": 250, "protein_g": 90}
    items = build_mission_items_from_slots(
        slots, {}, targets, wt_kg=50, is_sc_day=False, duration_min=0,
    )
    # Every non-hydration rest slot is everyday_meal → all get equal grams
    cho_values = {it["carbs_g"] for it in items if "carbs_g" in it}
    assert len(cho_values) == 1  # even division → all identical
```

- [ ] **Step 2: Run the end-to-end test**

Run: `python3 -m pytest tests/test_window_distribution_integration.py -v`
Expected: PASS (14 tests total)

- [ ] **Step 3: Manual sanity print (optional, not committed)**

Run:
```bash
python3 -c "
import os; os.environ['EVENT_RELATIVE_WINDOWS']='true'
from api.services.meal_timing import compute_meal_slots
from api.services.today_service import build_mission_items_from_slots
slots = compute_meal_slots('practice','16:00',1.5)
items = build_mission_items_from_slots(slots, {}, {'carbs_g':326,'protein_g':101}, wt_kg=54.4, duration_min=90)
for it in items: print(f\"{it['meal_type']:28s} cho={it.get('carbs_g'):>4} prot={it.get('protein_g'):>4} flag={it.get('ratio_flag')}\")
print('TOTAL cho', sum(i.get('carbs_g',0) for i in items), 'prot', sum(i.get('protein_g',0) for i in items))
"
```
Expected: per-slot grams print; totals ≈ 326 / 101.

- [ ] **Step 4: Commit**

```bash
git add tests/test_window_distribution_integration.py
git commit -m "test: end-to-end window-distribution allocation over realistic event/rest days"
```

---

## After all tasks

- [ ] Run full suite once more: `python3 -m pytest tests/ -q` — confirm green.
- [ ] Use **superpowers:finishing-a-development-branch** to decide merge/PR.
- [ ] **Before enabling for athletes:** review the four "Open decisions for Purvi" with the dietician. The flag (`EVENT_RELATIVE_WINDOWS`) is already true in prod for window *timing*; this change rides the same flag, so flipping it affects *both*. If timing-v2 is already live, this allocation change goes live with the next deploy — confirm Purvi has signed off on even-division + the recharge RATIO_LOW behavior first, or gate behind a *separate* flag (e.g. `WINDOW_MACRO_SPLIT_V2`) if she wants timing and macro-split decoupled.

---

## Self-Review

**Spec coverage:**
- Map engine slots → Purvi windows → Task 1 ✅
- Reconcile multiple-slots-per-window → Task 2 (even-division) ✅
- Swap `_FOCUS_MACRO_PCT` → `validate_windows` → Task 3 ✅
- Thread `wt_kg`/`is_sc_day`/`duration` → Task 4 ✅
- `keep_going` as oz/packets not grams → Task 2 (skipped from gram split; `keep_going_window` already exists for oz/packets) ✅
- RATIO_LOW flags parent-only → Task 3 (`ratio_flag` field) + Task 4 (`window_ratio_flags`) ✅
- Reversible behind flag with fallback → Task 3 ✅

**Gap flagged, not silently dropped:** `keep_going` oz/packet *rendering* in the athlete UI is mobile-side; this plan only stops it polluting the gram split and exposes `keep_going_window()` for the client. The actual halftime oz/packet card render is a mobile task, noted here, not implemented.

**Type consistency:** `distribute_to_slots()` returns `cho_g`/`prot_g` (matching `validate_windows`); `build_mission_items_from_slots` reads `d["cho_g"]`→`item["carbs_g"]` (the mission-item convention is `carbs_g`). Mapping is explicit and consistent across Tasks 2–4. `split_key_for_slot` used in both Task 1 tests and Task 2 implementation.

**Flag naming:** uses the existing `event_relative_windows_enabled()` helper from `window_engine_v2.py` — confirmed to exist (line 26). The "separate flag" option is raised in the final checklist as a decision, not implemented.
