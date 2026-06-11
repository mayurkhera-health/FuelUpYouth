import pytest
from api.services.today_service import calculate_performance_forecast, get_mission_items


def make_tl(calories=80, carbs=80, protein=80, iron=80, calcium=80, water=80):
    """Build a minimal traffic_light dict for testing."""
    def cell(pct):
        return {"pct_met": pct, "logged": 0, "target": 100, "gap": max(0, 100 - pct), "status": "met" if pct >= 80 else "low" if pct >= 50 else "critical"}
    return {
        "calories":   cell(calories),
        "carbs_g":    cell(carbs),
        "protein_g":  cell(protein),
        "iron_mg":    cell(iron),
        "calcium_mg": cell(calcium),
        "water_oz":   cell(water),
        "daily_fuel_score": 75,
    }


# ── calculate_performance_forecast ───────────────────────────────────────────

def test_forecast_returns_four_keys():
    result = calculate_performance_forecast(make_tl())
    assert set(result.keys()) == {"sprint_capacity", "energy_reserves", "second_half_power", "mental_focus"}


def test_forecast_all_100_gives_100():
    result = calculate_performance_forecast(make_tl(100, 100, 100, 100, 100, 100))
    assert result["sprint_capacity"] == 100
    assert result["energy_reserves"] == 100
    assert result["second_half_power"] == 100
    assert result["mental_focus"] == 100


def test_forecast_all_zero_gives_zero():
    result = calculate_performance_forecast(make_tl(0, 0, 0, 0, 0, 0))
    assert result["sprint_capacity"] == 0
    assert result["energy_reserves"] == 0
    assert result["second_half_power"] == 0
    assert result["mental_focus"] == 0


def test_forecast_sprint_capacity_formula():
    # carbs=100, iron=0, protein=0 → 100*0.40 + 0*0.35 + 0*0.25 = 40
    result = calculate_performance_forecast(make_tl(calories=0, carbs=100, protein=0, iron=0, water=0))
    assert result["sprint_capacity"] == 40


def test_forecast_energy_reserves_formula():
    # calories=100, carbs=0 → 100*0.60 + 0*0.40 = 60
    result = calculate_performance_forecast(make_tl(calories=100, carbs=0, protein=0, iron=0, water=0))
    assert result["energy_reserves"] == 60


def test_forecast_second_half_power_formula():
    # iron=100, carbs=0, water=0 → 100*0.50 = 50
    result = calculate_performance_forecast(make_tl(calories=0, carbs=0, protein=0, iron=100, water=0))
    assert result["second_half_power"] == 50


def test_forecast_mental_focus_formula():
    # calories=0, water=100, protein=0 → 100*0.35 = 35
    result = calculate_performance_forecast(make_tl(calories=0, carbs=0, protein=0, iron=0, water=100))
    assert result["mental_focus"] == 35


def test_forecast_caps_at_100():
    # Each pct_met is capped at 100 before weighting
    tl = make_tl(100, 100, 100, 100, 100, 100)
    for k in tl:
        if isinstance(tl[k], dict):
            tl[k]["pct_met"] = 150  # simulate over-logging
    result = calculate_performance_forecast(tl)
    assert result["sprint_capacity"] == 100
    assert result["energy_reserves"] == 100
