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
    # Fuel IQ (spec §13)
    "fuel_iq_viewed", "fuel_iq_lesson_start", "fuel_iq_lesson_complete",
    "fuel_iq_quiz_answer", "fuel_iq_perfect_quiz",
    "fuel_iq_streak_day", "fuel_iq_streak_milestone", "fuel_iq_badge_earned",
    # Fuel IQ Daily Challenge — separate feature, replaced fuel_iq_myth_verdict
    "fuel_iq_daily_challenge_verdict",
]

# Events shown in the live activity feed: the "who did what" actions only.
# Excludes high-frequency, low-signal pings that would flood the feed with
# anonymous/noisy rows — app_opened (no parent_id), fuel_iq_viewed (fires on
# every tab visit), fuel_iq_quiz_answer (up to 3/lesson), and fuel_iq_streak_day
# (fires on every qualifying activity, redundant with the milestone event).
# Derived from CANONICAL_EVENTS (single source).
_ACTIVITY_EXCLUDED = {"app_opened", "fuel_iq_viewed", "fuel_iq_quiz_answer", "fuel_iq_streak_day"}
ACTIVITY_EVENTS = [e for e in CANONICAL_EVENTS if e not in _ACTIVITY_EXCLUDED]

# In-process cache: cache_key → (expires_at_epoch, data). 15-min TTL so dashboard
# refreshes never hammer the Query API. The live activity feed passes a shorter
# TTL (_ACTIVITY_TTL) so it actually feels recent.
_CACHE_TTL = 15 * 60
_ACTIVITY_TTL = 60
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


def cached(cache_key: str, fetch, force: bool = False, ttl: int = _CACHE_TTL) -> dict:
    """Return {available, data|reason, as_of}. `fetch` is a zero-arg callable that
    performs the real query and returns JSON-able data. Missing creds / API errors
    degrade to {available: False, reason} so the dashboard never 500s. `ttl` is the
    cache lifetime in seconds (defaults to 15 min; the activity feed uses 60s)."""
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
        return {"available": True, "data": entry[1], "as_of": _iso(now - (ttl - (entry[0] - now)))}

    try:
        data = fetch()
    except Exception as e:  # network / auth / rate limit
        if entry:  # serve stale cache rather than failing the dashboard
            return {"available": True, "data": entry[1], "as_of": _iso(now), "stale": True}
        return {"available": False, "reason": f"PostHog query failed: {_short(e)}"}

    _cache[cache_key] = (now + ttl, data)
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


def recent_activity(limit: int = 20, force: bool = False) -> dict:
    """Newest canonical actions across all users (for the live activity feed).
    Returns raw rows under `data` — {event, timestamp, parent_id} — leaving
    parent_id → name resolution to the route (which has DB access). Filters to
    ACTIVITY_EVENTS, so noise events ($autocapture/$screen/etc.) never appear.
    Short 60s cache so it feels live."""
    limit = max(1, min(50, int(limit)))
    ev_list = "', '".join(ACTIVITY_EVENTS)  # fixed constants — no injection surface

    def fetch():
        rows = _hogql(
            f"SELECT event, timestamp, properties.parent_id AS parent_id FROM events "
            f"WHERE event IN ('{ev_list}') "
            f"ORDER BY timestamp DESC LIMIT {limit}", name="recent_activity")
        return {"rows": [{"event": r[0], "timestamp": str(r[1]), "parent_id": r[2]} for r in rows]}
    return cached(f"activity:{limit}", fetch, force, ttl=_ACTIVITY_TTL)


def discover_event_names(force: bool = False) -> dict:
    """List distinct event names actually firing, most frequent first."""
    def fetch():
        rows = _hogql(
            "SELECT event, count() AS c FROM events "
            "WHERE timestamp > now() - INTERVAL 30 DAY "
            "GROUP BY event ORDER BY c DESC LIMIT 50", name="discover")
        return {"events": [{"event": r[0], "count": int(r[1])} for r in rows]}
    return cached("discover", fetch, force)
