"""
Recurring calendar sync — BYGA + PlayMetrics .ics feeds.

A background APScheduler job (`run_calendar_sync_tick`, registered in api/main.py)
fetches every athlete's stored .ics subscription URL(s) and reconciles the feed
into the `events` table: INSERT new games/practices, UPDATE ones whose time or
place changed, and DELETE future ones that vanished from the feed (a cancelled or
removed game). Every mutation calls `on_event_added_or_changed` so the fuel-window
engine regenerates that day's Today / Meal-Plan windows — exactly like the manual
POST/PUT/DELETE /events routes do.

Design mirrors the client-side importer (mobile utils/icsImport.ts) so a synced
event classifies identically to a hand-imported one, with two server-only guards:

  * "Past" is judged in each event's own TZID (Option 1A) with a 24h buffer, since
    a background job has no client timezone and Fly runs UTC.
  * The DELETE phase only removes FUTURE events (event_date >= cutoff) whose source
    matches the feed, and is skipped entirely when a fetch fails or the feed has no
    VEVENTs — so a transient/empty feed can never wipe the athlete's schedule, and
    manual events (source='manual') are never touched.
"""

import logging
import threading
from datetime import datetime, timedelta, timezone, date

import httpx
from icalendar import Calendar

from api.database import get_conn
from api.services.window_templates import on_event_added_or_changed
from api.services.nutrition_calc import derive_intensity

logger = logging.getLogger(__name__)

# How far back an event may sit before it's "past". A full day comfortably covers
# any client-vs-UTC offset, so we never delete a today/yesterday event over tz skew.
_PAST_BUFFER = timedelta(hours=24)

_PLATFORMS = ("byga", "playmetrics")


# ─── URL + fetch ──────────────────────────────────────────────────────────────
def normalize_calendar_url(url: str) -> str:
    """webcal(s):// is just http(s) under the calendar scheme — normalize so httpx
    can fetch it. Mirrors normalizeCalendarUrl / the fetch-ics proxy."""
    u = (url or "").strip()
    if u.startswith("webcal://"):
        return "https://" + u[len("webcal://"):]
    if u.startswith("webcals://"):
        return "https://" + u[len("webcals://"):]
    return u


def fetch_ics_text(url: str) -> str:
    """Fetch raw ICS text. Raises on network / HTTP error — callers treat any raise
    as a failed feed and SKIP the delete phase (never wipe on a transient failure)."""
    fetch_url = normalize_calendar_url(url)
    if not fetch_url.startswith("http"):
        raise ValueError(f"Invalid calendar URL: {url!r}")
    resp = httpx.get(fetch_url, timeout=15, headers={"User-Agent": "FuelUp/1.0"},
                     follow_redirects=True)
    resp.raise_for_status()
    return resp.text


# ─── Parsing ──────────────────────────────────────────────────────────────────
def guess_event_type(summary: str) -> str:
    """Map a VEVENT summary to a FuelUp event_type. Kept in lockstep with
    guessEventType in mobile utils/icsImport.ts so client + server agree."""
    s = (summary or "").lower()
    if "game" in s or "match" in s:
        return "game"
    if "tournament" in s or "tourney" in s:
        return "tournament"
    if "rest" in s or "off" in s or "recovery" in s:
        return "rest"
    if "strength" in s or "gym" in s or "lift" in s:
        return "strength"
    return "practice"


def _is_cancelled(vevent, summary: str) -> bool:
    # PlayMetrics double-signals: STATUS:CANCELLED *and* a "CANCELED " summary
    # prefix. Check both (matches the TS /^cancell?ed\b/i check).
    status = str(vevent.get("status", "")).upper()
    if status == "CANCELLED":
        return True
    head = (summary or "").strip().lower()
    return head.startswith("cancelled") or head.startswith("canceled")


def _as_utc(dt) -> datetime:
    """Coerce a VEVENT datetime to an aware UTC datetime for past-comparison. A
    TZID-bearing dt is converted from its own zone (Option 1A); a floating/naive
    dt is assumed UTC (conservative — at worst imports a barely-past event)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _vevent_to_event(vevent, cutoff_utc: datetime) -> dict | None:
    """Convert one VEVENT to an event dict, or None if it should be skipped
    (malformed / all-day / cancelled / past). Skip order matches icsImport.ts.

    event_date / start_time use the event's OWN local wall clock (its TZID), which
    is how the app stores + reasons about schedule times — not a UTC conversion."""
    uid = str(vevent.get("uid") or "").strip()
    summary = str(vevent.get("summary") or "").strip() or "Event"
    dtstart = vevent.get("dtstart")
    if not uid or dtstart is None:
        return None

    start = dtstart.dt
    # All-day entries (date, not datetime) carry no usable start time for the
    # window engine — SUMMER BREAK / OFF WEEKEND. Treat as unsupported.
    if isinstance(start, date) and not isinstance(start, datetime):
        return None

    if _is_cancelled(vevent, summary):
        return None

    # Past check in the event's own zone, with a 24h buffer.
    dtend = vevent.get("dtend")
    end = dtend.dt if dtend is not None else start
    if isinstance(end, date) and not isinstance(end, datetime):
        end = start
    if _as_utc(end) < cutoff_utc:
        return None

    # Local wall-clock date/time from the event's TZID (aware) or as-written (naive).
    event_date = start.strftime("%Y-%m-%d")
    start_time = start.strftime("%H:%M")

    # Duration: prefer DTEND, clamp to the same 0.5–8h band the client uses.
    duration_hours = 1.5
    try:
        if dtend is not None and isinstance(end, datetime) and isinstance(start, datetime):
            diff_h = (end - start).total_seconds() / 3600.0
            if diff_h > 0:
                duration_hours = diff_h
    except Exception:
        pass
    duration_hours = max(0.5, min(8.0, round(duration_hours * 2) / 2))

    location = str(vevent.get("location") or "").strip()
    city = location.split(",")[0].strip() if location else None

    return {
        "uid": uid,
        "event_name": summary,
        "event_type": guess_event_type(summary),
        "event_date": event_date,
        "start_time": start_time,
        "duration_hours": duration_hours,
        "city": city,
        "venue_name": location or None,
    }


def parse_feed(ics_text: str, cutoff_utc: datetime) -> dict[str, dict]:
    """Parse ICS text → {uid: event_dict} of the FUTURE, non-cancelled, timed events
    the feed wants on the schedule. Raises if the text isn't a calendar (callers
    treat a raise as a failed feed → skip delete). Last-write-wins on duplicate UIDs
    within one feed."""
    if "BEGIN:VCALENDAR" not in ics_text:
        raise ValueError("Not an ICS calendar (no VCALENDAR).")
    cal = Calendar.from_ical(ics_text)
    desired: dict[str, dict] = {}
    for comp in cal.walk("VEVENT"):
        try:
            ev = _vevent_to_event(comp, cutoff_utc)
        except Exception:
            logger.debug("Skipping malformed VEVENT", exc_info=True)
            continue
        if ev:
            desired[ev["uid"]] = ev
    return desired


# ─── Reconcile ────────────────────────────────────────────────────────────────
_SYNC_FIELDS = ("event_name", "event_type", "event_date", "start_time",
                "duration_hours", "city", "venue_name")


def _needs_update(existing: dict, desired: dict) -> bool:
    for f in _SYNC_FIELDS:
        if (existing.get(f) or None) != (desired.get(f) or None):
            return True
    return False


def sync_platform(conn, athlete_id: int, platform: str, ics_url: str,
                  competition_level: str | None) -> dict:
    """Fetch + reconcile one athlete's feed for one platform. Returns a counts dict
    for logging. Never raises — a bad feed is logged and skipped so one athlete's
    broken link can't abort the whole tick."""
    counts = {"inserted": 0, "updated": 0, "deleted": 0, "feed": 0, "error": None}
    now_utc = datetime.now(timezone.utc)
    cutoff_utc = now_utc - _PAST_BUFFER
    cutoff_date = (now_utc - _PAST_BUFFER).strftime("%Y-%m-%d")

    # 1. Fetch + parse. ANY failure here → skip reconcile entirely (no deletes).
    try:
        ics_text = fetch_ics_text(ics_url)
        desired = parse_feed(ics_text, cutoff_utc)
    except Exception as exc:
        counts["error"] = str(exc)
        logger.warning("Calendar fetch/parse failed (athlete %s, %s): %s",
                       athlete_id, platform, exc)
        return counts
    counts["feed"] = len(desired)

    # 2. Existing synced rows for this athlete + platform.
    existing_rows = conn.execute(
        "SELECT * FROM events WHERE athlete_id = ? AND source = ?",
        (athlete_id, platform),
    ).fetchall()
    existing = {r["uid"]: dict(r) for r in existing_rows if r["uid"]}
    now_iso = now_utc.isoformat()
    affected_dates: set[str] = set()

    # 3. INSERT + UPDATE.
    for uid, ev in desired.items():
        intensity = derive_intensity(ev["event_type"], competition_level)
        if uid not in existing:
            try:
                conn.execute(
                    "INSERT INTO events (athlete_id, event_name, event_type, event_date, "
                    "start_time, duration_hours, city, venue_name, intensity, uid, source, synced_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (athlete_id, ev["event_name"], ev["event_type"], ev["event_date"],
                     ev["start_time"], ev["duration_hours"], ev["city"], ev["venue_name"],
                     intensity, uid, platform, now_iso),
                )
                counts["inserted"] += 1
                affected_dates.add(ev["event_date"])
            except Exception:
                # Partial unique index (athlete_id, uid) — e.g. same UID already
                # synced under the other platform. Leave it; log and move on.
                logger.debug("Insert skipped for uid %s", uid, exc_info=True)
        else:
            cur = existing[uid]
            if _needs_update(cur, ev):
                conn.execute(
                    "UPDATE events SET event_name=?, event_type=?, event_date=?, start_time=?, "
                    "duration_hours=?, city=?, venue_name=?, intensity=?, synced_at=? WHERE id=?",
                    (ev["event_name"], ev["event_type"], ev["event_date"], ev["start_time"],
                     ev["duration_hours"], ev["city"], ev["venue_name"], intensity, now_iso, cur["id"]),
                )
                counts["updated"] += 1
                affected_dates.add(ev["event_date"])
                if cur["event_date"] != ev["event_date"]:
                    affected_dates.add(cur["event_date"])  # recompute the vacated day too

    # 4. DELETE — future-only, source-scoped. A synced event that dropped out of the
    #    feed (cancelled / removed) and is dated today-or-later gets removed. Past
    #    events (< cutoff) are preserved as history; manual events are never here.
    for uid, cur in existing.items():
        if uid not in desired and (cur["event_date"] or "") >= cutoff_date:
            conn.execute("DELETE FROM events WHERE id = ?", (cur["id"],))
            counts["deleted"] += 1
            affected_dates.add(cur["event_date"])

    conn.commit()

    # 5. Regenerate fuel windows once per touched day (idempotent full recompute).
    for d in affected_dates:
        try:
            on_event_added_or_changed(athlete_id, d, conn)
        except Exception:
            logger.warning("Window recompute failed (athlete %s, %s)", athlete_id, d, exc_info=True)
    conn.commit()

    if counts["inserted"] or counts["updated"] or counts["deleted"]:
        logger.info("Calendar sync %s/%s: +%d ~%d -%d (feed=%d)", athlete_id, platform,
                    counts["inserted"], counts["updated"], counts["deleted"], counts["feed"])
    return counts


def run_calendar_sync_tick() -> None:
    """APScheduler entrypoint — sync every athlete that has connected a feed. One DB
    connection for the whole tick (mirrors run_notification_tick)."""
    conn = get_conn()
    attempted = succeeded = 0
    try:
        rows = conn.execute(
            "SELECT id, competition_level, byga_ics_url, playmetrics_ics_url FROM athletes "
            "WHERE byga_ics_url IS NOT NULL OR playmetrics_ics_url IS NOT NULL"
        ).fetchall()
        logger.info("Calendar sync tick: %d athlete(s) with feeds", len(rows))
        for row in rows:
            urls = {"byga": row["byga_ics_url"], "playmetrics": row["playmetrics_ics_url"]}
            for platform in _PLATFORMS:
                if urls[platform]:
                    attempted += 1
                    try:
                        counts = sync_platform(conn, row["id"], platform, urls[platform], row["competition_level"])
                        if not counts.get("error"):
                            succeeded += 1
                    except Exception:
                        logger.exception("Calendar sync crashed (athlete %s, %s)", row["id"], platform)
    finally:
        conn.close()
        # Feed the System Health calendar_sync_systemic check (systemic = a whole-
        # provider outage). Best-effort; must not affect sync behavior.
        try:
            from api.services.health_service import record_calendar_sync_stats
            record_calendar_sync_stats(attempted, succeeded)
        except Exception:
            pass


# ── Startup catch-up (Option B) ──────────────────────────────────────────────
# In-memory APScheduler timers reset on every deploy/restart, so a mid-cycle restart
# otherwise pushes the next 6-h run up to 6 h past schedule and trips the 420-min
# calendar-sync alert. On startup we either run one catch-up (stale/initial) or
# re-anchor the interval's first run to last_success + 6h (fresh). Notifications
# (15-min cadence) is unaffected and untouched.

_CALSYNC_LOCK = threading.Lock()


def _with_calsync_lock(fn):
    """Wrap a job callable in a non-blocking skip-if-running lock so the startup
    catch-up and the 6-h interval can never execute concurrently (they share the same
    underlying tick). The lock sits OUTSIDE instrument_job, so a skipped trigger stamps
    no heartbeat."""
    def wrapper():
        if not _CALSYNC_LOCK.acquire(blocking=False):
            logger.info("calendar_sync already running — skipping this trigger")
            return
        try:
            fn()
        finally:
            _CALSYNC_LOCK.release()
    wrapper.__name__ = getattr(fn, "__name__", "calendar_sync") + "_locked"
    return wrapper


def build_calendar_sync_job():
    """The callable registered as the 6-h interval AND reused for the startup catch-up:
    instrument_job (stamps heartbeats) wrapped in the skip-if-running lock."""
    from api.services.health_service import instrument_job
    return _with_calsync_lock(instrument_job("calendar_sync", run_calendar_sync_tick))


def configure_calendar_sync_startup(scheduler) -> None:
    """Option B startup handling for calendar_sync ONLY. Call once, after the 6-h
    interval job is registered and the scheduler is started.

      • initial (no prior successful run): claim + run ONE immediate sync;
        log 'no prior run — running initial sync'.
      • stale (> 6 h since last success): claim + run ONE immediate catch-up.
      • fresh (<= 6 h): re-anchor the interval's FIRST run to last_success + 6h so a
        sub-cadence restart resumes the original schedule instead of restarting the
        6-h clock. Re-anchor is applied ONLY here — a past-dated next_run_time in the
        initial/stale branches would make APScheduler fire the interval immediately
        alongside the catch-up (a double run)."""
    from api.services import health_service as hs
    conn = get_conn()
    try:
        branch, mins, last_success = hs.calendar_sync_freshness(conn)

        if branch == "fresh":
            anchor = datetime.fromisoformat(last_success).replace(tzinfo=timezone.utc) + timedelta(hours=6)
            try:
                scheduler.modify_job("calendar_sync", next_run_time=anchor)
                logger.info("calendar_sync fresh (%.0fm ago) — next run anchored to "
                            "last_success + 6h (%s)", mins, anchor.isoformat())
            except Exception:
                logger.exception("calendar_sync: failed to re-anchor next_run_time — "
                                 "leaving default interval schedule")
            return

        # initial or stale → claim exactly one catch-up (multi-instance safe)
        if not hs.claim_calendar_sync_catchup(conn):
            logger.info("calendar_sync %s but a run was already claimed/in progress — skipping catch-up", branch)
            return

        scheduler.add_job(
            build_calendar_sync_job(), "date",
            run_date=datetime.now(timezone.utc),
            id="calendar_sync_catchup", replace_existing=True,
            max_instances=1, coalesce=True,
        )
        if branch == "initial":
            logger.info("calendar_sync: no prior run — running initial sync")
        else:
            logger.info("calendar_sync stale (%.0fm > %dm) — running catch-up now",
                        mins, hs.CALSYNC_CADENCE_MIN)
    finally:
        conn.close()
