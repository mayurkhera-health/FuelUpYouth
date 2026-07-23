"""Live web search restricted to approved sports-nutrition domains."""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse

import requests

from api.services.knowledge.approved_sources import approved_domains, match_approved_source
from api.services.knowledge.embedding_utils import cosine_similarity, embed_text

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 10
_MAX_PAGE_CHARS = 1800
_MAX_FETCH_PAGES = 4
_USER_AGENT = "FuelUpYouth-NutritionCoach/1.0 (+https://fuelup-youth.fly.dev)"

# Empirically calibrated against live results for "Panda Express": the
# restaurant's own pages scored 0.57-0.70, unrelated "giant panda the animal"
# noise scored 0.13-0.24. 0.45 cleanly separates the two with margin.
_MIN_RESTAURANT_RELEVANCE = 0.45

# The underlying scraper (no official API) is confirmed transiently flaky
# under load — the exact same query returned 0 results, then 5 minutes
# later returned 5, with no code change. One short retry absorbs that
# without adding much latency to a request the user is already waiting on.
_DDG_RETRY_DELAY_SECONDS = 1.5


@dataclass
class WebSearchResult:
    url: str
    title: str
    snippet: str
    content: str
    organization_id: str
    organization_name: str
    organization_url: str
    score: float = 0.0


@dataclass
class RestaurantSearchResult:
    """A page from a specific restaurant's own site — NOT a vetted
    sports-nutrition source. Callers must say so in the response."""
    url: str
    title: str
    snippet: str
    content: str
    score: float = 0.0


def _web_search_enabled() -> bool:
    return os.getenv("COACH_WEB_SEARCH_ENABLED", "true").lower() not in ("0", "false", "no")


def _site_filter_query(query: str) -> str:
    domains = approved_domains()
    site_clause = " OR ".join(f"site:{domain}" for domain in domains)
    return f"({site_clause}) {query}"


def _ddg_search(query: str, max_results: int) -> list[dict]:
    """One retry on empty results or a raised exception — the scraper returns
    an empty list (not an error) when transiently rate-limited/blocked, so an
    empty result on the first attempt is retried once before being trusted as
    "genuinely nothing found"."""
    try:
        from duckduckgo_search import DDGS
    except ImportError as exc:
        raise RuntimeError("duckduckgo-search is required for coach web search") from exc

    for attempt in range(2):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
        except Exception:
            if attempt == 0:
                time.sleep(_DDG_RETRY_DELAY_SECONDS)
                continue
            raise
        else:
            if results or attempt == 1:
                return results
            time.sleep(_DDG_RETRY_DELAY_SECONDS)
    return []  # unreachable — loop always returns or raises


def _strip_html(html: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    cleaned = re.sub(r"(?is)<!--.*?-->", " ", cleaned)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _fetch_page_text(url: str) -> str:
    response = requests.get(
        url,
        timeout=_FETCH_TIMEOUT,
        headers={"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        return ""
    return _strip_html(response.text)[:_MAX_PAGE_CHARS]


def search_approved_sites(query: str, *, max_results: int = 5) -> list[WebSearchResult]:
    """
    Search the public web, limited to approved organization domains.
    Returns page excerpts ranked by embedding similarity to the query.
    """
    if not _web_search_enabled():
        return []

    trimmed = (query or "").strip()
    if not trimmed:
        return []

    try:
        hits = _ddg_search(_site_filter_query(trimmed), max_results=max_results * 2)
    except Exception:
        logger.exception("Approved-domain web search failed")
        return []

    query_vec = embed_text(trimmed)
    results: list[WebSearchResult] = []
    seen_urls: set[str] = set()

    for hit in hits:
        url = (hit.get("href") or hit.get("url") or "").strip()
        if not url or url in seen_urls:
            continue

        org = match_approved_source(url)
        if not org:
            continue

        seen_urls.add(url)
        title = (hit.get("title") or urlparse(url).path or url).strip()
        snippet = (hit.get("body") or hit.get("snippet") or "").strip()

        content = snippet
        if len(results) < _MAX_FETCH_PAGES:
            try:
                page_text = _fetch_page_text(url)
                if page_text:
                    content = page_text
            except Exception:
                logger.debug("Could not fetch approved page %s", url, exc_info=True)

        if not content:
            continue

        score = cosine_similarity(query_vec, embed_text(f"{title}\n{content[:1200]}"))
        results.append(
            WebSearchResult(
                url=url,
                title=title,
                snippet=snippet,
                content=content,
                organization_id=org.id,
                organization_name=org.name,
                organization_url=org.url,
                score=score,
            )
        )

        if len(results) >= max_results:
            break

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:max_results]


def search_restaurant_menu(
    restaurant_name: str, query: str, *, city: str | None = None, max_results: int = 5
) -> list[RestaurantSearchResult]:
    """
    Open web search for a specific named restaurant's own menu/nutrition
    page — deliberately NOT restricted to approved_domains(). Results come
    from the restaurant's own site, not a vetted sports-nutrition source;
    the caller is responsible for saying so in the response.

    `city`, when given, narrows the search to that location (multi-location
    chains often have region-specific menus/pricing). Optional — searches
    the chain generally without it.
    """
    if not _web_search_enabled():
        return []

    name = (restaurant_name or "").strip()
    if not name:
        return []

    # Search on the restaurant name (+ city, if known) alone — appending the
    # athlete's raw, conversational question (punctuation, filler words)
    # reliably returns zero hits from DDG. `query` is still used below to
    # rank the fetched pages by relevance, just not the search string itself.
    search_query = f"{name} menu nutrition facts"
    if city:
        search_query += f" near {city}"

    try:
        hits = _ddg_search(search_query, max_results=max_results * 2)
    except Exception:
        logger.exception("Restaurant menu search failed for %r", name)
        return []

    query_vec = embed_text(f"{name} {query}".strip())
    results: list[RestaurantSearchResult] = []
    seen_urls: set[str] = set()
    fetched_pages = 0

    # Score every candidate before ranking/truncating — an early cutoff at
    # max_results (before sorting) can lock in low-relevance hits ahead of
    # better ones DDG happened to rank lower. Only page *fetches* stay capped
    # (network cost); scoring itself is cheap.
    for hit in hits:
        url = (hit.get("href") or hit.get("url") or "").strip()
        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        title = (hit.get("title") or urlparse(url).path or url).strip()
        snippet = (hit.get("body") or hit.get("snippet") or "").strip()

        content = snippet
        if fetched_pages < _MAX_FETCH_PAGES:
            fetched_pages += 1
            try:
                page_text = _fetch_page_text(url)
                if page_text:
                    content = page_text
            except Exception:
                logger.debug("Could not fetch restaurant page %s", url, exc_info=True)

        if not content:
            continue

        score = cosine_similarity(query_vec, embed_text(f"{title}\n{content[:1200]}"))
        if score < _MIN_RESTAURANT_RELEVANCE:
            continue
        results.append(
            RestaurantSearchResult(url=url, title=title, snippet=snippet, content=content, score=score)
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:max_results]
