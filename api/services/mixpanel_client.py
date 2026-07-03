"""
Mixpanel Query API client — backend-only. The Mixpanel secret is NEVER exposed to
the browser; the admin dashboard renders shaped data from these functions.

Config (os.getenv, graceful when unset — dashboard falls back to DB-only cards):
  MIXPANEL_API_SECRET   — project API secret OR service-account secret (Basic auth)
  MIXPANEL_PROJECT_ID   — numeric project id (Project Settings → overview / URL)
  MIXPANEL_SA_USERNAME  — (optional) service-account username; if set, Basic auth
                          uses SA_USERNAME:API_SECRET instead of API_SECRET:''

Where to find these in Mixpanel: Project Settings → Overview (Project ID) and
Project Settings → Service Accounts (username + secret) or → Access Keys (API
secret). Set them as Fly secrets:
  flyctl secrets set MIXPANEL_API_SECRET=... MIXPANEL_PROJECT_ID=... --app fuelup-youth

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EVENT_MAP — funnel step → the ACTUAL Mixpanel event name.
The real event names are instrumented in the React Native app (a separate repo)
and are NOT visible from this backend. They are placeholders until discovered.
Discover them by hitting  GET /api/admin/analytics/discover  (calls the Query API
events/names endpoint) once MIXPANEL_API_SECRET is set, then edit the strings
below to match. This dict is the single place to adjust event names.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import time

import requests

QUERY_BASE = "https://mixpanel.com/api/query"
_TIMEOUT = 20

# funnel step key → Mixpanel event name (PLACEHOLDERS — see module docstring)
EVENT_MAP = {
    "signup": "Sign Up",
    "created_athlete": "Athlete Created",
    "connected_calendar": "Calendar Connected",
    "viewed_meal_plan": "Meal Plan Viewed",
}

# In-process cache: cache_key → (expires_at_epoch, data). 15-min TTL. The Query
# API is rate-limited (~60/hr) so we must not call it on every page refresh.
_CACHE_TTL = 15 * 60
_cache: dict[str, tuple[float, dict]] = {}
# ?force=true floor: never allow a forced refresh more than once per minute.
_last_forced: dict[str, float] = {}
_FORCE_FLOOR = 60


def is_configured() -> bool:
    return bool(os.getenv("MIXPANEL_API_SECRET"))


def _auth() -> tuple[str, str]:
    secret = os.getenv("MIXPANEL_API_SECRET", "")
    username = os.getenv("MIXPANEL_SA_USERNAME")
    return (username, secret) if username else (secret, "")


def _project_params() -> dict:
    pid = os.getenv("MIXPANEL_PROJECT_ID")
    return {"project_id": pid} if pid else {}


def cache_age_seconds(cache_key: str) -> float | None:
    entry = _cache.get(cache_key)
    if not entry:
        return None
    return max(0.0, _CACHE_TTL - (entry[0] - time.time()))


def _query(path: str, params: dict) -> dict | list:
    """Raw Query API call. Raises requests.HTTPError on non-2xx."""
    resp = requests.get(
        f"{QUERY_BASE}/{path}",
        params={**_project_params(), **params},
        auth=_auth(),
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def cached(cache_key: str, fetch, force: bool = False) -> dict:
    """Return {available, data|reason, as_of}. `fetch` is a zero-arg callable that
    performs the real Query API call and returns JSON-able data. Errors and missing
    creds degrade to {available: False, reason}."""
    if not is_configured():
        return {"available": False, "reason": "Mixpanel not connected"}

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
    except Exception as e:  # network error, auth error, rate limit, plan gate
        if entry:  # serve stale cache rather than failing the dashboard
            return {"available": True, "data": entry[1], "as_of": _iso(now), "stale": True}
        resp = getattr(e, "response", None)
        # 402 = the project's Mixpanel plan doesn't include Query API access.
        # Surface a clean, actionable reason instead of a raw HTTP error string.
        if resp is not None and getattr(resp, "status_code", None) == 402:
            return {"available": False, "plan_gated": True, "reason": "Requires Mixpanel paid plan"}
        return {"available": False, "reason": f"Mixpanel query failed: {e}"}

    _cache[cache_key] = (now + _CACHE_TTL, data)
    return {"available": True, "data": data, "as_of": _iso(now)}


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


# ── Shaped queries ───────────────────────────────────────────────────────────
def discover_event_names(force: bool = False) -> dict:
    """List the event names actually firing in the project (last 30d)."""
    def fetch():
        names = _query("events/names", {"type": "general", "limit": 255})
        return {"events": names}
    return cached("discover", fetch, force)


def signups_over_time(days: int, force: bool = False) -> dict:
    event = EVENT_MAP["signup"]

    def fetch():
        from_date, to_date = _date_range(days)
        return _query("segmentation", {
            "event": event, "from_date": from_date, "to_date": to_date, "unit": "day",
        })
    return cached(f"signups:{days}", fetch, force)


def top_events(days: int, force: bool = False) -> dict:
    def fetch():
        from_date, to_date = _date_range(days)
        # top events by volume over the window
        return _query("events", {
            "event": [], "type": "general", "unit": "day",
            "from_date": from_date, "to_date": to_date,
        })
    return cached(f"top_events:{days}", fetch, force)


def retention(weeks: int, force: bool = False) -> dict:
    def fetch():
        from_date, to_date = _date_range(weeks * 7)
        return _query("retention", {
            "from_date": from_date, "to_date": to_date,
            "retention_type": "birth", "interval_count": weeks, "unit": "week",
            "born_event": EVENT_MAP["signup"],
        })
    return cached(f"retention:{weeks}", fetch, force)


def _date_range(days: int) -> tuple[str, str]:
    to_epoch = time.time()
    from_epoch = to_epoch - days * 86400
    fmt = "%Y-%m-%d"
    return time.strftime(fmt, time.gmtime(from_epoch)), time.strftime(fmt, time.gmtime(to_epoch))
