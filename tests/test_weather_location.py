"""get_weather supports coordinate lookup (lat/lon) with city-name fallback."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.services.weather as weather


class _FakeResp:
    status_code = 200

    def json(self):
        return {
            "main": {"temp": 72.0, "humidity": 55},
            "weather": [{"description": "clear sky"}],
        }


def _capture_url(monkeypatch):
    """Stub requests.get + the API key, returning a dict that records the URL hit."""
    seen = {"url": None}

    def fake_get(url, timeout=None):
        seen["url"] = url
        return _FakeResp()

    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key")
    monkeypatch.setattr(weather.requests, "get", fake_get)
    return seen


def test_fetch_builds_latlon_url_when_coords_given(monkeypatch):
    seen = _capture_url(monkeypatch)
    result = weather._fetch_weather(city="San Ramon", lat=37.78, lon=-121.98)
    assert "lat=37.78" in seen["url"] and "lon=-121.98" in seen["url"]
    assert "q=" not in seen["url"]               # coords win over city
    assert result["temp_f"] == 72.0 and result["error"] is None


def test_fetch_builds_city_url_when_no_coords(monkeypatch):
    seen = _capture_url(monkeypatch)
    weather._fetch_weather(city="Denver")
    assert "q=Denver" in seen["url"]
    assert "lat=" not in seen["url"]


def test_fetch_errors_when_no_location(monkeypatch):
    _capture_url(monkeypatch)
    result = weather._fetch_weather()
    assert result["error"] == "No location provided"
    assert result["temp_f"] is None


def test_get_weather_prefers_coords(monkeypatch):
    weather._weather_cache.clear()
    monkeypatch.setattr(weather, "_now", lambda: 1000.0)
    got = {}

    def fake_fetch(city=None, lat=None, lon=None):
        got["city"], got["lat"], got["lon"] = city, lat, lon
        return {"temp_f": 80.0, "humidity": 40, "description": "sunny", "error": None}

    monkeypatch.setattr(weather, "_fetch_weather", fake_fetch)
    res = weather.get_weather(city="San Ramon", lat=37.78, lon=-121.98)
    assert (got["lat"], got["lon"]) == (37.78, -121.98)
    assert res["temp_f"] == 80.0
    # cached under a coord key, distinct from the city key
    assert any(k.startswith("coord:") for k in weather._weather_cache)


def test_get_weather_city_fallback(monkeypatch):
    weather._weather_cache.clear()
    monkeypatch.setattr(weather, "_now", lambda: 1000.0)
    got = {}

    def fake_fetch(city=None, lat=None, lon=None):
        got["city"], got["lat"], got["lon"] = city, lat, lon
        return {"temp_f": 65.0, "humidity": 60, "description": "cloudy", "error": None}

    monkeypatch.setattr(weather, "_fetch_weather", fake_fetch)
    res = weather.get_weather(city="Denver")
    assert got["city"] == "Denver" and got["lat"] is None and got["lon"] is None
    assert res["temp_f"] == 65.0


def test_get_weather_none_when_both_missing(monkeypatch):
    weather._weather_cache.clear()

    def boom(city=None, lat=None, lon=None):
        raise AssertionError("_fetch_weather must not be called when no location given")

    monkeypatch.setattr(weather, "_fetch_weather", boom)
    res = weather.get_weather()
    assert res["error"] == "No location provided"
    assert res["temp_f"] is None


class _FakeGeoResp:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data if data is not None else []

    def json(self):
        return self._data


def test_reverse_geocode_returns_city_and_state(monkeypatch):
    weather._geocode_cache.clear()
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key")
    monkeypatch.setattr(
        weather.requests, "get",
        lambda url, params=None, timeout=None: _FakeGeoResp(200, [{"name": "San Jose", "state": "CA"}]),
    )
    assert weather.reverse_geocode_city(37.33, -121.89) == "San Jose, CA"


def test_reverse_geocode_no_api_key_returns_none(monkeypatch):
    weather._geocode_cache.clear()
    monkeypatch.delenv("OPENWEATHERMAP_API_KEY", raising=False)

    def boom(*a, **k):
        raise AssertionError("must not call the API with no key configured")

    monkeypatch.setattr(weather.requests, "get", boom)
    assert weather.reverse_geocode_city(37.33, -121.89) is None


def test_reverse_geocode_empty_response_returns_none(monkeypatch):
    weather._geocode_cache.clear()
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key")
    monkeypatch.setattr(weather.requests, "get", lambda url, params=None, timeout=None: _FakeGeoResp(200, []))
    assert weather.reverse_geocode_city(0.0, 0.0) is None


def test_reverse_geocode_is_cached(monkeypatch):
    weather._geocode_cache.clear()
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key")
    calls = {"n": 0}

    def fake_get(url, params=None, timeout=None):
        calls["n"] += 1
        return _FakeGeoResp(200, [{"name": "San Jose", "state": "CA"}])

    monkeypatch.setattr(weather.requests, "get", fake_get)
    weather.reverse_geocode_city(37.33, -121.89)
    weather.reverse_geocode_city(37.33, -121.89)
    assert calls["n"] == 1
