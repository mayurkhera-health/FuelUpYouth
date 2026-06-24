"""
Fuel Gauge tests — T1 (calculation), T2 (split), T3 (payload), T4 (regression).

Coefficients are PENDING_CLINICAL placeholders, so calculation tests assert
STRUCTURE, MONOTONICITY, and the architecture guarantees (D1/D4/D5/D6, T6/T7) —
never exact clinical magnitudes. The one hard-number guarantee is the rest-day
Blueprint consistency (T7): rest-day targets must equal Blueprint exactly.
"""

import json
import sqlite3

import pytest

from api.services import fuel_gauge as fg, fueling_targets as ft
from api.services.nutrition_calc import calc_daily_targets
from api.services.today_service import (
    build_today_view,
    record_window_capture,
    remove_window_capture,
    _ensure_window_logs_table,
)


# ── fixtures / helpers ───────────────────────────────────────────────────────
def _athlete(weight_lbs=110, age=14, gender="Girl", level="competitive_club",
             season_phase="in_season"):
    return dict(
        id=1, first_name="Mia", sport="soccer", weight_lbs=weight_lbs,
        height_ft=5, height_in=4.0, gender=gender, age=age,
        position="Midfielder", competition_level=level, sweat_profile=None,
        season_phase=season_phase,
    )


def _event(event_type="practice", intensity="medium", duration=1.5):
    return dict(event_type=event_type, intensity=intensity, duration_hours=duration,
                city=None, latitude=None, longitude=None)


MILD = dict(temp_f=70, humidity=50)
HOT = dict(temp_f=96, humidity=85)
NUTRIENTS = ("protein_g", "carbs_g", "fluids_ml", "sodium_mg", "calcium_mg")


def _today_conn(athlete: dict, events: list[tuple] = ()):
    """In-memory DB with the full set of tables build_today_view + get_streak read.
    `events` is a list of (event_date, event_type, intensity, start_time, duration)."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _ensure_window_logs_table(conn)
    conn.execute("""
        CREATE TABLE meal_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, athlete_id INTEGER NOT NULL,
            plan_date TEXT NOT NULL, slot_name TEXT NOT NULL, logged INTEGER DEFAULT 0,
            UNIQUE(athlete_id, plan_date, slot_name))
    """)
    conn.execute("""
        CREATE TABLE athletes (
            id INTEGER PRIMARY KEY, first_name TEXT, sport TEXT, gender TEXT, age INTEGER,
            weight_lbs REAL, height_ft INTEGER, height_in REAL, position TEXT,
            competition_level TEXT, sweat_profile TEXT, season_phase TEXT)
    """)
    conn.execute("""
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, athlete_id INTEGER NOT NULL,
            event_name TEXT, event_type TEXT, event_date TEXT, start_time TEXT,
            duration_hours REAL, intensity TEXT, city TEXT, latitude REAL, longitude REAL)
    """)
    conn.execute("CREATE TABLE confirmations (athlete_id INTEGER, log_date TEXT)")
    conn.execute("CREATE TABLE report_config (key TEXT, value TEXT)")
    cols = ",".join(athlete.keys())
    conn.execute(f"INSERT INTO athletes ({cols}) VALUES ({','.join('?' * len(athlete))})",
                 tuple(athlete.values()))
    for (d, et, inten, st, dur) in events:
        conn.execute(
            "INSERT INTO events (athlete_id, event_name, event_type, event_date, start_time, "
            "duration_hours, intensity) VALUES (?,?,?,?,?,?,?)",
            (athlete["id"], et.title(), et, d, st, dur, inten),
        )
    conn.commit()
    return conn


@pytest.fixture
def live_v2(monkeypatch):
    """Mirror production: v2 window engine on."""
    monkeypatch.setenv("EVENT_RELATIVE_WINDOWS", "true")


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("FUEL_GAUGE_ENABLED", "true")


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setenv("FUEL_GAUGE_ENABLED", "false")


# ═══════════════════════════════════════════════════════════════════════════
# T1 — CALCULATION UNIT TESTS (pure functions; no DB)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("profile", [
    _athlete(weight_lbs=88, age=13, gender="Girl"),
    _athlete(weight_lbs=132, age=16, gender="Boy", level="elite_club"),
    _athlete(weight_lbs=154, age=17, gender="Boy", level="recreational"),
])
def test_rest_day_delegates_to_blueprint_exactly(profile):
    """T7/D1: rest-day targets MUST equal what Blueprint computes for the same
    athlete (reduced to a single value per D2). Not an approximation."""
    base = calc_daily_targets(profile, "rest")
    rest = fg.compute_rest_day_targets(profile)
    assert rest["protein_g"] == round(ft.reduce_range(base["protein_g_min"], base["protein_g_max"]), 1)
    assert rest["carbs_g"] == int(round(ft.reduce_range(base["carbs_g_min"], base["carbs_g_max"])))
    assert rest["fluids_ml"] == int(round(
        ft.reduce_range(base["hydration_oz_min"], base["hydration_oz_max"]) * ft.OZ_TO_ML))
    assert rest["calcium_mg"] == base["calcium_mg"]


def test_rest_day_sodium_is_none():
    """D4: Blueprint computes no sodium → rest-day sodium is None, not fabricated."""
    assert fg.compute_rest_day_targets(_athlete())["sodium_mg"] is None


def test_event_day_has_all_five_metrics():
    t = fg.compute_event_day_targets(_athlete(), [_event("game")], "in_season", MILD)
    assert set(t.keys()) == set(NUTRIENTS)
    assert t["sodium_mg"] is not None and t["sodium_mg"] > 0


def test_carb_monotonicity_practice_game_tournament():
    """Training-load tiers: carbs game > practice, tournament > game (same intensity)."""
    a = _athlete()
    p = fg.compute_event_day_targets(a, [_event("practice", "medium")], "in_season", MILD)
    g = fg.compute_event_day_targets(a, [_event("game", "medium")], "in_season", MILD)
    t = fg.compute_event_day_targets(a, [_event("tournament", "medium")], "in_season", MILD)
    assert p["carbs_g"] < g["carbs_g"] < t["carbs_g"]


def test_body_weight_scaling_is_proportional():
    """50kg vs 70kg → protein scales ~proportionally (validates per-kg model)."""
    small = fg.compute_event_day_targets(_athlete(weight_lbs=110), [_event("game")], "in_season", MILD)
    large = fg.compute_event_day_targets(_athlete(weight_lbs=154), [_event("game")], "in_season", MILD)
    ratio = large["protein_g"] / small["protein_g"]
    assert 1.3 < ratio < 1.5  # 154/110 ≈ 1.40


def test_season_phase_shifts_carbs():
    """off_season carb multiplier < in_season (placeholder shape, D-config)."""
    a, ev = _athlete(), [_event("game")]
    in_s = fg.compute_event_day_targets(a, ev, "in_season", MILD)
    off = fg.compute_event_day_targets(a, ev, "off_season", MILD)
    assert off["carbs_g"] < in_s["carbs_g"]


def test_default_season_phase_applies_when_unset():
    a, ev = _athlete(), [_event("game")]
    assert fg.compute_event_day_targets(a, ev, None, MILD) == \
           fg.compute_event_day_targets(a, ev, "in_season", MILD)


def test_sodium_responds_to_weather():
    """Sodium higher on hot/high-sweat than mild (reuses calc_sweat_output)."""
    a, ev = _athlete(), [_event("game")]
    mild = fg.compute_event_day_targets(a, ev, "in_season", MILD)
    hot = fg.compute_event_day_targets(a, ev, "in_season", HOT)
    assert hot["sodium_mg"] > mild["sodium_mg"]


def test_sodium_higher_on_game_than_rest():
    game = fg.compute_event_day_targets(_athlete(), [_event("game")], "in_season", MILD)
    rest = fg.compute_rest_day_targets(_athlete())
    assert game["sodium_mg"] is not None and rest["sodium_mg"] is None
    assert game["sodium_mg"] > 0


def test_multiple_events_aggregate_without_double_counting_macros():
    """Two events same day: sweat-driven sodium ADDS up, but macros use the
    dominant event only (no macro double-count)."""
    a = _athlete()
    one = fg.compute_event_day_targets(a, [_event("game")], "in_season", MILD)
    two = fg.compute_event_day_targets(a, [_event("game"), _event("practice")], "in_season", MILD)
    # carbs driven by dominant (game) — not summed across both events
    assert two["carbs_g"] == one["carbs_g"]
    # sodium aggregates sweat across both events
    assert two["sodium_mg"] > one["sodium_mg"]


# ── D5: calcium is FLAT (the revised test — NOT age-differentiated) ──────────
def test_calcium_flat_across_age():
    """D5: calcium is 1300mg regardless of age (14 vs 17). The old
    '14yo vs 17yo differ' expectation was wrong per the audit."""
    young = fg.compute_event_day_targets(_athlete(age=14), [_event("game")], "in_season", MILD)
    old = fg.compute_event_day_targets(_athlete(age=17), [_event("game")], "in_season", MILD)
    assert young["calcium_mg"] == old["calcium_mg"] == 1300


def test_calcium_flat_across_load_and_intensity_and_day_type():
    """D5: calcium does NOT swing with training load, intensity, or day type."""
    a = _athlete()
    vals = {fg.compute_rest_day_targets(a)["calcium_mg"]}
    for et in ("practice", "game", "tournament"):
        for inten in ("low", "medium", "high"):
            vals.add(fg.compute_event_day_targets(a, [_event(et, inten)], "in_season", MILD)["calcium_mg"])
    assert vals == {1300}


# ═══════════════════════════════════════════════════════════════════════════
# T2 — CONTRIBUTION SPLIT TESTS (pure)
# ═══════════════════════════════════════════════════════════════════════════

def _mixed_windows():
    return [
        dict(slot_name="pre_event_meal", category_key="carb"),
        dict(slot_name="fuel_during", category_key="hydrate"),       # non-tappable → excluded
        dict(slot_name="fuel_after_primary", category_key="recovery"),
        dict(slot_name="everyday_breakfast", category_key="balanced"),
    ]


def test_split_sums_to_100_percent_per_nutrient():
    daily = fg.compute_event_day_targets(_athlete(), [_event("game")], "in_season", MILD)
    split = fg.split_targets_across_windows(daily, _mixed_windows())
    for n in NUTRIENTS:
        s = sum(w["contribution"][n] for w in split if w["contribution"][n] is not None)
        assert 98.0 <= (s / daily[n]) * 100 <= 102.0, (n, s, daily[n])


def test_split_excludes_hydrate_category():
    split = fg.split_targets_across_windows(
        fg.compute_event_day_targets(_athlete(), [_event("game")], "in_season", MILD),
        _mixed_windows(),
    )
    assert "fuel_during" not in {w["slot_name"] for w in split}
    assert all(w["category_key"] != "hydrate" for w in split)


def test_split_unknown_category_contributes_zero_and_logs(caplog):
    daily = fg.compute_event_day_targets(_athlete(), [_event("game")], "in_season", MILD)
    windows = [dict(slot_name="weird", category_key="mystery"),
               dict(slot_name="fuel_after_primary", category_key="recovery")]
    with caplog.at_level("WARNING"):
        split = fg.split_targets_across_windows(daily, windows)
    weird = next(w for w in split if w["slot_name"] == "weird")
    assert all(weird["contribution"][n] == 0 for n in ("protein_g", "carbs_g"))
    assert any("unknown" in r.message.lower() for r in caplog.records)


def test_split_rest_day_propagates_none_sodium():
    rest = fg.compute_rest_day_targets(_athlete())
    split = fg.split_targets_across_windows(rest, [
        dict(slot_name="everyday_breakfast", category_key="balanced"),
        dict(slot_name="everyday_dinner", category_key="balanced"),
    ])
    assert all(w["contribution"]["sodium_mg"] is None for w in split)


# ═══════════════════════════════════════════════════════════════════════════
# T1/T3 — target_source boundary + payload integration (via build_today_view)
# ═══════════════════════════════════════════════════════════════════════════
TODAY = "2026-06-23"
FUTURE = "2026-09-01"


def _view(athlete, events, today=TODAY):
    conn = _today_conn(athlete, events)
    try:
        return build_today_view(athlete["id"], conn, today=today)
    finally:
        conn.close()


def test_target_source_blueprint_when_zero_events_today(live_v2, flag_on):
    # has_schedule via a future event; no event today → rest/blueprint path
    view = _view(_athlete(), [(FUTURE, "game", "medium", "10:00", 1.5)])
    assert view["fuel_targets"]["target_source"] == "blueprint"
    assert view["fuel_targets"]["daily"]["sodium_mg"] is None  # D4


@pytest.mark.parametrize("etype", ["practice", "game", "tournament", "conditioning"])
def test_target_source_event_day_for_each_event_type(live_v2, flag_on, etype):
    """Boundary: exactly 1 event of each type → event_day path fires. (conditioning
    is not a modelled macro tier — it still routes event_day by event count.)"""
    view = _view(_athlete(), [(TODAY, etype, "medium", "10:00", 1.5)])
    assert view["fuel_targets"]["target_source"] == "event_day"


def test_fuel_targets_shape_when_flag_on(live_v2, flag_on):
    ft_block = _view(_athlete(), [(TODAY, "game", "medium", "10:00", 1.5)])["fuel_targets"]
    assert set(ft_block.keys()) == {"target_source", "daily", "confirmed_totals", "windows", "daily_met"}
    assert set(ft_block["daily"].keys()) == set(NUTRIENTS)
    assert isinstance(ft_block["daily_met"], bool)
    for w in ft_block["windows"]:
        assert set(w.keys()) == {"slot_name", "category_key", "contribution", "confirmed"}
        assert w["category_key"] in ("carb", "recovery", "balanced")  # never hydrate


def test_category_key_added_to_windows_when_flag_on(live_v2, flag_on):
    view = _view(_athlete(), [(TODAY, "game", "medium", "10:00", 1.5)])
    tappable = [w for w in view["windows"] if w.get("status") != "nudge"]
    assert any("category_key" in w for w in tappable)


def test_confirmed_totals_and_daily_met_track_confirmations(live_v2, flag_on):
    """confirmed_totals sums confirmed windows; daily_met true only when ALL
    creditable windows confirmed. Confirm via the real window_logs path."""
    athlete = _athlete()
    conn = _today_conn(athlete, [(TODAY, "game", "medium", "10:00", 1.5)])
    try:
        view = build_today_view(athlete["id"], conn, today=TODAY)
        windows = view["fuel_targets"]["windows"]
        assert windows, "expected creditable windows on a game day"

        # 0 confirmed → totals 0, not met
        assert view["fuel_targets"]["daily_met"] is False
        assert all(view["fuel_targets"]["confirmed_totals"][n] in (0, None) for n in NUTRIENTS)

        # confirm a SUBSET (the first window) → partial totals == that window's contribution
        first = windows[0]
        record_window_capture(athlete["id"], first["slot_name"], "text", "x",
                              None, None, conn, log_date=TODAY)
        v2 = build_today_view(athlete["id"], conn, today=TODAY)
        ct = v2["fuel_targets"]["confirmed_totals"]
        assert ct["carbs_g"] == first["contribution"]["carbs_g"]
        assert v2["fuel_targets"]["daily_met"] is False

        # confirm ALL → daily_met True and totals ≈ daily (within rounding)
        for w in windows:
            record_window_capture(athlete["id"], w["slot_name"], "text", "x",
                                  None, None, conn, log_date=TODAY)
        v3 = build_today_view(athlete["id"], conn, today=TODAY)
        assert v3["fuel_targets"]["daily_met"] is True
        daily = v3["fuel_targets"]["daily"]
        for n in ("protein_g", "carbs_g", "fluids_ml", "sodium_mg"):
            pct = v3["fuel_targets"]["confirmed_totals"][n] / daily[n] * 100
            assert 98.0 <= pct <= 102.0, (n, pct)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# T4 — REGRESSION (mandatory: Today is LIVE)
# ═══════════════════════════════════════════════════════════════════════════
PRODUCTION_TOP_KEYS = {
    "athlete", "today_event", "today_events", "day_type", "readiness",
    "windows", "next_game", "has_schedule", "readiness_grid", "streak",
}


def test_flag_off_payload_is_byte_identical_to_production(live_v2, flag_off):
    """Snapshot/contract: flag OFF → no new top-level keys, no fuel_targets, no
    category_key anywhere. This is THE additive guarantee."""
    view = _view(_athlete(), [(TODAY, "game", "medium", "10:00", 1.5)])
    assert set(view.keys()) == PRODUCTION_TOP_KEYS
    assert "fuel_targets" not in view
    blob = json.dumps(view)
    assert "fuel_targets" not in blob
    assert "category_key" not in blob


def test_flag_off_preserves_existing_today_fields(live_v2, flag_off):
    view = _view(_athlete(), [(TODAY, "game", "medium", "10:00", 1.5)])
    assert view["has_schedule"] is True
    assert view["day_type"]                      # day_type rendering preserved
    assert isinstance(view["windows"], list) and view["windows"]
    assert isinstance(view["readiness_grid"], list)
    assert "score" in view["readiness"]          # readiness untouched


def test_no_schedule_athlete_gets_welcome_state_and_no_gauges(live_v2, flag_on):
    """has_schedule=False → WELCOME state, and NO fuel_targets even with flag ON."""
    view = _view(_athlete(), [])  # no events ever
    assert view["has_schedule"] is False
    assert "fuel_targets" not in view


def test_no_schedule_no_block_regardless_of_flag(live_v2, flag_off):
    view = _view(_athlete(), [])
    assert "fuel_targets" not in view


def test_rest_day_with_schedule_still_shows_existing_ui_plus_gauges(live_v2, flag_on):
    """Genuine rest day (has_schedule True, no event today): existing rest UI
    fields intact AND Blueprint-sourced gauges present."""
    view = _view(_athlete(), [(FUTURE, "game", "medium", "10:00", 1.5)])
    assert view["has_schedule"] is True
    assert view["day_type"] == "rest"
    assert view["fuel_targets"]["target_source"] == "blueprint"


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2 — UN-CONFIRM (data model + gauge auto-update)
# ═══════════════════════════════════════════════════════════════════════════

def test_remove_window_capture_reverses_both_writes_and_is_idempotent():
    """Un-confirm must clear BOTH window_logs and meal_plans.logged (capture sets
    both, and build_today_view derives `logged` from either). Idempotent."""
    a = _athlete()
    conn = _today_conn(a, [(TODAY, "game", "medium", "10:00", 1.5)])
    try:
        conn.execute("INSERT INTO meal_plans (athlete_id, plan_date, slot_name, logged) "
                     "VALUES (?,?,?,1)", (a["id"], TODAY, "everyday_breakfast"))
        conn.commit()
        record_window_capture(a["id"], "everyday_breakfast", "text", "x", None, None, conn, log_date=TODAY)
        assert conn.execute(
            "SELECT COUNT(*) FROM window_logs WHERE athlete_id=? AND window_id='everyday_breakfast' "
            "AND log_date=?", (a["id"], TODAY)).fetchone()[0] == 1

        assert remove_window_capture(a["id"], "everyday_breakfast", conn, log_date=TODAY) is True
        assert conn.execute(
            "SELECT COUNT(*) FROM window_logs WHERE athlete_id=? AND window_id='everyday_breakfast' "
            "AND log_date=?", (a["id"], TODAY)).fetchone()[0] == 0
        assert conn.execute(
            "SELECT logged FROM meal_plans WHERE athlete_id=? AND plan_date=? AND slot_name=?",
            (a["id"], TODAY, "everyday_breakfast")).fetchone()["logged"] == 0
        # nothing left to undo
        assert remove_window_capture(a["id"], "everyday_breakfast", conn, log_date=TODAY) is False
    finally:
        conn.close()


def test_uncapture_decrements_gauge_back_to_zero(live_v2, flag_on):
    """Confirm all → daily_met True; un-confirm one → decremented + not met;
    un-confirm all → confirmed_totals back to 0 (gauge updates automatically)."""
    a = _athlete()
    conn = _today_conn(a, [(TODAY, "game", "medium", "10:00", 1.5)])
    try:
        windows = build_today_view(a["id"], conn, today=TODAY)["fuel_targets"]["windows"]
        for w in windows:
            record_window_capture(a["id"], w["slot_name"], "text", "x", None, None, conn, log_date=TODAY)
        all_on = build_today_view(a["id"], conn, today=TODAY)["fuel_targets"]
        assert all_on["daily_met"] is True
        full_carbs = all_on["confirmed_totals"]["carbs_g"]
        assert full_carbs > 0

        remove_window_capture(a["id"], windows[0]["slot_name"], conn, log_date=TODAY)
        one_off = build_today_view(a["id"], conn, today=TODAY)["fuel_targets"]
        assert one_off["daily_met"] is False
        assert one_off["confirmed_totals"]["carbs_g"] < full_carbs

        for w in windows:
            remove_window_capture(a["id"], w["slot_name"], conn, log_date=TODAY)
        zero = build_today_view(a["id"], conn, today=TODAY)["fuel_targets"]
        assert zero["confirmed_totals"]["carbs_g"] == 0
        assert zero["daily_met"] is False
    finally:
        conn.close()
