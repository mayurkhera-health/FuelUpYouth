"""assemble_context weather resolution: event location (existing) vs the new
device-location fallback for days with no event."""
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


def test_no_event_no_location_leaves_weather_none():
    conn = _conn()
    ctx = assemble_context(conn=conn, **_kwargs())
    assert ctx["weather"] is None


def test_no_event_falls_back_to_device_location():
    conn = _conn()
    fake_weather = {"temp_f": 92.0, "humidity": 40, "description": "sunny", "error": None}

    with patch("api.services.coach_service.get_weather", return_value=fake_weather) as mock_weather:
        with patch(
            "api.services.weather.reverse_geocode_city", return_value="San Jose, CA"
        ) as mock_geocode:
            ctx = assemble_context(conn=conn, latitude=37.33, longitude=-121.89, **_kwargs())

    mock_geocode.assert_called_once_with(37.33, -121.89)
    mock_weather.assert_called_once_with(lat=37.33, lon=-121.89)
    assert ctx["weather"]["temp_f"] == 92.0
    assert ctx["weather"]["heat_flag"] is True
    assert ctx["weather"]["location_label"] == "San Jose, CA"


def test_event_location_wins_over_device_location():
    """An event with its own venue location must NOT be overridden by the
    device fallback — game-day weather at the actual venue matters more than
    wherever the athlete's phone happens to be right now."""
    conn = _conn()
    conn.execute(
        "INSERT INTO events (athlete_id, event_date, event_name, event_type, city, latitude, longitude) "
        "VALUES (1, '2026-07-23', 'Big Game', 'game', 'Stadium City', 10.0, 20.0)"
    )

    with patch("api.services.coach_service.get_weather", return_value={
        "temp_f": 70.0, "humidity": 30, "description": "clear", "error": None,
    }) as mock_weather:
        with patch("api.services.weather.reverse_geocode_city") as mock_geocode:
            ctx = assemble_context(conn=conn, latitude=37.33, longitude=-121.89, **_kwargs())

    mock_geocode.assert_not_called()
    mock_weather.assert_called_once_with(city="Stadium City", lat=10.0, lon=20.0)
    assert ctx["weather"]["temp_f"] == 70.0


def test_geocode_failure_still_returns_weather_without_label():
    conn = _conn()
    with patch("api.services.coach_service.get_weather", return_value={
        "temp_f": 60.0, "humidity": 50, "description": "cloudy", "error": None,
    }):
        with patch("api.services.weather.reverse_geocode_city", side_effect=RuntimeError("boom")):
            ctx = assemble_context(conn=conn, latitude=1.0, longitude=2.0, **_kwargs())

    assert ctx["weather"]["temp_f"] == 60.0
    assert ctx["weather"]["location_label"] is None
