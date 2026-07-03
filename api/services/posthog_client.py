"""
PostHog Query API client — backend-only (the Personal API Key is a SECRET and is
never exposed to the browser). Replaces the old Mixpanel client; the admin
analytics router consumes the same function surface (is_configured,
signups_over_time, top_events, retention, discover_event_names, cached) so the
dashboard just gets a working data source underneath.

Config (os.getenv, graceful when unset — dashboard falls back to DB-only cards):
  POSTHOG_PROJECT_ID       — numeric project id (Project Settings → General)
  POSTHOG_PERSONAL_API_KEY — phx_... key scoped to Query Read (SECRET)
  POSTHOG_API_HOST         — private API host, e.g. https://us.posthog.com
                             (US Cloud). NOT the ingestion host (us.i.posthog.com).

Queries run via HogQL against POST {host}/api/projects/{id}/query/ with body
{"query": {"kind": "HogQLQuery", "query": "<SQL>"}}. Free-tier friendly: the
Query API allows ~2400 queries/hour and every result is cached for 15 min
(see cached()), so normal dashboard use is orders of magnitude under the limit.

Canonical event set (must match the mobile instrumentation):
"""

import os
import time

import requests

_TIMEOUT = 20

# The explicit events the mobile app fires. Used by /discover for reference.
CANONICAL_EVENTS = [
    "signup_completed", "athlete_created", "calendar_connected", "meal_plan_viewed",
    "event_added_manual", "problem_reported", "feature_idea_submitted", "app_opened",
]

# In-process cache: cache_key → (expires_at_epoch, data). 15-min TTL so dashboard
# refreshes never hammer the Query API.
_CACHE_TTL = 15 * 60
_cache: dict[str, tuple[float, dict]] = {}
# ?force=true floor: never allow a forced refresh more than once per minute.
_last_forced: dict[str, float] = {}
_FORCE_FLOOR = 60


def is_configured() -> bool:
    return bool(os.getenv("POSTHOG_PERSONAL_API_KEY") and os.getenv("POSTHOG_PROJECT_ID"))


def _host() -> str:
    return (os.getenv("POSTHOG_API_HOST") or "https://us.posthog.com").rstrip("/")


def cache_age_seconds(cache_key: str) -> float | None:
    entry = _cache.get(cache_key)
    if not entry:
        return None
    return max(0.0, _CACHE_TTL - (entry[0] - time.time()))


def _hogql(sql: str, name: str = "admin") -> list:
    """Run one HogQL query; return the `results` rows (list of lists). Raises
    requests.HTTPError on non-2xx (caught by cached())."""
    pid = os.getenv("POSTHOG_PROJECT_ID")
    key = os.getenv("POSTHOG_PERSONAL_API_KEY", "")
    resp = requests.post(
        f"{_host()}/api/projects/{pid}/query/",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"query": {"kind": "HogQLQuery", "query": sql}, "name": name},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def cached(cache_key: str, fetch, force: bool = False) -> dict:
    """Return {available, data|reason, as_of}. `fetch` is a zero-arg callable that
    performs the real query and returns JSON-able data. Missing creds / API errors
    degrade to {available: False, reason} so the dashboard never 500s."""
    if not is_configured():
        return {"available": False, "reason": "PostHog not connected"}

    now = time.time()
    if force:
        if now - _last_forced.get(cache_key, 0) < _FORCE_FLOOR:
            force = False  # respect the 1/min floor — serve cache instead
        else:
            _last_forced[cache_key] = now

    entry = _cache.get(cache_key)
    if entry and not force and entry[0] > now:
        return {"available": True, "data": entry[1], "as_of": _iso(now - (_CACHE_TTL - (entry[0] - now)))}

    try:
        data = fetch()
    except Exception as e:  # network / auth / rate limit
        if entry:  # serve stale cache rather than failing the dashboard
            return {"available": True, "data": entry[1], "as_of": _iso(now), "stale": True}
        return {"available": False, "reason": f"PostHog query failed: {_short(e)}"}

    _cache[cache_key] = (now + _CACHE_TTL, data)
    return {"available": True, "data": data, "as_of": _iso(now)}


def _short(e) -> str:
    resp = getattr(e, "response", None)
    if resp is not None:
        code = getattr(resp, "status_code", "?")
        if code in (401, 403):
            return "authentication failed (check Personal API Key + Query Read scope)"
        return f"HTTP {code}"
    return str(e)[:120]


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


# ── Shaped queries (return frontend-ready data under `data`) ──────────────────
def signups_over_time(days: int, force: bool = False) -> dict:
    days = int(days)

    def fetch():
        rows = _hogql(
            f"SELECT toDate(timestamp) AS d, count() AS c FROM events "
            f"WHERE event = 'signup_completed' AND timestamp > now() - INTERVAL {days} DAY "
            f"GROUP BY d ORDER BY d", name="signups_over_time")
        return {"points": [{"date": str(r[0]), "count": int(r[1])} for r in rows]}
    return cached(f"signups:{days}", fetch, force)


def top_events(days: int, force: bool = False) -> dict:
    days = int(days)

    def fetch():
        rows = _hogql(
            f"SELECT event, count() AS c FROM events "
            f"WHERE timestamp > now() - INTERVAL {days} DAY "
            f"GROUP BY event ORDER BY c DESC LIMIT 20", name="top_events")
        return {"rows": [{"event": r[0], "count": int(r[1])} for r in rows]}
    return cached(f"top_events:{days}", fetch, force)


def retention(weeks: int, force: bool = False) -> dict:
    """Weekly active users (distinct persons/week) — the WAU trend that stands in
    for cohort retention on the free tier."""
    weeks = int(weeks)

    def fetch():
        rows = _hogql(
            f"SELECT toStartOfWeek(timestamp) AS wk, count(DISTINCT person_id) AS c FROM events "
            f"WHERE timestamp > now() - INTERVAL {weeks} WEEK "
            f"GROUP BY wk ORDER BY wk", name="wau")
        return {"points": [{"week_start": str(r[0])[:10], "active": int(r[1])} for r in rows]}
    return cached(f"retention:{weeks}", fetch, force)


def discover_event_names(force: bool = False) -> dict:
    """List distinct event names actually firing, most frequent first."""
    def fetch():
        rows = _hogql(
            "SELECT event, count() AS c FROM events "
            "WHERE timestamp > now() - INTERVAL 30 DAY "
            "GROUP BY event ORDER BY c DESC LIMIT 50", name="discover")
        return {"events": [{"event": r[0], "count": int(r[1])} for r in rows]}
    return cached("discover", fetch, force)
