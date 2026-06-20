"""Tests for approved-domain web search."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.knowledge.web_search import WebSearchResult, search_approved_sites


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
