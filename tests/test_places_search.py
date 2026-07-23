"""Tests for Foursquare-backed nearby restaurant discovery."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.places import nearby_search
from api.services.places.nearby_search import PlaceCandidate, search_nearby_restaurants


def _fake_response(status_code=200, results=None, raise_for_status_error=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"results": results or []}
    if raise_for_status_error:
        resp.raise_for_status.side_effect = raise_for_status_error
    else:
        resp.raise_for_status.return_value = None
    return resp


def _place(fsq_id="p1", name="Green Bowl", distance=800, rating=8.7, review_count=210,
           price=2, open_now=True, category="Salad"):
    return {
        "fsq_id": fsq_id,
        "name": name,
        "distance": distance,
        "location": {"formatted_address": "123 Main St, San Jose, CA"},
        "categories": [{"name": category}],
        "rating": rating,
        "review_count": review_count,
        "price": price,
        "hours": {"open_now": open_now},
        "website": "https://example.com",
        "link": "https://foursquare.com/v/green-bowl",
    }


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    nearby_search._rate_limit_calls.clear()
    yield
    nearby_search._rate_limit_calls.clear()


def test_search_requires_api_key(monkeypatch):
    monkeypatch.delenv("FOURSQUARE_API_KEY", raising=False)
    results = search_nearby_restaurants(37.33, -121.89, athlete_id=1)
    assert results == []  # degrades gracefully, never raises to the caller


def test_search_sends_auth_header_and_params(monkeypatch):
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    seen = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        seen.update(url=url, headers=headers, params=params)
        return _fake_response(results=[_place()])

    monkeypatch.setattr(nearby_search.requests, "get", fake_get)
    results = search_nearby_restaurants(37.33, -121.89, athlete_id=1)

    assert seen["url"] == nearby_search._SEARCH_URL
    assert seen["headers"]["Authorization"] == "Bearer test-key"
    assert seen["headers"]["X-Places-Api-Version"] == nearby_search._API_VERSION
    assert seen["params"]["ll"] == "37.33,-121.89"
    assert len(results) == 1
    assert isinstance(results[0], PlaceCandidate)
    assert results[0].name == "Green Bowl"
    assert results[0].place_id == "p1"


def test_search_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    monkeypatch.setenv("COACH_WEB_SEARCH_ENABLED", "false")
    results = search_nearby_restaurants(37.33, -121.89, athlete_id=1)
    assert results == []


def test_search_retries_once_on_exception(monkeypatch):
    """3+ results avoids the separate widen-radius path, isolating the
    single-request retry behavior being tested here."""
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    monkeypatch.setattr(nearby_search.time, "sleep", lambda s: None)
    calls = {"n": 0}
    hits = [_place(fsq_id=f"p{i}", name=f"Spot {i}") for i in range(3)]

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("blocked")
        return _fake_response(results=hits)

    monkeypatch.setattr(nearby_search.requests, "get", fake_get)
    results = search_nearby_restaurants(37.33, -121.89, athlete_id=1)
    assert len(results) == 3
    assert calls["n"] == 2


def test_search_provider_failure_returns_empty_not_raise(monkeypatch):
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    monkeypatch.setattr(nearby_search.time, "sleep", lambda s: None)

    def fake_get(url, headers=None, params=None, timeout=None):
        raise ConnectionError("still blocked")

    monkeypatch.setattr(nearby_search.requests, "get", fake_get)
    results = search_nearby_restaurants(37.33, -121.89, athlete_id=1)
    assert results == []


def test_closed_places_filtered_when_open_options_exist(monkeypatch):
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    hits = [
        _place(fsq_id="closed", name="Closed Spot", open_now=False),
        _place(fsq_id="open", name="Open Spot", open_now=True),
    ]
    monkeypatch.setattr(nearby_search.requests, "get", lambda *a, **k: _fake_response(results=hits))
    results = search_nearby_restaurants(37.33, -121.89, athlete_id=1)
    assert [c.name for c in results] == ["Open Spot"]


def test_closed_places_kept_when_nothing_else_open(monkeypatch):
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    hits = [_place(fsq_id="closed", name="Closed Spot", open_now=False)]
    monkeypatch.setattr(nearby_search.requests, "get", lambda *a, **k: _fake_response(results=hits))
    results = search_nearby_restaurants(37.33, -121.89, athlete_id=1)
    assert [c.name for c in results] == ["Closed Spot"]


def test_widens_radius_when_thin_results(monkeypatch):
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    calls = {"n": 0}

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["n"] += 1
        if params["radius"] == nearby_search._DEFAULT_RADIUS_M:
            return _fake_response(results=[_place(fsq_id="p1", name="Only One")])
        return _fake_response(results=[
            _place(fsq_id="p1", name="Only One"),
            _place(fsq_id="p2", name="Second"),
            _place(fsq_id="p3", name="Third"),
        ])

    monkeypatch.setattr(nearby_search.requests, "get", fake_get)
    results = search_nearby_restaurants(37.33, -121.89, athlete_id=1)
    assert calls["n"] == 2
    names = {c.name for c in results}
    assert "Second" in names and "Third" in names


def test_no_widen_when_enough_results(monkeypatch):
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    calls = {"n": 0}
    hits = [_place(fsq_id=f"p{i}", name=f"Spot {i}") for i in range(5)]

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["n"] += 1
        return _fake_response(results=hits)

    monkeypatch.setattr(nearby_search.requests, "get", fake_get)
    search_nearby_restaurants(37.33, -121.89, athlete_id=1)
    assert calls["n"] == 1


def test_results_sorted_by_rating_missing_rating_last(monkeypatch):
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    hits = [
        _place(fsq_id="low", name="Low", rating=6.0),
        _place(fsq_id="none", name="NoRating", rating=None),
        _place(fsq_id="high", name="High", rating=9.2),
    ]
    monkeypatch.setattr(nearby_search.requests, "get", lambda *a, **k: _fake_response(results=hits))
    results = search_nearby_restaurants(37.33, -121.89, athlete_id=1)
    assert [c.name for c in results] == ["High", "Low", "NoRating"]


def test_rate_limit_blocks_after_max_calls(monkeypatch):
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    monkeypatch.setattr(nearby_search.requests, "get", lambda *a, **k: _fake_response(results=[_place()]))

    for _ in range(nearby_search._RATE_LIMIT_MAX_CALLS):
        assert search_nearby_restaurants(37.33, -121.89, athlete_id=42) != []

    assert search_nearby_restaurants(37.33, -121.89, athlete_id=42) == []
    # A different athlete is unaffected by athlete 42's limit
    assert search_nearby_restaurants(37.33, -121.89, athlete_id=99) != []


def test_missing_place_id_or_name_dropped(monkeypatch):
    monkeypatch.setenv("FOURSQUARE_API_KEY", "test-key")
    hits = [{"name": "No ID"}, {"fsq_id": "p1"}, _place(fsq_id="p2", name="Valid")]
    monkeypatch.setattr(nearby_search.requests, "get", lambda *a, **k: _fake_response(results=hits))
    results = search_nearby_restaurants(37.33, -121.89, athlete_id=1)
    assert [c.name for c in results] == ["Valid"]
