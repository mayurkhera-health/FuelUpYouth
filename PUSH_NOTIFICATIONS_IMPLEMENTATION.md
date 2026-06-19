# Push Notifications — Backend Implementation Guide (v4)

---

## Verified Against Actual Code

Four items checked before this version was written.

### 1. `get_event_window_times()` — CONFIRMED
`api/services/window_engine_v2.py:867`. Returns `window_key`, `category`, `open_time`
(HH:MM 24h), `close_time`, `sort_time`, `window_type`, `is_tappable`, `priority`.

### 2. `window_logs` column is `window_id` NOT `slot_name`
Created lazily by `_ensure_window_logs_table()` in `today_service.py:663`.
Column: `window_id`. The suppress query in v2 used `slot_name` — would have silently never fired.

There is also a separate `confirmations` table (tap-based completions, `db_migrations.py:21`)
with column `window_key`. Both must be checked. See combined suppress query below.

### 3. Timezone — No athlete timezone stored anywhere
Fly.io runs UTC. Events store naive `start_time`. Engine produces naive `open_time` in local time.
No timezone on `athletes`, `events`, or `expo_push_tokens`. Fix required before building.

### 4. `notification_log` — Does not exist
Must be created. See schema below.

---

## Four Design Decisions (v4)

### Decision 1 — Suppress must check BOTH paths

The suppress-if-logged check uses a single combined query — not two separate checks that could
be bypassed if only one path fires:

```python
def already_logged(athlete_id: int, window_key: str, date_str: str, conn) -> bool:
    captured = conn.execute(
        "SELECT 1 FROM window_logs "
        "WHERE athlete_id = ? AND window_id = ? AND log_date = ? LIMIT 1",
        (athlete_id, window_key, date_str),
    ).fetchone()
    confirmed = conn.execute(
        "SELECT 1 FROM confirmations "
        "WHERE athlete_id = ? AND window_key = ? AND log_date = ? LIMIT 1",
        (athlete_id, window_key, date_str),
    ).fetchone()
    return bool(captured or confirmed)
```

Both must be checked every time. If either returns a row, suppress.

### Decision 2 — Pacific fallback is NOT silent

The fallback to `America/Los_Angeles` logs a WARNING and is a temporary measure only.
Every token registered before the `timezone` column is added has `None` timezone and will
silently use Pacific until re-registration.

**Fix: wire `registerTokenIfPermitted` into `app/_layout.tsx`.**
This function already exists in `services/notifications.ts:25` but is never called on app launch.
If it is called on every cold start — and the token payload includes `timezone` — then the DB
self-heals within one app open for every active user, without any manual backfill or forced
re-registration flow.

Mobile change required (in `services/notifications.ts`):
```ts
// Add timezone to every token registration call
const payload = {
  ...(profileType === "parent"
    ? { parent_id: profileId }
    : { athlete_id: profileId }),
  token:    token.data,
  platform: Platform.OS,
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,  // e.g. "America/Los_Angeles"
};
```

Mobile change required (in `app/_layout.tsx`):
```ts
// Call on every cold start — silent if permission not yet granted
useEffect(() => {
  if (session?.athleteId || session?.parentId) {
    registerTokenIfPermitted(profileId, profileType);
  }
}, []);
```

Backend change required:
```python
class ExpoTokenPayload(BaseModel):
    token:      str
    platform:   Optional[str] = None
    timezone:   Optional[str] = None   # IANA e.g. "America/Los_Angeles"
    athlete_id: Optional[int] = None
    parent_id:  Optional[int] = None
```

Scheduler behavior:
```python
import logging
from zoneinfo import ZoneInfo

FALLBACK_TZ = "America/Los_Angeles"

def resolve_timezone(tz_str: str | None) -> ZoneInfo:
    if not tz_str:
        logging.warning("expo_push_tokens.timezone is NULL — using Pacific fallback. "
                        "Ensure mobile app re-registers token with timezone on next launch.")
        return ZoneInfo(FALLBACK_TZ)
    return ZoneInfo(tz_str)
```

Until a non-Pacific pilot user exists, the silent fallback is acceptable. Before any expansion
beyond San Jose, CA, confirm all active tokens have a non-null timezone.

### Decision 3 — INSERT-before-send (prevents double-fire, may miss on crash)

Two failure modes exist:

| Order | Crash scenario | Result |
|---|---|---|
| Send → INSERT | Crash after send, before INSERT | **Double-fire on retry** |
| INSERT → Send | Crash after INSERT, before send | Silent miss on retry |

For a youth nutrition reminder app, a duplicate "eat now" push is more disruptive than a
missed one. **INSERT comes first.** The notification_log entry acts as a reservation:

```python
def send_notification_guarded(
    athlete_id: int, window_key: str, date_str: str,
    recipient: str, tokens: list[str], title: str, body: str, conn
) -> bool:
    """
    Returns True if the notification was sent.
    INSERT-before-send: prevents double-fire; a crash between INSERT and send
    causes a silent miss on re-run (acceptable for best-effort reminders).
    """
    try:
        conn.execute(
            "INSERT OR IGNORE INTO notification_log "
            "(athlete_id, window_key, send_date, recipient, token) VALUES (?, ?, ?, ?, ?)",
            (athlete_id, window_key, date_str, recipient, tokens[0] if tokens else ""),
        )
        conn.commit()
    except Exception:
        return False  # UNIQUE constraint fired — already sent

    # Row count == 0 means IGNORE fired (already sent)
    if conn.execute(
        "SELECT changes()"
    ).fetchone()[0] == 0:
        return False

    send_expo_push(tokens, title, body)
    return True
```

### Decision 5 — Rest Days: No Push (Deliberate)

On rest days `generate_windows_v2()` returns only `everyday` category windows (breakfast,
lunch, snack, dinner). These have rank 99 in `rank_for_notification()` and are excluded by
`select_notification_windows()`. The scheduler fires nothing.

**This is intentional.** Reasons:

- The in-app Today card already shows everyday meals with fueling context — no gap to fill.
- A rest-day push has nothing actionable behind it: no fuel window to open, no time-sensitive
  behaviour to change.
- Sending a notification with no clear action trains athletes to ignore pushes.

**If a rest-day nudge is added later it needs its own spec covering:**
- Trigger time (once in the morning? fixed at 09:00?)
- Frequency (every rest day, or only after consecutive event days?)
- Copy (needs dietitian review; the "gains happen on rest days" framing was never approved)
- A separate send path — it must NOT go through the window-based scheduler

Do not route rest-day notifications through `rank_for_notification()` or
`select_notification_windows()`. They would require a dedicated function, separate copy, and
a separate dedup key that doesn't collide with event-day window keys.

---

### Decision 4 — Copy Review

Copy is presented here for review before building.

**Content rules (same lens as all athlete-facing content):**
- Athlete copy: fueling-framed, performance language, first-person
- Parent copy: helpful reminder tone; never surveillance, tracking, or accusatory language
- No food names
- No calories, macros, or numbers
- Positive framing only — "fuel window open", not "you haven't eaten"

---

## Copy Strings (PENDING REVIEW)

### Athlete Stream

| Window | Title | Body |
|---|---|---|
| `pre_event_meal` (game) | "Pre-Game Meal" | "Your fuel window is open. Eat now — {event_name} starts at {start_time}." |
| `pre_event_meal` (training) | "Pre-Training Meal" | "Fuel up before your session. Your body will thank you." |
| `quick_morning_snack` | "Early Start" | "Light snack time before your early game. Keep it simple." |
| `fuel_after_primary` | "Recovery Window" | "Eat in the next 30 min. Your muscles are ready to recover." |
| `refuel_ready` | "Recover & Refuel" | "Recovery + fuel for your next session — both in one window." |
| `between_games` | "Quick Refuel" | "Short break — grab fast carbs and fluid before the next game." |
| rest day | "Rest Day" | "Regular meals today. This is where the gains happen." |

### Parent Stream

| Window | Title | Body |
|---|---|---|
| `pre_event_meal` (game) | "{first_name}'s Pre-Game Meal" | "This is the fuel window before {event_name}. A meal now sets them up for the game." |
| `pre_event_meal` (training) | "{first_name}'s Pre-Training Meal" | "Fuel window is open before {first_name}'s session." |
| `quick_morning_snack` | "Early Game for {first_name}" | "Early start today — a light snack before the game, then a proper meal after." |
| `fuel_after_primary` | "{first_name}'s Recovery Window" | "First 30 min after activity is the key recovery window — protein + carbs when ready." |
| `refuel_ready` | "Refuel for {first_name}" | "Between sessions — this is the window to recover and fuel up for what's next." |
| `between_games` | "Between Games" | "Short break between {first_name}'s games — quick carbs and fluid." |
| rest day | — | *(no parent notification on rest days)* |

**Notes for reviewer:**
- Parent copy says "this is the window" not "your child hasn't eaten" — it's a timing signal, not a status report
- "When ready" in recovery copy avoids implying the parent hasn't acted yet
- Rest days send to athlete only — no parent nudge, nothing to act on

---

## Architecture

```
Backend scheduler (every 15 min)
  → for each athlete with tokens
      → compute local now using athlete's timezone (from expo_push_tokens.timezone)
      → call generate_windows_v2() — same engine as Today + Meal Plan
      → get_event_window_times() → select top 2 by priority rank
      → for each selected window whose open_time is within ±8 min of local now:
          → skip if quiet hours (before 06:30 or after 22:00 local)
          → skip if already logged (window_logs.window_id OR confirmations.window_key)
          → INSERT-before-send to notification_log (dedup)
          → POST to Expo push API (athlete stream + parent stream separately)
```

---

## Token Streams

```sql
-- Athlete's own devices
SELECT token, timezone FROM expo_push_tokens WHERE athlete_id = :athlete_id

-- Parent's devices (for this athlete)
SELECT token, timezone FROM expo_push_tokens
WHERE parent_id = (SELECT parent_id FROM athletes WHERE id = :athlete_id)
```

---

## Guardrails

### Quiet Hours
```python
def in_quiet_hours(open_time: str) -> bool:
    return open_time < "06:30" or open_time >= "22:00"
```

### Daily Cap — Top 2 by Priority (per stream)

```python
def rank_for_notification(w: dict) -> int:
    if w["priority"]:                                                    return 0
    if w["category"] in ("fuel_before", "quick_snack") \
       and "top_up_snack" not in w["window_key"]:                        return 1
    if w["category"] in ("refuel_ready", "between_games"):               return 2
    if w["category"] == "fuel_after":                                    return 3
    return 99  # everyday, top-up, nudges — skip

DAILY_CAP = 2

def select_notification_windows(windows: list[dict]) -> list[dict]:
    eligible = [
        w for w in windows
        if w["is_tappable"]
        and not in_quiet_hours(w["open_time"])
        and rank_for_notification(w) < 99
    ]
    return sorted(eligible, key=lambda w: (rank_for_notification(w), w["sort_time"]))[:DAILY_CAP]
```

---

## Schema Changes Required

Add to `db_migrations.py`:

```python
def _create_notification_log(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id  INTEGER NOT NULL,
            window_key  TEXT    NOT NULL,
            send_date   TEXT    NOT NULL,
            recipient   TEXT    NOT NULL,   -- 'athlete' | 'parent'
            token       TEXT    NOT NULL,
            sent_at     TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (athlete_id, window_key, send_date, recipient)
        )
    """)

def _add_timezone_to_tokens(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(expo_push_tokens)").fetchall()]
    if "timezone" not in cols:
        conn.execute("ALTER TABLE expo_push_tokens ADD COLUMN timezone TEXT")
```

---

## What Changes Across Files

| File | Change |
|---|---|
| `api/services/db_migrations.py` | Add `_create_notification_log()` + `_add_timezone_to_tokens()` |
| `api/routes/notifications.py` | Add `timezone` to `ExpoTokenPayload`; replace `_send_push()` with `send_expo_push()` |
| `api/services/notification_service.py` | **New file** — scheduler, guardrails, copy, dedup |
| Mobile `services/notifications.ts` | Add `timezone` to token registration payload |
| Mobile `app/_layout.tsx` | Wire `registerTokenIfPermitted()` on cold start (fixes timezone backfill) |

---

## Critical Prerequisite: Dev Build Required

Expo Go no longer supports receiving push notifications as of SDK 53. This app runs SDK 54.
**A dev build must be issued before any end-to-end push testing:**

```bash
eas build --platform ios --profile development
```

---

## Dependencies

- `requests` — add to `requirements.txt` if not present
- `zoneinfo` — Python 3.9+ stdlib, available on Fly.io Python 3.11
- `APScheduler` — for 15-min cron, or Fly.io Machines cron
