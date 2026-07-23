"""Nearby restaurant discovery via the Foursquare Places API — for the AI
Coach's "restaurants near me" intent. Distinct from
api.services.knowledge.web_search.search_restaurant_menu, which looks up a
SPECIFIC NAMED restaurant's own menu text; this module only returns
discovery data (name, distance, rating, hours, price) for restaurants near
a coordinate — no menu contents are available from this provider."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://places-api.foursquare.com/places/search"
_API_VERSION = "2025-06-17"
_FETCH_TIMEOUT = 10

_DEFAULT_RADIUS_M = 3000
_WIDE_RADIUS_M = 8000
_MIN_RESULTS_BEFORE_WIDEN = 3

_SEARCH_RETRY_DELAY_SECONDS = 1.5

# Per-athlete throttle on this provider — unlike the flat-fee Bedrock/Brave
# integrations, Foursquare bills per call, so an unbounded loop (or a chatty
# retry from the client) is a real cost risk here specifically.
_RATE_LIMIT_MAX_CALLS = 10
_RATE_LIMIT_WINDOW_SECONDS = 600
_rate_limit_calls: dict[int, list[float]] = {}


@dataclass
class PlaceCandidate:
    place_id: str
    name: str
    distance_m: float | None
    address: str
    category: str
    rating: float | None
    review_count: int | None
    price_level: int | None
    open_now: bool | None
    website: str | None
    maps_url: str | None


def _places_enabled() -> bool:
    return os.getenv("COACH_WEB_SEARCH_ENABLED", "true").lower() not in ("0", "false", "no")


def _now() -> float:
    return time.monotonic()


def _rate_limited(athlete_id: int | None) -> bool:
    if athlete_id is None:
        return False
    now = _now()
    calls = [t for t in _rate_limit_calls.get(athlete_id, []) if now - t < _RATE_LIMIT_WINDOW_SECONDS]
    if len(calls) >= _RATE_LIMIT_MAX_CALLS:
        _rate_limit_calls[athlete_id] = calls
        return True
    calls.append(now)
    _rate_limit_calls[athlete_id] = calls
    return False


def _fsq_search(lat: float, lon: float, radius_m: int, query: str, limit: int) -> list[dict]:
    api_key = os.getenv("FOURSQUARE_API_KEY")
    if not api_key:
        raise RuntimeError("FOURSQUARE_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Places-Api-Version": _API_VERSION,
        "Accept": "application/json",
    }
    params = {
        "ll": f"{lat},{lon}",
        "radius": radius_m,
        "query": query,
        "sort": "RATING",
        "limit": limit,
    }

    for attempt in range(2):
        try:
            resp = requests.get(_SEARCH_URL, headers=headers, params=params, timeout=_FETCH_TIMEOUT)
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception:
            if attempt == 0:
                time.sleep(_SEARCH_RETRY_DELAY_SECONDS)
                continue
            raise
        else:
            if results or attempt == 1:
                return results
            time.sleep(_SEARCH_RETRY_DELAY_SECONDS)
    return []  # unreachable — loop always returns or raises


def _parse_candidate(raw: dict) -> PlaceCandidate | None:
    place_id = raw.get("fsq_id") or raw.get("fsq_place_id")
    name = (raw.get("name") or "").strip()
    if not place_id or not name:
        return None

    location = raw.get("location") or {}
    address = location.get("formatted_address") or ", ".join(
        p for p in [location.get("address"), location.get("locality"), location.get("region")] if p
    )

    categories = raw.get("categories") or []
    category = categories[0].get("name") if categories and isinstance(categories[0], dict) else ""

    # Field names have shifted across Foursquare API generations (v3 -> the
    # 2025 Places API) — fall back across the known variants rather than
    # trusting one exact shape, same defensive posture as the Brave parser.
    rating = raw.get("rating")
    review_count = raw.get("review_count") or (raw.get("stats") or {}).get("total_ratings")
    price_level = raw.get("price")

    hours = raw.get("hours") or {}
    open_now = hours.get("open_now") if isinstance(hours, dict) else raw.get("open_now")

    return PlaceCandidate(
        place_id=place_id,
        name=name,
        distance_m=raw.get("distance"),
        address=address or "",
        category=category or "Restaurant",
        rating=rating,
        review_count=review_count,
        price_level=price_level,
        open_now=open_now,
        website=raw.get("website"),
        maps_url=raw.get("link"),
    )


def search_nearby_restaurants(
    lat: float,
    lon: float,
    athlete_id: int | None,
    *,
    radius_m: int = _DEFAULT_RADIUS_M,
    query_hint: str | None = None,
    max_results: int = 8,
) -> list[PlaceCandidate]:
    """Discovery-only restaurant search near a coordinate. Returns
    PlaceCandidate objects (no menu contents — see module docstring). Empty
    list on: feature disabled, rate-limited, no API key, or a provider
    failure — callers must degrade to a friendly message, never a 500."""
    if not _places_enabled() or _rate_limited(athlete_id):
        return []

    query = (query_hint or "restaurant").strip() or "restaurant"

    try:
        raw_results = _fsq_search(lat, lon, radius_m, query, max_results * 2)
    except Exception:
        logger.exception("Foursquare nearby search failed")
        return []

    candidates = [c for c in (_parse_candidate(r) for r in raw_results) if c]

    # Widen BEFORE applying the open-now preference, so a wide-radius pass
    # can't reintroduce a closed place the base pass already filtered out.
    if len(candidates) < _MIN_RESULTS_BEFORE_WIDEN and radius_m < _WIDE_RADIUS_M:
        try:
            wider_raw = _fsq_search(lat, lon, _WIDE_RADIUS_M, query, max_results * 2)
            wider = [c for c in (_parse_candidate(r) for r in wider_raw) if c]
            seen_ids = {c.place_id for c in candidates}
            candidates.extend(c for c in wider if c.place_id not in seen_ids)
        except Exception:
            logger.exception("Foursquare wide-radius nearby search failed")

    # Prefer currently-open places, but don't zero out the list if that
    # leaves nothing — a closed-early stop is still a real, useful answer.
    open_candidates = [c for c in candidates if c.open_now is not False]
    if open_candidates:
        candidates = open_candidates

    candidates.sort(key=lambda c: (c.rating is None, -(c.rating or 0)))
    return candidates[:max_results]
