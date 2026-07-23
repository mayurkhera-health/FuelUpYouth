"""Tests for approved-domain web search."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.knowledge.web_search import (
    WebSearchResult,
    RestaurantSearchResult,
    search_approved_sites,
    search_restaurant_menu,
)


def test_search_filters_to_approved_domains():
    hits = [
        {"href": "https://www.aap.org/en/patient-care/iron", "title": "Iron guidance", "body": "Iron for youth athletes"},
        {"href": "https://example.com/spam", "title": "Spam", "body": "Ignore me"},
    ]

    with patch("api.services.knowledge.web_search._ddg_search", return_value=hits):
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

    with patch("api.services.knowledge.web_search._ddg_search", return_value=hits) as mock_search:
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

    with patch("api.services.knowledge.web_search._ddg_search", return_value=hits):
        with patch("api.services.knowledge.web_search._fetch_page_text", return_value=""):
            with patch("api.services.knowledge.web_search.embed_text", side_effect=vectors):
                results = search_restaurant_menu("Panda Express", "healthy lunch options", max_results=5)

    assert len(results) == 1
    assert results[0].url == "https://www.pandaexpress.com/"


def test_restaurant_search_query_excludes_raw_question():
    """A verbose, punctuated athlete question must not be appended to the DDG
    search string — it reliably returns zero hits (confirmed live against
    DuckDuckGo). Only the restaurant name feeds the actual search."""
    with patch("api.services.knowledge.web_search._ddg_search", return_value=[]) as mock_search:
        with patch("api.services.knowledge.web_search.embed_text", return_value=[1.0, 0.0]):
            search_restaurant_menu(
                "Panda Express",
                "I am heading to Panda Express for lunch. Can you recommend a few healthy options?",
            )

    query_used = mock_search.call_args.args[0]
    assert query_used == "Panda Express menu nutrition facts"


def test_restaurant_search_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("COACH_WEB_SEARCH_ENABLED", "false")
    results = search_restaurant_menu("Panda Express", "lunch")
    assert results == []


def test_restaurant_search_empty_name_returns_empty():
    results = search_restaurant_menu("", "lunch")
    assert results == []
