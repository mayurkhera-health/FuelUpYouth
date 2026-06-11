# Meal Planner Day View Redesign — Design Spec

**Date:** 2026-06-10
**Status:** Approved

---

## Overview

Redesign the Meal Planner from a static weekly horizontal-scroll grid into a single-day timeline view. Meal categories are **dynamically calculated** from the athlete's schedule using a timing engine — the slots shown, their names, and their "Eat by" times all derive from the event's actual start time, duration, and type. The weekly overview is stubbed out (greyed toggle) for a later iteration.

---

## Goals

- Give parents/athletes more space to plan each day's meals
- Educate on *how* to fuel for each day type with contextual slot names and timing
- Make "Eat by" times concrete and actionable (derived from the schedule, not generic)
- Remove clutter: no auto-generated plans, no "Mark as Eaten" in the planner
- Simple day-by-day navigation

---

## Screen Structure

### Header

```
[ 🍳  Meal Planner        ]  [ Day | Week (greyed) ]
      Mehr Khera
```

- **Day | Week toggle** — top-right. "Day" is active. "Week" is visually greyed out (`color: #c0c0c0`, `cursor: not-allowed`). Tapping "Week" shows a brief "Coming soon" tooltip; no navigation occurs.

### Week Dot Strip

A row of 7 dots, one per day of the current week (Mon–Sun). Each dot shows:
- Day initial (M / T / W / T / F / S / S) with date number below
- Small coloured indicator dot below the number for event type (green = rest, amber = practice/training, red = game, purple = tournament)
- **Active dot** (currently viewed day) — filled dark green
- **Planned dot** (≥1 slot filled) — light green
- **Empty dot** — grey

Tapping any dot navigates directly to that day.

### Day Navigator

```
  ‹        WEDNESDAY          ›
              10
           June 2026
```

- ‹ / › buttons navigate one day at a time
- Crossing Sunday → Monday loads next week's data from the API
- Crossing Monday → Sunday loads previous week's data

### Day Hero Card

Full-width colour-coded banner at the top of the day. Colour is determined by event type:

| Event type | Gradient | BG emoji |
|---|---|---|
| Rest | `#2d6a4f → #52b788` (green) | 🌿 |
| Practice / Training / Strength | `#b45309 → #f59e0b` (amber) | 🏃 |
| Game | `#9a1a1a → #e05a4a` (red) | ⚽ |
| Tournament | `#4a2a8a → #9a7ae8` (purple) | 🏆 |

Contents:
- Small pill badge with event type label
- Bold day title
- 2–3 sentence educational description (see copy table below)
- Calorie progress bar: `{planned} / {target} kcal` embedded at the bottom

#### Hero Copy by Day Type

| Event type | Title | Description |
|---|---|---|
| Rest | Recovery & Rebuild Day | No training today — your body is repairing muscle and replenishing glycogen. Focus on protein to rebuild and complex carbs to restore energy stores. Prioritise iron-rich foods and calcium for bone health. |
| Practice / Training / Strength | Training Fuel Day | Your body needs sustained energy before practice and fast recovery after. Load up on complex carbs at lunch and your pre-training meal, then hit the protein + carb recovery window right after finishing. |
| Game | Game Day — Perform & Recover | Today is all about peak performance and rapid recovery. Front-load carbs before kick-off, stay on top of hydration throughout, and hit your recovery window within 30 minutes of the final whistle. |
| Tournament | Tournament Day — Fuel to Compete | Multiple games means fuel management is critical. Prioritise carb availability all day, recover fast between games, and protect your muscles with quality protein at dinner. |

### Timeline Slot Layout

Each slot in the timeline has a vertical line running down the left with a dot marking its position. Each slot card shows:

- Emoji icon + slot name (bold)
- "Eat by [exact clock time]" derived from the timing engine
- Nutrition guidance tags (coloured pills)
- **＋ Add Meal / ＋ Add Snack** button (green outline)

When a recipe is assigned to a slot:
- Recipe name + kcal shown
- **🔄 Swap** and **✕ Remove** buttons
- No "Mark as Eaten" button (removed from this screen)

**Hydration slots** — informational only. Show the calculated fluid target and guidance text. No Add button. No recipe assignment.

### Removed Elements

- "Generate Week Plan" / "Generate Day Plan" button — removed entirely
- "Mark as Eaten" button — removed from all slot cards
- `overwriteWarning` and `aiReasoning` UI — removed
- Week View — greyed out toggle, not built in this iteration

---

## Dynamic Timing Engine

Meal categories are calculated per-day by a server-side service function. The engine runs 4 steps.

### Step 1 — Read Calendar Event

For the given athlete and date, read from `events` table:
- `event_type` (practice / game / tournament / rest)
- `start_time` (HH:MM, 24h)
- `duration_minutes`
- Derived: `event_end = start_time + duration_minutes`

If no event exists for the date → `event_type = "rest"`, skip to Step 4 rest template.

### Step 2 — Apply Timing Formulas

| Slot name | Formula | Applies to |
|---|---|---|
| Pre-Event Fuel | `event_start − 3h` | practice, game, tournament |
| Power Snack | `event_start − 45min` | practice, game, tournament |
| Halftime Fueling | `event_start + 45min` | game, tournament |
| Recovery Fuel | `event_end + 30min` | practice, game, tournament |
| Night Fuel | 21:00–22:00 (fixed) | practice, game, tournament |
| During Hydration | `event_start → event_end` | all event types |

### Step 3 — Check for Conflicts

**Rule 1 — Early Event (Pre-Event Fuel before 06:00)**
```
IF pre_event_fuel_time < 06:00
  → Remove Pre-Event Fuel slot
  → Keep Power Snack only
  → Add note: "Early event — light snack only before kick-off"
```

**Rule 2 — Late Event (event ends after 19:00)**
```
IF event_end_time > 19:00
  → Remove separate Recovery Fuel slot
  → Remove separate Night Fuel slot
  → Replace both with single "Recovery Dinner" slot at event_end
  → Tags: High Protein + Complex Carbs + Fast Carbs
  → Note: "Post-event dinner doubles as your recovery meal"
```

**Rule 3 — Double Event (two events same day)**
```
IF two events found for the same date
  → Add "Between Games Recovery + Refuel" slot between event_1_end and event_2_start
  → Increase calorie target by 15%
  → Add "Double Day" alert banner at top of day
  → Apply timing formulas to each event independently
  → Merge overlapping slots where window < 30 min
```

**Rule 4 — No Event (Rest Day)**
```
IF no event on calendar
  → Skip all timing formulas
  → Load static Rest Day template (fixed time windows)
  → No performance categories shown
```

### Step 4 — Build Final Slot List

After applying conflicts, return an ordered list of slot objects each containing:

```python
{
  "slot_name":      str,   # unique ID e.g. "pre-event-fuel"
  "display_label":  str,   # e.g. "Pre-Training Fuel"
  "eat_by_time":    str,   # e.g. "4:30 PM" — exact calculated time
  "time_note":      str,   # e.g. "3 hrs before training"
  "tags":           list,  # e.g. ["Complex Carbs", "Light Protein"]
  "icon":           str,   # emoji e.g. "⚡"
  "is_hydration":   bool,  # True = no recipe, informational only
  "is_merged":      bool,  # True = merged slot (e.g. Recovery Dinner)
  "note":           str,   # conflict note if applicable, else ""
  "recipe_category": str,  # maps to recipe DB category for picker
}
```

---

## Slot Definitions by Day Type

### Rest Day (static template — no event)

| Icon | Slot ID | Display Name | Eat By | Tags |
|---|---|---|---|---|
| 🍳 | `breakfast` | Breakfast | 8:30 AM | Complex Carbs · Protein · Healthy Fats |
| 🍎 | `mid-morning-snack` | Mid-Morning Snack | 11:00 AM | Quick Carbs · Light |
| 🥗 | `lunch` | Lunch | 1:30 PM | High Protein · Complex Carbs · Iron-Rich |
| 🥜 | `afternoon-snack` | Afternoon Snack | 4:00 PM | Protein · Healthy Fats |
| 🍽️ | `dinner` | Dinner | 7:00 PM | High Protein · Complex Carbs · Healthy Fats |
| 🌙 | `evening-recovery` | Evening Recovery / Pre-Bed Fueling | 9:30 PM | Casein Protein · Light |
| 💧 | `daily-hydration` | Daily Hydration | All day | — (hydration, informational) |

### Training / Practice / Strength Day (dynamic)

Fixed slots:
- Breakfast (7:00–8:30 AM)
- Mid-Morning Snack (10:00–11:00 AM)
- Lunch (12:00–1:30 PM)

Dynamic slots (calculated from event time):
- Pre-Training Fuel → `event_start − 3h`
- Power Snack → `event_start − 45min`
- During Practice Hydration → `event_start` to `event_end`

Post-event (branching on event end time):
- **If event ends ≤ 19:00:** Recovery Fuel (`event_end + 30min`) + Dinner (7:00–7:30 PM) + Night Fuel (21:00)
- **If event ends > 19:00:** Recovery Dinner merged slot (`event_end`) — replaces Recovery Fuel, Dinner, and Night Fuel

Always appended:
- Daily Hydration (informational)

### Game Day / Tournament Day (dynamic)

Fixed slots:
- Breakfast (7:00–8:30 AM)

Dynamic slots:
- Pre-Game Fuel → `event_start − 3h`
- Power Snack → `event_start − 45min`
- During Game Hydration → `event_start` to `event_end`
- Halftime Fueling → `event_start + 45min`

Post-event (same branching rule):
- **If event ends ≤ 19:00:** Recovery Fuel (`event_end + 30min`) + Dinner (7:00–7:30 PM) + Night Fuel (21:00)
- **If event ends > 19:00:** Recovery Dinner merged slot (`event_end`)

Always appended:
- Daily Hydration (informational)

---

## Backend Changes

### New service function — `api/services/meal_timing.py`

New function (replaces static `SLOTS_BY_EVENT` dict):

```python
def compute_meal_slots(event_type: str, start_time: str | None, duration_minutes: int | None) -> list[dict]:
    """
    Given an event type and start time, return an ordered list of meal slot
    objects with calculated eat_by_time, tags, and display metadata.
    Returns the Rest Day static template if event_type is None or "rest".
    """
```

This function encapsulates all 4 steps of the timing engine. `_build_week` in `meal_plans.py` calls this function instead of looking up `SLOTS_BY_EVENT`.

### Updated `_build_week` in `api/routes/meal_plans.py`

Pass `event.start_time` and `event.duration_minutes` to `compute_meal_slots()`. The API response already returns `display_label` and `recipe_category` per slot — add `eat_by_time`, `tags`, `icon`, `is_hydration`, `is_merged`, and `note` to the slot response.

### `SLOTS_BY_EVENT`, `SLOT_LABELS`, `SLOT_TO_CATEGORY` — removed

Replaced entirely by `compute_meal_slots()`. No static dictionaries.

---

## Frontend Changes — `frontend/src/MealPlannerScreen.jsx`

### New state

| State | Type | Purpose |
|---|---|---|
| `selectedDate` | `string` (ISO) | Currently viewed date |
| `weekStart` | `Date` | Monday of the loaded week (existing, kept) |
| `weekData` | `object` | Full 7-day data (existing, kept) |

### New frontend constants

```js
const DAY_HERO = {
  rest:       { gradient: ["#2d6a4f","#52b788"], emoji:"🌿", badge:"🌿 Rest Day",     title:"Recovery & Rebuild Day",          desc:"..." },
  practice:   { gradient: ["#b45309","#f59e0b"], emoji:"🏃", badge:"🏃 Training Day",  title:"Training Fuel Day",               desc:"..." },
  training:   { gradient: ["#b45309","#f59e0b"], emoji:"🏃", badge:"🏃 Training Day",  title:"Training Fuel Day",               desc:"..." },
  strength:   { gradient: ["#b45309","#f59e0b"], emoji:"🏋️", badge:"🏋️ Strength Day", title:"Training Fuel Day",               desc:"..." },
  game:       { gradient: ["#9a1a1a","#e05a4a"], emoji:"⚽", badge:"⚽ Game Day",       title:"Game Day — Perform & Recover",    desc:"..." },
  tournament: { gradient: ["#4a2a8a","#9a7ae8"], emoji:"🏆", badge:"🏆 Tournament",   title:"Tournament Day — Fuel to Compete", desc:"..." },
};
```

### New components

| Component | Replaces | Purpose |
|---|---|---|
| `DayHero` | — | Colour-coded hero banner with description + calorie bar |
| `TimelineSlot` | `SlotCard` | Vertical timeline dot + card with eat_by_time, tags, Add/Swap/Remove |
| `WeekDots` | — | 7-dot strip with event-type indicators and day-jump on tap |

### Removed from UI

- "Generate Week Plan" / "Generate Day Plan" button and all generate logic
- "Mark as Eaten" (`onLogEaten`, `logged` state display)
- `overwriteWarning` state and warning UI
- `aiReasoning` state and reasoning box
- Horizontal `weekGrid` div (replaced by single-day timeline)
- `DayColumn` component (replaced by full-width single-day layout)

### Day navigation

```js
function goToPrevDay() {
  const prev = addDays(parseISO(selectedDate), -1);
  if (prev < weekStart) setWeekStart(getMondayOf(prev));
  setSelectedDate(toISO(prev));
}
function goToNextDay() {
  const next = addDays(parseISO(selectedDate), 1);
  if (next >= addDays(weekStart, 7)) setWeekStart(getMondayOf(next));
  setSelectedDate(toISO(next));
}
```

---

## Nutrition Tag Colour Scheme

| Tag | Background | Text | Border |
|---|---|---|---|
| Complex Carbs / Quick Carbs | `#fff8e7` | `#b8720a` | `#f4d3a0` |
| Protein / High Protein / Casein | `#eff8ff` | `#1a6ab8` | `#b8d9f4` |
| Healthy Fats | `#fdf5ff` | `#7a3ab8` | `#ddbef4` |
| Light | `#f4fdf7` | `#2a7a4a` | `#a8e4bc` |
| Iron-Rich | `#fff0f0` | `#b83a3a` | `#f4a8a8` |
| Fast Carbs | `#fff8e7` | `#b8720a` | `#f4d3a0` |
| Electrolytes | `#e8f4ff` | `#1a6aa8` | `#a0cce8` |

---

## Out of Scope

- Week View (greyed-out toggle; built in a later iteration)
- "Mark as Eaten" / meal logging (removed from planner; lives in Today screen)
- AI plan generation (Generate button removed)
- Existing `meal_plans` rows with old slot names — orphaned silently, no migration needed
- Location-based slot adjustments (travel time to venue)
