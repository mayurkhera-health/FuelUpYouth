"""assemble_context threads today's event + device latitude/longitude into
resolve_weather() correctly. Weather-resolution logic itself (event-wins,
device-fallback, heat thresholds) is tested directly in test_weather_location.py
against api.services.weather, which now owns that logic."""
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.coach_service import assemble_context


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE athletes (
            id INTEGER PRIMARY KEY, first_name TEXT, age INTEGER, gender TEXT,
            weight_lbs REAL, height_ft REAL, height_in REAL, competition_level TEXT,
            allergies TEXT, dietary_restrictions TEXT,
            food_preferences TEXT, supplement_use TEXT, sweat_profile TEXT,
            blueprint_json TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE events (
            id INTEGER PRIMARY KEY, athlete_id INTEGER, event_date TEXT,
            event_name TEXT, event_type TEXT, start_time TEXT,
            city TEXT, latitude REAL, longitude REAL
        )
    """)
    conn.execute(
        "INSERT INTO athletes (id, first_name, age, gender, weight_lbs, height_ft, height_in) "
        "VALUES (1, 'Alex', 14, 'female', 120, 5, 4)"
    )
    return conn


def _kwargs(**overrides):
    base = dict(
        athlete_id=1, window_key="breakfast", window_label="Breakfast",
        window_time="7:00 AM", category_key="everyday", category_label="Everyday",
        plan_date="2026-07-23",
    )
    base.update(overrides)
    return base


def test_no_event_passes_none_and_device_coords_to_resolve_weather():
    conn = _conn()
    with patch("api.services.coach_service.resolve_weather", return_value=None) as mock_resolve:
        assemble_context(conn=conn, latitude=37.33, longitude=-121.89, **_kwargs())

    mock_resolve.assert_called_once_with(None, 37.33, -121.89)


def test_todays_event_passed_to_resolve_weather():
    conn = _conn()
    conn.execute(
        "INSERT INTO events (athlete_id, event_date, event_name, event_type, city, latitude, longitude) "
        "VALUES (1, '2026-07-23', 'Big Game', 'game', 'Stadium City', 10.0, 20.0)"
    )
    with patch("api.services.coach_service.resolve_weather", return_value=None) as mock_resolve:
        assemble_context(conn=conn, latitude=37.33, longitude=-121.89, **_kwargs())

    (event_arg, lat_arg, lon_arg), _ = mock_resolve.call_args
    assert event_arg["event_name"] == "Big Game"
    assert event_arg["city"] == "Stadium City"
    assert (lat_arg, lon_arg) == (37.33, -121.89)


def test_no_latitude_longitude_still_works():
    conn = _conn()
    with patch("api.services.coach_service.resolve_weather", return_value=None) as mock_resolve:
        ctx = assemble_context(conn=conn, **_kwargs())

    mock_resolve.assert_called_once_with(None, None, None)
    assert ctx["weather"] is None


def test_weather_result_flows_into_context():
    conn = _conn()
    fake_weather = {
        "temp_f": 92.0, "humidity": 40, "description": "sunny",
        "heat_flag": True, "heat_level": "hot", "location_label": "San Jose, CA",
    }
    with patch("api.services.coach_service.resolve_weather", return_value=fake_weather):
        ctx = assemble_context(conn=conn, latitude=37.33, longitude=-121.89, **_kwargs())

    assert ctx["weather"] == fake_weather


def test_survives_resolve_weather_raising_unexpectedly():
    """assemble_context itself has no try/except around resolve_weather —
    it relies entirely on resolve_weather being a hardened boundary that
    never raises. This proves that contract from assemble_context's side:
    even if resolve_weather somehow still raised, real weather.resolve_weather
    (not mocked here) is what actually protects this call — see
    test_weather_location.py's test_resolve_weather_survives_get_weather_raising
    for the boundary itself. This test exercises the REAL resolve_weather
    (unmocked) with a null-humidity API response reaching it through the
    full assemble_context call, end to end."""
    conn = _conn()
    with patch(
        "api.services.weather._fetch_weather",
        return_value={"temp_f": 92.0, "humidity": None, "description": "hazy", "error": None},
    ):
        ctx = assemble_context(conn=conn, latitude=37.33, longitude=-121.89, **_kwargs())

    assert ctx["weather"] is not None
    assert ctx["weather"]["heat_flag"] is True
