"""
api/services/window_engine_v2.py
Deploy to: fuelup-youth backend repo at api/services/window_engine_v2.py

Single shared computation layer for all window generation consumers:
  - Today page  (today_service.py)
  - Meal Plan   (window_templates.py)
  - Notifications (generator_notifications.py via notification_gap_filter.py)
  - Fueling Essentials / Reports (via same API response shape)

Feature flag: EVENT_RELATIVE_WINDOWS env var.
Old window_templates.py / window engine is NOT deleted until Phase 4 cutover.

Pure computation — no DB I/O.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Optional

# ── Feature flag ──────────────────────────────────────────────────────────────

def event_relative_windows_enabled() -> bool:
    return os.environ.get("EVENT_RELATIVE_WINDOWS", "false").lower() == "true"

# ── Constants ──────────────────────────────────────────────────────────────────

DISPLAY_FLOOR = time(6, 30)        # Hard rule: no window open_time before this — ever
GAP_LARGE_H   = 3.5                # > 3h30m → two separate full cycles
GAP_MEDIUM_H  = 1.0                # ≥ 1h AND ≤ 3h30m → merged "Recover & refuel"
                                    # < 1h → single "Quick refuel between sessions"

FUEL_DURING_MIN_MIN = 90           # Session must be ≥ 90 min to show Fuel During nudge

BETWEEN_WINDOW_MIN_GAP_MIN = 15    # Min gap (minutes) between two tappable windows
MAX_TAPPABLE_WINDOWS       = 6

EVERYDAY_DINNER_CUTOFF      = time(17, 30)  # Dinner only if ALL events end before this
SECOND_RECOVERY_CUTOFF      = time(22, 30)  # Recovery Meal skipped if it would open at/after 10:30 PM

# Verbatim teaching message — do NOT change wording without spec approval
EARLY_MORNING_MESSAGE = (
    "Early game today! There's no time for a big meal before. "
    "Have a light snack now (like a banana or toast), then eat a "
    "proper breakfast right after you play. Pro athletes do this too."
)

GAME_TYPES     = {"game", "tournament"}
# "conditioning" (Gym/Conditioning) is offered in the mobile picker. v2 is LIVE
# in prod (EVENT_RELATIVE_WINDOWS=true), so map it explicitly as a training-type
# day by design rather than relying on the non-game fallthrough.
TRAINING_TYPES = {"practice", "training", "strength", "conditioning"}
ALL_TYPES      = GAME_TYPES | TRAINING_TYPES

DEFAULT_DURATION_MIN: dict[str, int] = {
    "game":         90,   # live-verified: old engine uses 90min when duration_hours is null
    "tournament":   90,
    "practice":     90,
    "training":     90,
    "strength":     60,
    "conditioning": 60,   # gym session — same default as strength
    "rest":          0,
}

EVERYDAY_DEFS = [
    {
        "key":          "everyday_breakfast",
        "label":        "Breakfast",
        "open":         time(7, 0),
        "close":        time(9, 0),
        "macro_focus":  "Balanced",
        "category_key": "balanced",
    },
    {
        "key":          "everyday_lunch",
        "label":        "Lunch",
        "open":         time(12, 0),
        "close":        time(13, 30),
        "macro_focus":  "Balanced",
        "category_key": "balanced",
    },
    {
        "key":          "everyday_snack",
        "label":        "Afternoon Snack",
        "open":         time(15, 0),
        "close":        time(16, 30),
        "macro_focus":  "Balanced",
        "category_key": "balanced",
    },
    {
        "key":          "everyday_dinner",
        "label":        "Dinner",
        "open":         time(18, 30),
        "close":        time(20, 0),
        "macro_focus":  "Balanced",
        "category_key": "balanced",
    },
]

# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class Event:
    id: int
    athlete_id: int
    event_type: str            # "game"|"tournament"|"practice"|"training"|"strength"|"rest"
    event_date: str            # YYYY-MM-DD
    start_time: str            # HH:MM 24h
    duration_hours: Optional[float] = None

@dataclass
class WindowCard:
    window_key:     str            # e.g. "pre_event_meal_1", "refuel_ready_1_2"
    label:          str            # display label
    category:       str            # "fuel_before"|"fuel_after"|"everyday"|"quick_snack"|
                                   # "between_games"|"refuel_ready"
    category_key:   str            # "carb"|"balanced"|"recovery"|"hydrate"
    category_label: str
    open_time:      str            # "HH:MM" 24h — NEVER before 06:30
    close_time:     str            # "HH:MM" 24h
    time_display:   str            # "H:MM AM – H:MM PM"
    sort_time:      str            # "HH:MM" 24h for ordering
    macro_focus:    str
    window_type:    Optional[str]  # "pre_fuel"|"recovery"|None  (for Today page compat.)
    priority:       bool           # True = primary recovery (always emphasised)
    is_tappable:    bool           # False only for fuel_during nudges
    why:            str
    event_index:    Optional[int] = None    # 1-based event index for multi-event days

@dataclass
class DayWindowResult:
    day_type:              str
    windows:               list[WindowCard]
    early_morning_message: Optional[str]   # first event that triggered early rule
    events_processed:      int

# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_start(event: Event) -> datetime:
    return datetime.strptime(f"{event.event_date} {event.start_time}", "%Y-%m-%d %H:%M")

def _event_end(event: Event, start: datetime) -> datetime:
    if event.duration_hours:   # falsy covers both None and 0.0 (missing end time)
        return start + timedelta(hours=event.duration_hours)
    return start + timedelta(minutes=DEFAULT_DURATION_MIN.get(event.event_type, 90))

def _floor(dt: datetime) -> datetime:
    """Clamp to 06:30 display floor."""
    floor_dt = dt.replace(hour=DISPLAY_FLOOR.hour, minute=DISPLAY_FLOOR.minute,
                          second=0, microsecond=0)
    return max(dt, floor_dt)

def _hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")

def _display_time(dt: datetime) -> str:
    h = dt.hour % 12 or 12
    period = "AM" if dt.hour < 12 else "PM"
    return f"{h}:{dt.minute:02d} {period}"

def _range(o: datetime, c: datetime) -> str:
    return f"{_display_time(o)} – {_display_time(c)}"

def _early_morning(start: datetime) -> bool:
    """Pre-event open time (start − 3h) would be before 06:30."""
    return (start - timedelta(hours=3)).time() < DISPLAY_FLOOR

def _long_session(start: datetime, end: datetime) -> bool:
    return (end - start).total_seconds() / 60 >= FUEL_DURING_MIN_MIN

def _suf(idx: int, total: int) -> str:
    return f"_{idx}" if total > 1 else ""

def _minutes_between(a: str, b: str) -> float:
    """Signed minutes from HH:MM string a to HH:MM string b."""
    ah, am = int(a[:2]), int(a[3:])
    bh, bm = int(b[:2]), int(b[3:])
    return (bh * 60 + bm) - (ah * 60 + am)

# ── Per-event cycle ────────────────────────────────────────────────────────────

def _event_cycle(
    event: Event,
    start: datetime,
    end: datetime,
    idx: int,           # 1-based event index
    total: int,
    include_pre:    bool = True,
    include_recovery: bool = True,
) -> tuple[list[WindowCard], Optional[str]]:
    """
    Generate the raw window cycle for one event.
    Returns (cards, early_morning_message_or_None).
    """
    cards: list[WindowCard] = []
    early_msg: Optional[str] = None
    s = _suf(idx, total)
    is_game = event.event_type in GAME_TYPES

    # ── Pre-event ──────────────────────────────────────────────────────────────
    if include_pre:
        pre_open_raw  = start - timedelta(hours=3)
        pre_close_raw = start - timedelta(hours=2, minutes=45)

        if _early_morning(start):
            # Per-event early-morning rule — evaluated independently for each event
            early_msg = EARLY_MORNING_MESSAGE
            snack_open  = _floor(start - timedelta(minutes=60))
            snack_close = _floor(start - timedelta(minutes=30))
            if snack_close <= snack_open:
                snack_close = snack_open + timedelta(minutes=30)
            cards.append(WindowCard(
                window_key     = f"quick_morning_snack{s}",
                label          = "Quick Morning Snack",
                category       = "quick_snack",
                category_key   = "carb",
                category_label = "Light Carbs",
                open_time      = _hhmm(snack_open),
                close_time     = _hhmm(snack_close),
                time_display   = _range(snack_open, snack_close),
                sort_time      = _hhmm(snack_open),
                macro_focus    = "Light Carbs",
                window_type    = "pre_fuel",
                priority       = False,
                is_tappable    = True,
                why = (
                    "Early start — a light snack now gives you quick energy without a "
                    "heavy stomach before the game."
                ),
                event_index = idx,
            ))
        else:
            pre_open  = _floor(pre_open_raw)
            pre_close = _floor(pre_close_raw)
            if pre_close <= pre_open:
                pre_close = pre_open + timedelta(minutes=30)
            cards.append(WindowCard(
                window_key     = f"pre_event_meal{s}",
                label          = "Fuel Before",
                category       = "fuel_before",
                category_key   = "carb",
                category_label = "PRE-EVENT",
                open_time      = _hhmm(pre_open),
                close_time     = _hhmm(pre_close),
                time_display   = _range(pre_open, pre_close),
                sort_time      = _hhmm(pre_open),
                macro_focus    = "Carb-Forward",
                window_type    = "pre_fuel",
                priority       = False,
                is_tappable    = True,
                why = (
                    "A full meal 3-4 hours before gives your body time to digest "
                    "and top up your fuel stores."
                ),
                event_index = idx,
            ))
            # Top-Up Snack: S−60 → S−30 — every non-early-morning event.
            # Generated here so gap-merge can suppress it via suppress_pre
            # using the same flag that suppresses pre_event_meal.
            topup_open  = start - timedelta(minutes=60)
            topup_close = start - timedelta(minutes=30)
            cards.append(WindowCard(
                window_key     = f"top_up_snack{s}",
                label          = "Top-Up Snack",
                category       = "quick_snack",
                category_key   = "carb",
                category_label = "PRE-EVENT",
                open_time      = _hhmm(topup_open),
                close_time     = _hhmm(topup_close),
                time_display   = _range(topup_open, topup_close),
                sort_time      = _hhmm(topup_open),
                macro_focus    = "Light Carbs",
                window_type    = "pre_fuel",
                priority       = False,
                is_tappable    = True,
                why = (
                    "A small carb snack 30–60 min before keeps glycogen topped up "
                    "without sitting heavy going into the session."
                ),
                event_index = idx,
            ))

    # ── Fuel During — NUDGE ONLY, never a confirmation tap ────────────────────
    # Fires for any session ≥90 min — games AND long trainings. Label and copy
    # are game-aware; the underlying hydration need is duration-based, not type-based.
    if _long_session(start, end):
        mid = start + (end - start) / 2
        during_open  = mid - timedelta(minutes=5)
        during_close = mid + timedelta(minutes=5)
        cards.append(WindowCard(
            window_key     = f"fuel_during{s}",
            label          = "Halftime Fuel" if is_game else "Hydration Break",
            category       = "fuel_during",
            category_key   = "hydrate",
            category_label = "Fuel During",
            open_time      = _hhmm(during_open),
            close_time     = _hhmm(during_close),
            time_display   = _range(during_open, during_close),
            sort_time      = _hhmm(during_open),
            macro_focus    = "Fast Carbs + Fluid",
            window_type    = None,
            priority       = False,
            is_tappable    = False,    # NEVER a confirmation tap
            why = (
                "Keeping fuel and fluid up at halftime sustains energy to the final whistle."
                if is_game else
                "Long training sessions deplete glycogen and fluid just like games do. "
                "A quick carb + hydration break mid-session keeps intensity up through the end."
            ),
            event_index = idx,
        ))

    # ── Fuel After — recovery ─────────────────────────────────────────────────
    if include_recovery:
        # Primary recovery snack — always shown, no cutoff (priority=True)
        cards.append(WindowCard(
            window_key     = f"fuel_after_primary{s}",
            label          = "Recharge Snack",
            category       = "fuel_after",
            category_key   = "recovery",
            category_label = "POST-EVENT",
            open_time      = _hhmm(end),
            close_time     = _hhmm(end + timedelta(minutes=30)),
            time_display   = _range(end, end + timedelta(minutes=30)),
            sort_time      = _hhmm(end),
            macro_focus    = "Protein-Forward",
            window_type    = "recovery",
            priority       = True,
            is_tappable    = True,
            why = (
                "Muscles are most receptive to protein in the first 30 minutes after "
                "activity — something like chocolate milk gets recovery started fast."
            ),
            event_index = idx,
        ))
        if is_game and _early_morning(start):
            # Early game: same structural role as Recovery Meal — the substantial post-event
            # meal that stands in for lunch. Category is fuel_after so the cap treats it
            # identically to fuel_after_second. Key stays proper_breakfast_after so
            # has_recovery_meal stays False (preserves dinner on single early-game days).
            cards.append(WindowCard(
                window_key     = f"proper_breakfast_after{s}",
                label          = "Rebuild Breakfast",
                category       = "fuel_after",
                category_key   = "recovery",
                category_label = "POST-EVENT",
                open_time      = _hhmm(end + timedelta(minutes=30)),
                close_time     = _hhmm(end + timedelta(minutes=90)),
                time_display   = _range(end + timedelta(minutes=30), end + timedelta(minutes=90)),
                sort_time      = _hhmm(end + timedelta(minutes=30)),
                macro_focus    = "Protein + Carbs",
                window_type    = None,
                priority       = False,
                is_tappable    = True,
                why = (
                    "You skipped the full pre-game meal to protect your stomach. "
                    "Now eat a proper balanced breakfast — your body is primed to absorb it."
                ),
                event_index = idx,
            ))
        else:
            # Recovery Meal — substantial dinner-replacement, E+1h to E+2h.
            # Suppressed if it would open at/after SECOND_RECOVERY_CUTOFF (22:30),
            # which also prevents everyday dinner from being explicitly suppressed
            # (has_recovery_meal stays False when this card isn't generated).
            second_open  = end + timedelta(hours=1)
            second_close = end + timedelta(hours=2)
            # Suppress the second recovery meal at/after the 22:30 cutoff — INCLUDING
            # when it wraps past midnight after a late-evening event. Comparing .time()
            # alone wrapped 00:30 back under 22:30 and wrongly kept a ~1 AM "Rebuild Meal".
            if second_open.date() == start.date() and second_open.time() < SECOND_RECOVERY_CUTOFF:
                cards.append(WindowCard(
                    window_key     = f"fuel_after_second{s}",
                    label          = "Rebuild Meal",
                    category       = "fuel_after",
                    category_key   = "recovery",
                    category_label = "POST-EVENT",
                    open_time      = _hhmm(second_open),
                    close_time     = _hhmm(second_close),
                    time_display   = _range(second_open, second_close),
                    sort_time      = _hhmm(second_open),
                    macro_focus    = "Protein + Carbs",
                    window_type    = "recovery",
                    priority       = False,
                    is_tappable    = True,
                    why = (
                        "A full recovery meal 1–2 hours after activity replenishes glycogen "
                        "and continues muscle repair — this replaces dinner on event days."
                    ),
                    event_index = idx,
                ))

    return cards, early_msg

# ── Gap merge ─────────────────────────────────────────────────────────────────

def _apply_gap_merge(
    raw_cycles: list[list[WindowCard]],
    event_times: list[tuple[datetime, datetime]],  # (start, end) per event (0-based)
    total: int,
) -> list[WindowCard]:
    """
    Apply pairwise gap-tier merge rules across all events.
    Merges happen in place: removes suppressed windows from cycles,
    inserts merged/quick-refuel cards after A's cycle.
    """
    # suppress flags (0-based event index)
    suppress_recovery = [False] * total   # suppress both primary AND second recovery
    suppress_pre      = [False] * total   # suppress pre-event of this event

    merge_inserts: list[tuple[int, WindowCard]] = []  # (after-event-index, card)

    for i in range(total - 1):
        _, ta = event_times[i]      # end of event i
        sb, _ = event_times[i + 1]  # start of event i+1
        gap_h = (sb - ta).total_seconds() / 3600

        if gap_h > GAP_LARGE_H:
            pass  # Two full separate cycles; no suppression

        elif gap_h >= GAP_MEDIUM_H:
            # 1h–3h30m: ONE merged "Recover & refuel" card
            # Replaces A's full recovery cycle AND B's pre-event
            suppress_recovery[i] = True
            suppress_pre[i + 1]  = True
            merged_open  = ta
            merged_close = sb - timedelta(minutes=30)
            if merged_close <= merged_open:
                merged_close = merged_open + timedelta(minutes=20)
            merge_inserts.append((i, WindowCard(
                window_key     = f"refuel_ready_{i+1}_{i+2}",
                label          = "Recover & refuel for your next session",
                category       = "refuel_ready",
                category_key   = "recovery",
                category_label = "Refuel",
                open_time      = _hhmm(merged_open),
                close_time     = _hhmm(merged_close),
                time_display   = _range(merged_open, merged_close),
                sort_time      = _hhmm(merged_open),
                macro_focus    = "Carbs + Protein",
                window_type    = "recovery",
                priority       = False,
                is_tappable    = True,
                why = (
                    "After a session and before the next, this window refills fuel "
                    "stores and delivers protein to repair, while keeping digestion "
                    "comfortable for what comes next."
                ),
                event_index = i + 1,  # logically belongs to the gap between i+1 and i+2
            )))

        else:
            # < 1h: single "Quick refuel between sessions" card
            # Replaces A's full recovery AND B's pre-event
            suppress_recovery[i] = True
            suppress_pre[i + 1]  = True
            quick_open  = ta
            quick_close = min(ta + timedelta(minutes=20), sb - timedelta(minutes=5))
            if quick_close <= quick_open:
                quick_close = quick_open + timedelta(minutes=15)
            merge_inserts.append((i, WindowCard(
                window_key     = f"between_games_{i+1}_{i+2}",
                label          = "Quick refuel between sessions",
                category       = "between_games",
                category_key   = "carb",
                category_label = "Between Sessions",
                open_time      = _hhmm(quick_open),
                close_time     = _hhmm(quick_close),
                time_display   = _range(quick_open, quick_close),
                sort_time      = _hhmm(quick_open),
                macro_focus    = "Fast Carbs + Fluid",
                window_type    = "recovery",
                priority       = False,
                is_tappable    = True,
                why = (
                    "Back-to-back sessions — fast carbs and fluid keep you sharp for "
                    "round two."
                ),
                event_index = i + 1,
            )))

    # Rebuild window list applying suppressions
    result: list[WindowCard] = []
    for i, cycle in enumerate(raw_cycles):
        for w in cycle:
            if suppress_recovery[i] and w.window_key.startswith(
                (f"fuel_after_primary{_suf(i+1, total)}",
                 f"fuel_after_second{_suf(i+1, total)}",
                 f"proper_breakfast_after{_suf(i+1, total)}")
            ):
                continue
            if suppress_pre[i] and w.window_key.startswith(
                (f"pre_event_meal{_suf(i+1, total)}",
                 f"quick_morning_snack{_suf(i+1, total)}",
                 f"top_up_snack{_suf(i+1, total)}")
            ):
                continue
            result.append(w)

        # Insert any merge card that belongs after event i
        for (after_idx, card) in merge_inserts:
            if after_idx == i:
                result.append(card)

    return result

# ── Everyday windows ───────────────────────────────────────────────────────────

def _everyday_windows(
    event_times: list[tuple[datetime, datetime]],
    event_cards: list[WindowCard],
    event_date: str,
    has_game: bool = False,
    has_early_game: bool = False,
) -> list[WindowCard]:
    """Return clock-anchored everyday windows that fill genuine gaps."""
    if not event_times:
        # Rest day — return all everyday windows
        ref = datetime.strptime(event_date, "%Y-%m-%d")
        return [_make_everyday(d, ref) for d in EVERYDAY_DEFS]

    ref = event_times[0][0].replace(hour=0, minute=0, second=0, microsecond=0)
    last_event_end = max(end for _, end in event_times)

    tappable_ranges = [
        (w.open_time, w.close_time) for w in event_cards if w.is_tappable
    ]
    # Actual event blocks (start → end) in HH:MM strings — everyday meals must
    # not overlap the event itself, not just the fueling cards around it.
    event_blocks = [
        (start.strftime("%H:%M"), end.strftime("%H:%M"))
        for start, end in event_times
    ]

    # Recovery Meal (fuel_after_second) acts as the dinner replacement on event days.
    # Suppress everyday_dinner whenever a Recovery Meal card was actually generated —
    # i.e., it wasn't killed by SECOND_RECOVERY_CUTOFF. This is the primary dinner
    # suppression mechanism; the cutoff check below handles very-late events only.
    has_recovery_meal = any(
        w.window_key.startswith("fuel_after_second") for w in event_cards
    )

    result: list[WindowCard] = []
    for d in EVERYDAY_DEFS:
        # Dinner suppression — two independent checks, either fires independently:
        # 1. Event ends too late for dinner to be sensible (existing cutoff).
        # 2. A Recovery Meal was generated that stands in for dinner.
        if d["key"] == "everyday_dinner" and last_event_end.time() >= EVERYDAY_DINNER_CUTOFF:
            continue
        if d["key"] == "everyday_dinner" and has_recovery_meal:
            continue
        # Live-verified: old engine never generates everyday_snack on game days.
        # The second recovery touch already covers that nutritional window.
        if d["key"] == "everyday_snack" and has_game:
            continue
        # On early-game days proper_breakfast_after serves the breakfast slot.
        # Generating everyday_breakfast too creates a confusing duplicate at 07:00.
        if d["key"] == "everyday_breakfast" and has_early_game:
            continue

        d_open  = d["open"].strftime("%H:%M")
        d_close = d["close"].strftime("%H:%M")

        # Suppress if the everyday window overlaps a tappable fueling card
        # (range intersection + 15-min proximity gap).
        fueling_conflict = any(
            (d_open < ex_close and d_close > ex_open)
            or abs(_minutes_between(d_open, ex_open)) < BETWEEN_WINDOW_MIN_GAP_MIN
            for ex_open, ex_close in tappable_ranges
        )
        # Suppress if the everyday window physically overlaps the event itself
        # (pure range intersection — a meal card must not sit inside an event block).
        event_conflict = any(
            d_open < ev_close and d_close > ev_open
            for ev_open, ev_close in event_blocks
        )
        if not fueling_conflict and not event_conflict:
            result.append(_make_everyday(d, ref))

    return result

def _make_everyday(d: dict, ref: datetime) -> WindowCard:
    o = ref.replace(hour=d["open"].hour,  minute=d["open"].minute)
    c = ref.replace(hour=d["close"].hour, minute=d["close"].minute)
    return WindowCard(
        window_key     = d["key"],
        label          = d["label"],
        category       = "everyday",
        category_key   = d["category_key"],
        category_label = "Everyday",
        open_time      = _hhmm(o),
        close_time     = _hhmm(c),
        time_display   = _range(o, c),
        sort_time      = _hhmm(o),
        macro_focus    = d["macro_focus"],
        window_type    = None,
        priority       = False,
        is_tappable    = True,
        why            = "Consistent everyday meals keep energy levels stable throughout the day.",
        event_index    = None,
    )

# ── Cap and guardrails ─────────────────────────────────────────────────────────

def _apply_guardrails(cards: list[WindowCard]) -> list[WindowCard]:
    """
    1. Floor enforcement (display never before 06:30) — should already hold
    2. between_games/refuel_ready must be ≥ 20 min wide (else nudge-only)
    3. 15-min minimum gap between tappable windows (everyday dropped first)
    4. Cap at 6 tappable windows/day
    """
    sorted_cards = sorted(cards, key=lambda w: w.sort_time)

    # 1. Floor
    for w in sorted_cards:
        if w.is_tappable and w.open_time < "06:30":
            w.open_time  = "06:30"
            w.sort_time  = "06:30"

    # 2. Width check for merged cards
    for w in sorted_cards:
        if w.category in ("between_games", "refuel_ready") and w.is_tappable:
            gap = _minutes_between(w.open_time, w.close_time)
            if gap < 20:
                w.is_tappable = False

    # 3. 15-min gap dedup (everyday dropped first within conflicts)
    tappable  = [w for w in sorted_cards if w.is_tappable]
    nudges    = [w for w in sorted_cards if not w.is_tappable]

    deduped: list[WindowCard] = []
    for w in tappable:
        # proper_breakfast_after opens at E+30min; Recovery Snack opens at E — 30-min gap
        # clears the 15-min dedup threshold, so this bypass is now redundant. Kept as a
        # guard against future timing changes inadvertently creating a conflict.
        if "proper_breakfast_after" in w.window_key:
            deduped.append(w)
            continue
        drop = False
        to_remove: list[WindowCard] = []
        for kept in deduped:
            gap = abs(_minutes_between(w.sort_time, kept.sort_time))
            if gap < BETWEEN_WINDOW_MIN_GAP_MIN:
                if w.category == "everyday" and kept.category != "everyday":
                    drop = True
                    break
                elif kept.category == "everyday" and w.category != "everyday":
                    to_remove.append(kept)
                elif w.priority and not kept.priority:
                    to_remove.append(kept)
                else:
                    drop = True
                    break
        for r in to_remove:
            deduped.remove(r)
        if not drop:
            deduped.append(w)

    # 4. Cap at 5
    if len(deduped) > MAX_TAPPABLE_WINDOWS:
        deduped = _cap_6(deduped)

    return sorted(deduped + nudges, key=lambda w: w.sort_time)

def _cap_6(windows: list[WindowCard]) -> list[WindowCard]:
    """
    Drop windows to reach MAX_TAPPABLE_WINDOWS (currently 6).

    Keep order (0 = never drop first):
      0  fuel_after_primary (priority=True) — Recovery Snack, never dropped
      1  fuel_before / quick_snack — pre-event meals (not top-up)
      2  refuel_ready / between_games — merged gap cards
      3  fuel_after — Recovery Meal + Recovery Breakfast (same tier; substantial meals)
      4  top_up_snack — S−60 snack; droppable on busy days when meals are all present
      5  everyday_breakfast
      6  everyday_lunch
      7  (unused)
      8  (unused)
      9  everyday_snack — shed first
    Note: everyday_dinner is explicitly suppressed before the cap runs when a
    Recovery Meal exists, so it rarely reaches the cap. Rank 3 (above top-up and
    everyday meals) handles any edge case where suppression didn't fire.
    """
    def keep_rank(w: WindowCard) -> int:
        if w.priority:                                             return 0
        if w.category in ("fuel_before", "quick_snack"):
            if "top_up_snack" in w.window_key:                    return 4
            return 1
        if w.category in ("refuel_ready", "between_games"):       return 2
        if w.category == "fuel_after":                            return 3  # Recovery Meal + Recovery Breakfast
        if w.category == "everyday":
            if "snack" in w.window_key:                           return 9
            if "dinner" in w.window_key:                          return 8  # belt-and-suspenders: explicit suppression
            if "lunch" in w.window_key:                           return 6  # is the real mechanism; this is fallback only
            return 5  # everyday_breakfast
        return 9

    by_keep = sorted(windows, key=lambda w: (keep_rank(w), w.sort_time))
    kept = by_keep[:MAX_TAPPABLE_WINDOWS]
    return sorted(kept, key=lambda w: w.sort_time)

# ── Day type ───────────────────────────────────────────────────────────────────

def _day_type(events: list[Event], event_times: list[tuple[datetime, datetime]]) -> str:
    if not events:
        return "rest"

    game_count     = sum(1 for e in events if e.event_type in GAME_TYPES)
    training_count = sum(1 for e in events if e.event_type in TRAINING_TYPES)

    if game_count >= 2 or any(e.event_type == "tournament" for e in events):
        return "tournament"
    if len(events) >= 2:
        if training_count == len(events):
            return "double_training"
        # Mixed training + game: treat as double-event day, not tournament.
        # "tournament" is reserved for ≥ 2 games.
        return "double_training"

    ev = events[0]
    start, _ = event_times[0]
    start_h = start.hour + start.minute / 60

    if ev.event_type in GAME_TYPES:
        if _early_morning(start):
            return "early_game"
        if start_h >= 17:
            return "evening_event"
        if start_h >= 12:
            return "afternoon_game"
        return "morning_game"
    else:
        if start_h >= 17:
            return "practice_evening"
        return "practice_morning"

# ── Public API ────────────────────────────────────────────────────────────────

def generate_windows_v2(
    events: list[Event],
    event_date: str,
) -> DayWindowResult:
    """
    Generate all fuel windows for a day.

    Called from:
      - today_service.py  (Today page)
      - window_templates.py  (Meal Plan)
      - notification_gap_filter.py  (notification timing)

    Returns DayWindowResult with windows sorted by sort_time and capped at 5.
    feature_flag check is the CALLER's responsibility so callers can fall back
    to the old engine when EVENT_RELATIVE_WINDOWS is not set.
    """
    if not events:
        # Rest day — only everyday windows
        ref = datetime.strptime(event_date, "%Y-%m-%d")
        everyday = [_make_everyday(d, ref) for d in EVERYDAY_DEFS]
        return DayWindowResult(
            day_type              = "rest",
            windows               = sorted(everyday, key=lambda w: w.sort_time),
            early_morning_message = None,
            events_processed      = 0,
        )

    events = sorted(events, key=lambda e: e.start_time)
    n = len(events)

    # Compute (start, end) for each event
    event_times: list[tuple[datetime, datetime]] = []
    for ev in events:
        s = _parse_start(ev)
        e = _event_end(ev, s)
        event_times.append((s, e))

    # Generate raw per-event cycles
    raw_cycles: list[list[WindowCard]] = []
    early_message: Optional[str] = None
    for i, (ev, (s, e)) in enumerate(zip(events, event_times)):
        cycle, msg = _event_cycle(ev, s, e, idx=i + 1, total=n)
        raw_cycles.append(cycle)
        if msg and not early_message:
            early_message = msg

    # Apply gap-tier merge rules
    merged_cards = _apply_gap_merge(raw_cycles, event_times, n)

    # Add everyday windows
    has_game = any(ev.event_type in GAME_TYPES for ev in events)
    has_early_game = any(
        ev.event_type in GAME_TYPES and _early_morning(s)
        for ev, (s, _) in zip(events, event_times)
    )
    everyday = _everyday_windows(
        event_times, merged_cards, event_date,
        has_game=has_game, has_early_game=has_early_game,
    )
    all_cards = merged_cards + everyday

    # Apply guardrails (floor, width, dedup, cap-5)
    final_cards = _apply_guardrails(all_cards)

    return DayWindowResult(
        day_type              = _day_type(events, event_times),
        windows               = final_cards,
        early_morning_message = early_message,
        events_processed      = n,
    )

# ── Helpers for callers ───────────────────────────────────────────────────────

def window_result_to_api_shape(result: DayWindowResult) -> dict:
    """
    Convert DayWindowResult to the existing API response shape for
    GET /api/athletes/:id/meal-plan?date=YYYY-MM-DD.
    Drop fuel_during nudges from the window list (they are timing signals only).
    """
    return {
        "day_type":              result.day_type,
        "early_morning_message": result.early_morning_message,
        "windows": [
            {
                "window_key":     w.window_key,
                "label":          w.label,
                "category":       w.category,
                "category_key":   w.category_key,
                "category_label": w.category_label,
                "time_display":   w.time_display,
                "sort_time":      w.sort_time,
                "macro_focus":    w.macro_focus,
                "why":            w.why,
                "items":          [],     # filled by caller from meal_plan_selections
                "ideas":          [],     # filled by caller from ideas service
            }
            for w in result.windows
            if w.category != "fuel_during"   # nudges never in window list
        ],
    }

def window_result_to_today_shape(result: DayWindowResult) -> list[dict]:
    """
    Convert DayWindowResult to the slot list shape for
    GET /api/athletes/:id/today.
    Maps category → window_type for Today page compat.
    """
    _wtype = {
        "fuel_before":   "pre_fuel",
        "quick_snack":   "pre_fuel",
        "fuel_after":    "recovery",
        "refuel_ready":  "recovery",
        "between_games": "recovery",
        "everyday":       None,
        "fuel_during":    None,
    }
    return [
        {
            "slot_name":     w.window_key,
            "display_label": w.label,
            "open_time":     w.open_time,
            "close_time":    w.close_time,
            "eat_by_time":   w.time_display,
            "macro_focus":   w.macro_focus,
            "window_type":   _wtype.get(w.category),
            "logged":        False,   # filled by caller from window_logs
            "status":        "upcoming",  # filled by today_service assign_window_status
        }
        for w in result.windows
        if w.is_tappable
    ]

def get_event_window_times(result: DayWindowResult) -> list[dict]:
    """
    Return event-relative window timing for the notification generator.
    fuel_during nudges are included here so the notification system can
    compute halftime reminder times.
    """
    return [
        {
            "window_key":  w.window_key,
            "category":    w.category,
            "open_time":   w.open_time,
            "close_time":  w.close_time,
            "sort_time":   w.sort_time,
            "window_type": w.window_type,
            "is_tappable": w.is_tappable,
            "priority":    w.priority,
        }
        for w in result.windows
    ]
