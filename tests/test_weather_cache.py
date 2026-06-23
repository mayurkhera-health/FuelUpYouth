"""get_weather caches results per city for a TTL window."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.services.weather as weather


def _stub_fetch(monkeypatch):
    calls = {"n": 0}

    def fake_fetch(city=None, lat=None, lon=None):
        calls["n"] += 1
        return {"temp_f": 70.0, "humidity": 50, "description": "clear", "error": None}

    monkeypatch.setattr(weather, "_fetch_weather", fake_fetch)
    return calls


def test_second_call_within_ttl_is_cached(monkeypatch):
    weather._weather_cache.clear()
    calls = _stub_fetch(monkeypatch)
    monkeypatch.setattr(weather, "_now", lambda: 1000.0)

    a = weather.get_weather("Denver")
    b = weather.get_weather("Denver")

    assert a == b
    assert calls["n"] == 1  # second call served from cache


def test_call_after_ttl_refetches(monkeypatch):
    weather._weather_cache.clear()
    calls = _stub_fetch(monkeypatch)

    monkeypatch.setattr(weather, "_now", lambda: 1000.0)
    weather.get_weather("Denver")
    monkeypatch.setattr(weather, "_now", lambda: 1000.0 + weather._WEATHER_TTL_SECONDS + 1)
    weather.get_weather("Denver")

    assert calls["n"] == 2


def test_errors_are_not_cached(monkeypatch):
    weather._weather_cache.clear()
    monkeypatch.setattr(weather, "_now", lambda: 1000.0)

    def err_fetch(city=None, lat=None, lon=None):
        return {"temp_f": None, "humidity": None, "description": "unknown", "error": "boom"}

    monkeypatch.setattr(weather, "_fetch_weather", err_fetch)
    weather.get_weather("Denver")
    assert "denver" not in weather._weather_cache
