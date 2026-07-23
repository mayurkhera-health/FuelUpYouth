"""Tests for approved-domain web search."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.knowledge import web_search
from api.services.knowledge.web_search import (
    WebSearchResult,
    RestaurantSearchResult,
    search_approved_sites,
    search_restaurant_menu,
)


# ── _brave_search retry behavior ────────────────────────────────────────────
def _fake_response(status_code=200, results=None, raise_for_status_error=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"web": {"results": results or []}}
    if raise_for_status_error:
        resp.raise_for_status.side_effect = raise_for_status_error
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_brave_search_requires_api_key(monkeypatch):
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="BRAVE_SEARCH_API_KEY"):
        web_search._brave_search("test query", 5)


def test_brave_search_sends_auth_header_and_query(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    seen = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        seen.update(url=url, headers=headers, params=params)
        return _fake_response(results=[{"title": "T", "url": "https://x.com", "description": "D"}])

    monkeypatch.setattr(web_search.requests, "get", fake_get)
    results = web_search._brave_search("Panda Express menu", 5)

    assert seen["url"] == web_search._BRAVE_SEARCH_URL
    assert seen["headers"]["X-Subscription-Token"] == "test-key"
    assert seen["params"]["q"] == "Panda Express menu"
    assert results == [{"title": "T", "href": "https://x.com", "body": "D"}]


def test_brave_search_returns_immediately_on_first_success(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")

    def boom_if_called_twice(*a, **k):
        raise AssertionError("must not sleep when the first attempt already has results")

    monkeypatch.setattr(web_search.time, "sleep", boom_if_called_twice)
    calls = {"n": 0}

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["n"] += 1
        return _fake_response(results=[{"title": "Found", "url": "https://x.com", "description": "b"}])

    monkeypatch.setattr(web_search.requests, "get", fake_get)
    results = web_search._brave_search("test query", 5)
    assert len(results) == 1
    assert calls["n"] == 1


def test_brave_search_retries_once_on_empty_result(monkeypatch):
    """The confirmed live failure mode with the previous scraper (an empty
    result rather than an error, from a transient block) is worth guarding
    against here too — cheap insurance even on a real API."""
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setattr(web_search.time, "sleep", lambda s: None)
    calls = {"n": 0}
    sequence = [[], [{"title": "Found", "url": "https://x.com", "description": "b"}]]

    def fake_get(url, headers=None, params=None, timeout=None):
        idx = calls["n"]
        calls["n"] += 1
        return _fake_response(results=sequence[idx])

    monkeypatch.setattr(web_search.requests, "get", fake_get)
    results = web_search._brave_search("test query", 5)
    assert len(results) == 1
    assert calls["n"] == 2


def test_brave_search_empty_on_both_attempts_returns_empty_not_raise(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setattr(web_search.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["n"] += 1
        return _fake_response(results=[])

    monkeypatch.setattr(web_search.requests, "get", fake_get)
    results = web_search._brave_search("test query", 5)
    assert results == []
    assert calls["n"] == 2  # confirmed it retried, not just gave up on attempt one


def test_brave_search_retries_once_on_exception(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setattr(web_search.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("blocked")
        return _fake_response(results=[{"title": "Found", "url": "https://x.com", "description": "b"}])

    monkeypatch.setattr(web_search.requests, "get", fake_get)
    results = web_search._brave_search("test query", 5)
    assert len(results) == 1
    assert calls["n"] == 2


def test_brave_search_raises_after_two_failed_attempts(monkeypatch):
    """Callers (search_approved_sites, search_restaurant_menu) already catch
    and degrade gracefully on an exception here — confirm it still surfaces
    as an exception (not silently swallowed a third time) after the retry
    budget is spent, rather than looping forever."""
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setattr(web_search.time, "sleep", lambda s: None)

    def fake_get(url, headers=None, params=None, timeout=None):
        raise ConnectionError("still blocked")

    monkeypatch.setattr(web_search.requests, "get", fake_get)
    with pytest.raises(ConnectionError):
        web_search._brave_search("test query", 5)


def test_brave_search_raises_on_http_error_status(monkeypatch):
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")
    monkeypatch.setattr(web_search.time, "sleep", lambda s: None)
    import requests as real_requests

    def fake_get(url, headers=None, params=None, timeout=None):
        return _fake_response(status_code=401, raise_for_status_error=real_requests.HTTPError("401"))

    monkeypatch.setattr(web_search.requests, "get", fake_get)
    with pytest.raises(real_requests.HTTPError):
        web_search._brave_search("test query", 5)


# ── search_approved_sites / search_restaurant_menu ──────────────────────────
def test_search_filters_to_approved_domains():
    hits = [
        {"href": "https://www.aap.org/en/patient-care/iron", "title": "Iron guidance", "body": "Iron for youth athletes"},
        {"href": "https://example.com/spam", "title": "Spam", "body": "Ignore me"},
    ]

    with patch("api.services.knowledge.web_search._brave_search", return_value=hits):
        with patch("api.services.knowledge.web_search._fetch_page_text", return_value=""):
            with patch("api.services.knowledge.web_search.embed_text", return_value=[1.0, 0.0]):
                results = search_approved_sites("iron for teenage athletes", max_results=3)

    assert len(results) == 1
    assert results[0].organization_id == "aap"
    assert "aap.org" in results[0].url


def test_search_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("COACH_WEB_SEARCH_ENABLED", "false")
    results = search_approved_sites("hydration")
    assert results == []


def test_site_filter_includes_approved_domains():
    from api.services.knowledge.web_search import _site_filter_query

    query = _site_filter_query("pre game snack")
    assert "site:acsm.org" in query
    assert "site:aap.org" in query
    assert "pre game snack" in query


def test_restaurant_search_not_restricted_to_approved_domains():
    hits = [
        {"href": "https://www.pandaexpress.com/menu", "title": "Panda Express Menu",
         "body": "Grilled Teriyaki Chicken, Broccoli Beef"},
    ]

    with patch("api.services.knowledge.web_search._brave_search", return_value=hits) as mock_search:
        with patch("api.services.knowledge.web_search._fetch_page_text", return_value=""):
            with patch("api.services.knowledge.web_search.embed_text", return_value=[1.0, 0.0]):
                results = search_restaurant_menu("Panda Express", "healthy lunch options", max_results=3)

    assert len(results) == 1
    assert isinstance(results[0], RestaurantSearchResult)
    assert results[0].url == "https://www.pandaexpress.com/menu"
    query_used = mock_search.call_args.args[0]
    assert "site:" not in query_used
    assert "Panda Express" in query_used


def test_restaurant_search_filters_low_relevance_results():
    """Off-topic hits (e.g. the giant panda animal, not Panda Express) must be
    dropped even though they matched the search term — confirmed live that
    genuine Panda Express pages score ~0.57-0.70 vs ~0.13-0.24 for animal
    content, well clear of the 0.45 floor."""
    hits = [
        {"href": "https://www.pandaexpress.com/", "title": "Panda Express",
         "body": "Orange Chicken, Broccoli Beef, Fried Rice menu"},
        {"href": "https://en.wikipedia.org/wiki/Giant_panda", "title": "Giant panda - Wikipedia",
         "body": "The giant panda is a bear species endemic to China"},
    ]

    # query vector, then one content vector per hit (in hit order)
    vectors = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]

    with patch("api.services.knowledge.web_search._brave_search", return_value=hits):
        with patch("api.services.knowledge.web_search._fetch_page_text", return_value=""):
            with patch("api.services.knowledge.web_search.embed_text", side_effect=vectors):
                results = search_restaurant_menu("Panda Express", "healthy lunch options", max_results=5)

    assert len(results) == 1
    assert results[0].url == "https://www.pandaexpress.com/"


def test_restaurant_search_query_excludes_raw_question():
    """A verbose, punctuated athlete question must not be appended to the
    search string — keeps the query targeted. Only the restaurant name feeds
    the actual search."""
    with patch("api.services.knowledge.web_search._brave_search", return_value=[]) as mock_search:
        with patch("api.services.knowledge.web_search.embed_text", return_value=[1.0, 0.0]):
            search_restaurant_menu(
                "Panda Express",
                "I am heading to Panda Express for lunch. Can you recommend a few healthy options?",
            )

    query_used = mock_search.call_args.args[0]
    assert query_used == "Panda Express menu nutrition facts"


def test_restaurant_search_includes_city_when_given():
    with patch("api.services.knowledge.web_search._brave_search", return_value=[]) as mock_search:
        with patch("api.services.knowledge.web_search.embed_text", return_value=[1.0, 0.0]):
            search_restaurant_menu("Panda Express", "healthy lunch options", city="San Jose, CA")

    query_used = mock_search.call_args.args[0]
    assert "near San Jose, CA" in query_used


def test_restaurant_search_omits_city_when_not_given():
    with patch("api.services.knowledge.web_search._brave_search", return_value=[]) as mock_search:
        with patch("api.services.knowledge.web_search.embed_text", return_value=[1.0, 0.0]):
            search_restaurant_menu("Panda Express", "healthy lunch options")

    query_used = mock_search.call_args.args[0]
    assert "near" not in query_used


def test_restaurant_search_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("COACH_WEB_SEARCH_ENABLED", "false")
    results = search_restaurant_menu("Panda Express", "lunch")
    assert results == []


def test_restaurant_search_empty_name_returns_empty():
    results = search_restaurant_menu("", "lunch")
    assert results == []
