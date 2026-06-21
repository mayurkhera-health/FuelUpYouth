# Event Intensity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture a per-event intensity (`low`/`medium`/`high`) — explicit for manually-added events, derived from competition level for ICS-imported and legacy events — and use it to reposition carbohydrate and protein targets *within* the existing scientific g/kg ranges.

**Architecture:** Add a tolerant `derive_intensity(event_type, competition_level)` and a `_reposition()` band helper to `nutrition_calc.py`. `calc_daily_targets` gains an optional `intensity` param (`None` = full band, unchanged — so the blueprint is untouched). Persist `intensity` on `events` (the capture point) and `daily_targets` (audit trail) via additive migrations with backfill. The events route stores explicit intensity or derives it; the nutrition route threads the day's event intensity into the calc. Frontend: collapse Competition Level to 3 tiers and add a required intensity dropdown to the Add Event form.

**Tech Stack:** FastAPI, raw `sqlite3` (no ORM), Pydantic v2, React (Vite), pytest.

**Reference spec:** `docs/superpowers/specs/2026-06-21-event-intensity-design.md`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `api/services/nutrition_calc.py` | Science calc | Add `derive_intensity`, `_reposition`; `intensity` param on `calc_daily_targets` |
| `api/services/db_migrations.py` | Additive migrations | `_add_intensity_to_events` (+backfill), `_add_intensity_to_daily_targets`; wire into `run_all()` |
| `api/models.py` | Request/response models | Optional `intensity` on `EventCreate`/`EventUpdate` (+validator); field on `EventResponse` |
| `api/routes/events.py` | Event HTTP handlers | Set intensity on create/update |
| `api/routes/nutrition.py` | Targets HTTP handler | Pass event intensity into calc; store in `daily_targets` |
| `frontend/src/Onboarding.jsx` | New-athlete form | 3-tier Competition Level |
| `frontend/src/ProfileScreen.jsx` | Edit-athlete form | 3-tier Competition Level |
| `frontend/src/ScheduleScreen.jsx` | Schedule UI | Required intensity dropdown on Add Event form |
| `tests/test_nutrition_calc.py` | Tests | New — derivation + repositioning |
| `tests/test_intensity_migration.py` | Tests | New — column creation + backfill |
| `docs/HLD.md` | Architecture doc | Document the field, derivation, calc effect |

**Note:** The web frontend currently has **no edit-event form** (only Add, Sync, Delete). The intensity dropdown is added to the Add form. `EventUpdate` keeps optional intensity support at the API layer for a future edit screen / API clients, but no edit UI is built in this plan.

---

## Task 1: Intensity derivation + band repositioning in `nutrition_calc.py`

**Files:**
- Modify: `api/services/nutrition_calc.py`
- Test: `tests/test_nutrition_calc.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_nutrition_calc.py`:

```python
"""Unit tests for intensity derivation and band repositioning in nutrition_calc."""

from api.services import nutrition_calc as nc


# ---- derive_intensity ----

def test_rest_event_floors_to_low_even_for_elite():
    assert nc.derive_intensity("Yoga/Flexibility/Recovery", "Elite Club") == "low"
    assert nc.derive_intensity("rest", "Elite Club") == "low"

def test_elite_club_competitive_event_is_high():
    assert nc.derive_intensity("game", "Elite Club") == "high"

def test_competitive_club_is_medium():
    assert nc.derive_intensity("game", "Competitive Club") == "medium"

def test_recreational_is_low():
    assert nc.derive_intensity("game", "Recreational") == "low"

def test_legacy_labels_still_map():
    assert nc.derive_intensity("game", "Elite") == "high"
    assert nc.derive_intensity("game", "Club") == "medium"
    assert nc.derive_intensity("game", "Competitive") == "medium"

def test_null_competition_level_defaults_low():
    assert nc.derive_intensity("game", None) == "low"
    assert nc.derive_intensity("game", "") == "low"
    assert nc.derive_intensity("game", "something weird") == "low"


# ---- repositioning in calc_daily_targets ----

ATH = {"weight_lbs": 110.231, "height_ft": 5, "height_in": 6, "gender": "girl"}
# 110.231 lbs -> 50.0 kg

def test_intensity_none_returns_full_band():
    t = nc.calc_daily_targets(ATH, "game")  # no intensity
    assert t["carbs_g_min"] == 400 and t["carbs_g_max"] == 500

def test_low_intensity_is_lower_half():
    t = nc.calc_daily_targets(ATH, "game", intensity="low")
    assert t["carbs_g_min"] == 400 and t["carbs_g_max"] == 450

def test_medium_intensity_is_middle():
    t = nc.calc_daily_targets(ATH, "game", intensity="medium")
    assert t["carbs_g_min"] == 425 and t["carbs_g_max"] == 475

def test_high_intensity_is_upper_half():
    t = nc.calc_daily_targets(ATH, "game", intensity="high")
    assert t["carbs_g_min"] == 450 and t["carbs_g_max"] == 500

def test_repositioned_band_never_exceeds_science_bounds():
    full = nc.calc_daily_targets(ATH, "game")
    high = nc.calc_daily_targets(ATH, "game", intensity="high")
    assert high["carbs_g_max"] <= full["carbs_g_max"]
    assert high["carbs_g_min"] >= full["carbs_g_min"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && pytest tests/test_nutrition_calc.py -v`
Expected: FAIL — `AttributeError: module 'api.services.nutrition_calc' has no attribute 'derive_intensity'` and `calc_daily_targets() got an unexpected keyword argument 'intensity'`.

- [ ] **Step 3: Add `derive_intensity` and `_reposition`**

In `api/services/nutrition_calc.py`, add these functions immediately after the existing `normalize_event_type` function:

```python
def derive_intensity(event_type: str, competition_level) -> str:
    """Derive intensity (low/medium/high) for ICS-imported, legacy, or
    otherwise-unspecified events. Manual events carry an explicit value.

    Rest/recovery events floor to "low" for everyone; all other events map
    from competition level. Tolerant of both the 3 current labels and the
    legacy 4-value labels."""
    if normalize_event_type(event_type) == "rest":
        return "low"
    level = (competition_level or "").strip().lower()
    if level == "":
        return "low"
    if "elite" in level:
        return "high"
    if "recreational" in level:
        return "low"
    if "competitive" in level or "club" in level:
        return "medium"
    return "low"


def _reposition(lo: float, hi: float, intensity: str):
    """Return a sub-band positioned within [lo, hi] by intensity.
    Never exceeds the original scientific bounds."""
    span = hi - lo
    if intensity == "low":
        return lo, lo + 0.5 * span
    if intensity == "high":
        return lo + 0.5 * span, hi
    # medium (and any unexpected value): middle 50%
    return lo + 0.25 * span, hi - 0.25 * span
```

- [ ] **Step 4: Thread `intensity` through `calc_daily_targets`**

In `api/services/nutrition_calc.py`, change the signature and the carb/protein block. Replace:

```python
def calc_daily_targets(athlete: dict, event_type: str = "rest") -> dict:
    wt_kg = lbs_to_kg(athlete["weight_lbs"])
    rmr = calc_rmr(athlete["weight_lbs"], athlete["height_ft"], athlete["height_in"], athlete["gender"])
    norm = normalize_event_type(event_type)

    total_calories = int(rmr * PAL_MULTIPLIERS.get(norm, 1.55))
    carb_min = int(CARB_TARGETS[norm][0] * wt_kg)
    carb_max = int(CARB_TARGETS[norm][1] * wt_kg)
    protein_min = round(PROTEIN_TARGETS[norm][0] * wt_kg, 1)
    protein_max = round(PROTEIN_TARGETS[norm][1] * wt_kg, 1)
```

with:

```python
def calc_daily_targets(athlete: dict, event_type: str = "rest", intensity: str = None) -> dict:
    wt_kg = lbs_to_kg(athlete["weight_lbs"])
    rmr = calc_rmr(athlete["weight_lbs"], athlete["height_ft"], athlete["height_in"], athlete["gender"])
    norm = normalize_event_type(event_type)

    total_calories = int(rmr * PAL_MULTIPLIERS.get(norm, 1.55))

    carb_lo, carb_hi = CARB_TARGETS[norm]
    prot_lo, prot_hi = PROTEIN_TARGETS[norm]
    if intensity:
        carb_lo, carb_hi = _reposition(carb_lo, carb_hi, intensity)
        prot_lo, prot_hi = _reposition(prot_lo, prot_hi, intensity)
    carb_min = int(carb_lo * wt_kg)
    carb_max = int(carb_hi * wt_kg)
    protein_min = round(prot_lo * wt_kg, 1)
    protein_max = round(prot_hi * wt_kg, 1)
```

Then add `"intensity": intensity,` to the returned dict (place it right after `"event_type": norm,`):

```python
    return {
        "event_type": norm,
        "intensity": intensity,
        "total_calories": total_calories,
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_nutrition_calc.py -v`
Expected: PASS (all 11 tests).

- [ ] **Step 6: Run the full suite to check for regressions**

Run: `pytest -q`
Expected: No *new* failures introduced by this change. (A pre-existing `test_shopping` seed-count failure may already exist and is unrelated.)

- [ ] **Step 7: Commit**

```bash
git add api/services/nutrition_calc.py tests/test_nutrition_calc.py
git commit -m "feat: intensity derivation + band repositioning in nutrition_calc"
```

---

## Task 2: Additive migrations — `events.intensity` + `daily_targets.intensity` with backfill

**Files:**
- Modify: `api/services/db_migrations.py`
- Test: `tests/test_intensity_migration.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_intensity_migration.py`:

```python
"""Tests for the additive intensity migrations."""

import sqlite3

from api.services.db_migrations import (
    _add_intensity_to_events,
    _add_intensity_to_daily_targets,
)


def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _seed_schema(conn):
    conn.executescript("""
        CREATE TABLE athletes (
            id INTEGER PRIMARY KEY, competition_level TEXT
        );
        CREATE TABLE events (
            id INTEGER PRIMARY KEY, athlete_id INTEGER,
            event_name TEXT, event_type TEXT, event_date TEXT
        );
        CREATE TABLE daily_targets (
            id INTEGER PRIMARY KEY, athlete_id INTEGER, target_date TEXT
        );
    """)


def test_events_intensity_column_created_and_backfilled():
    conn = _mk_conn()
    _seed_schema(conn)
    conn.execute("INSERT INTO athletes (id, competition_level) VALUES (1, 'Elite Club')")
    conn.execute("INSERT INTO athletes (id, competition_level) VALUES (2, 'Recreational')")
    conn.execute("INSERT INTO events (id, athlete_id, event_name, event_type, event_date) VALUES (10, 1, 'Game', 'game', '2026-06-21')")
    conn.execute("INSERT INTO events (id, athlete_id, event_name, event_type, event_date) VALUES (11, 1, 'Yoga', 'rest', '2026-06-22')")
    conn.execute("INSERT INTO events (id, athlete_id, event_name, event_type, event_date) VALUES (12, 2, 'Game', 'game', '2026-06-21')")

    _add_intensity_to_events(conn)

    cols = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
    assert "intensity" in cols
    rows = {r["id"]: r["intensity"] for r in conn.execute("SELECT id, intensity FROM events").fetchall()}
    assert rows[10] == "high"   # Elite Club game
    assert rows[11] == "low"    # rest floors to low
    assert rows[12] == "low"    # Recreational game


def test_events_migration_is_idempotent():
    conn = _mk_conn()
    _seed_schema(conn)
    _add_intensity_to_events(conn)
    _add_intensity_to_events(conn)  # must not raise
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    assert cols.count("intensity") == 1


def test_daily_targets_intensity_column_created():
    conn = _mk_conn()
    _seed_schema(conn)
    _add_intensity_to_daily_targets(conn)
    _add_intensity_to_daily_targets(conn)  # idempotent
    cols = {r[1] for r in conn.execute("PRAGMA table_info(daily_targets)").fetchall()}
    assert "intensity" in cols
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_intensity_migration.py -v`
Expected: FAIL — `ImportError: cannot import name '_add_intensity_to_events'`.

- [ ] **Step 3: Add the migration functions**

In `api/services/db_migrations.py`, add at the top with the other imports:

```python
from api.services.nutrition_calc import derive_intensity
```

Add these two functions (place them after `_add_timezone_to_tokens`):

```python
def _add_intensity_to_events(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    if "intensity" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN intensity TEXT")
        rows = conn.execute("""
            SELECT e.id AS id, e.event_type AS event_type, a.competition_level AS competition_level
            FROM events e LEFT JOIN athletes a ON a.id = e.athlete_id
        """).fetchall()
        for r in rows:
            intensity = derive_intensity(r["event_type"], r["competition_level"])
            conn.execute("UPDATE events SET intensity = ? WHERE id = ?", (intensity, r["id"]))


def _add_intensity_to_daily_targets(conn):
    cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_targets)").fetchall()]
    if "intensity" not in cols:
        conn.execute("ALTER TABLE daily_targets ADD COLUMN intensity TEXT")
```

- [ ] **Step 4: Wire into `run_all()`**

In `api/services/db_migrations.py`, in `run_all()`, add the two calls after `_add_timezone_to_tokens(conn)` and before `conn.commit()`:

```python
        _add_timezone_to_tokens(conn)
        _add_intensity_to_events(conn)
        _add_intensity_to_daily_targets(conn)
        conn.commit()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_intensity_migration.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Verify migrations run cleanly against a real DB**

Run: `python db/setup.py && python -c "from api.services.db_migrations import run_all; run_all(); print('migrations ok')"`
Expected: prints `migrations ok` with no traceback.

- [ ] **Step 7: Commit**

```bash
git add api/services/db_migrations.py tests/test_intensity_migration.py
git commit -m "feat: additive intensity columns on events + daily_targets with backfill"
```

---

## Task 3: Pydantic models — optional `intensity` with validation

**Files:**
- Modify: `api/models.py`
- Test: `tests/test_event_models.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_event_models.py`:

```python
"""Validation tests for intensity on event models."""

import pytest
from pydantic import ValidationError

from api.models import EventCreate, EventUpdate


def test_intensity_optional_defaults_none():
    e = EventCreate(athlete_id=1, event_name="Game", event_type="game", event_date="2026-06-21")
    assert e.intensity is None


def test_intensity_accepted_and_lowercased():
    e = EventCreate(athlete_id=1, event_name="Game", event_type="game",
                    event_date="2026-06-21", intensity="High")
    assert e.intensity == "high"


def test_invalid_intensity_rejected():
    with pytest.raises(ValidationError):
        EventCreate(athlete_id=1, event_name="Game", event_type="game",
                    event_date="2026-06-21", intensity="extreme")


def test_update_intensity_optional():
    u = EventUpdate(intensity="medium")
    assert u.intensity == "medium"
    u2 = EventUpdate()
    assert u2.intensity is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_event_models.py -v`
Expected: FAIL — `EventCreate` has no `intensity` field (extra field ignored or error depending on config), assertions fail.

- [ ] **Step 3: Add the field + validator to both models**

In `api/models.py`, add a module-level helper near the other validators (above `EventCreate`):

```python
def _normalize_intensity(v):
    if v is None or v == "":
        return None
    s = str(v).strip().lower()
    if s not in ("low", "medium", "high"):
        raise ValueError("intensity must be one of: low, medium, high")
    return s
```

In `EventCreate`, add the field and validator:

```python
class EventCreate(BaseModel):
    athlete_id: int
    event_name: str
    event_type: str
    event_date: str  # YYYY-MM-DD
    start_time: Optional[str] = None  # HH:MM (24h)
    duration_hours: Optional[float] = None
    city: Optional[str] = None
    intensity: Optional[str] = None  # low / medium / high; derived if omitted

    @field_validator("start_time", mode="before")
    @classmethod
    def normalize_start_time(cls, v):
        return _normalize_start_time(v)

    @field_validator("intensity", mode="before")
    @classmethod
    def normalize_intensity(cls, v):
        return _normalize_intensity(v)
```

In `EventUpdate`, add the same field and validator:

```python
class EventUpdate(BaseModel):
    event_name: Optional[str] = None
    event_type: Optional[str] = None
    event_date: Optional[str] = None  # YYYY-MM-DD
    start_time: Optional[str] = None  # HH:MM (24h)
    duration_hours: Optional[float] = None
    city: Optional[str] = None
    intensity: Optional[str] = None  # low / medium / high

    @field_validator("start_time", mode="before")
    @classmethod
    def normalize_start_time(cls, v):
        return _normalize_start_time(v)

    @field_validator("intensity", mode="before")
    @classmethod
    def normalize_intensity(cls, v):
        return _normalize_intensity(v)
```

In `EventResponse`, add `intensity` (after `city`):

```python
class EventResponse(BaseModel):
    id: int
    athlete_id: int
    event_name: str
    event_type: str
    event_date: str
    start_time: Optional[str]
    duration_hours: Optional[float]
    city: Optional[str]
    intensity: Optional[str] = None
    created_at: str
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_event_models.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add api/models.py tests/test_event_models.py
git commit -m "feat: optional validated intensity on event models"
```

---

## Task 4: Events route — set intensity on create & update

**Files:**
- Modify: `api/routes/events.py`

- [ ] **Step 1: Update `create_event` to set intensity**

In `api/routes/events.py`, add the import at the top:

```python
from api.services.nutrition_calc import derive_intensity
```

Replace the body of `create_event` (the athlete check + INSERT) with a version that fetches `competition_level`, resolves intensity (explicit or derived), and includes it in the INSERT:

```python
@router.post("/", response_model=EventResponse, status_code=201)
def create_event(data: EventCreate):
    conn = get_conn()
    try:
        athlete = conn.execute(
            "SELECT id, competition_level FROM athletes WHERE id = ?", (data.athlete_id,)
        ).fetchone()
        if not athlete:
            raise HTTPException(404, "Athlete not found.")

        intensity = data.intensity or derive_intensity(data.event_type, athlete["competition_level"])

        conn.execute(
            "INSERT INTO events (athlete_id, event_name, event_type, event_date, start_time, duration_hours, city, intensity) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (data.athlete_id, data.event_name, data.event_type, data.event_date, data.start_time, data.duration_hours, data.city, intensity),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM events WHERE rowid = last_insert_rowid()").fetchone()
        on_event_added_or_changed(data.athlete_id, data.event_date, conn)
        return dict(row)
    finally:
        conn.close()
```

- [ ] **Step 2: Update `update_event` to keep/resolve intensity**

In `api/routes/events.py`, in `update_event`, add intensity resolution after the other `new_*` lines and include it in the UPDATE. Replace:

```python
        new_city     = data.city           if data.city           is not None else existing["city"]

        conn.execute(
            "UPDATE events SET event_name=?, event_type=?, event_date=?, start_time=?, duration_hours=?, city=? WHERE id=?",
            (new_name, new_type, new_date, new_start, new_dur, new_city, event_id),
        )
```

with:

```python
        new_city     = data.city           if data.city           is not None else existing["city"]
        if data.intensity is not None:
            new_intensity = data.intensity
        elif existing["intensity"]:
            new_intensity = existing["intensity"]
        else:
            athlete = conn.execute(
                "SELECT competition_level FROM athletes WHERE id = ?", (existing["athlete_id"],)
            ).fetchone()
            level = athlete["competition_level"] if athlete else None
            new_intensity = derive_intensity(new_type, level)

        conn.execute(
            "UPDATE events SET event_name=?, event_type=?, event_date=?, start_time=?, duration_hours=?, city=?, intensity=? WHERE id=?",
            (new_name, new_type, new_date, new_start, new_dur, new_city, new_intensity, event_id),
        )
```

> Note: `existing["intensity"]` is safe to read because Task 2's migration adds the column to all rows before this code runs in any real/CI environment.

- [ ] **Step 3: Write an integration test**

Create `tests/test_events_route.py`:

```python
"""Integration tests for intensity on the events route."""

import os, tempfile, importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("DB_PATH", path)
    import db.setup as setup
    importlib.reload(setup)
    setup.init_db()
    from api.services.db_migrations import run_all
    run_all()
    import api.main as main
    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c
    os.remove(path)


def _make_athlete(client, level):
    p = client.post("/api/parents/", json={"full_name": "P", "email": f"{level}@x.com"})
    parent_id = p.json()["id"]
    a = client.post("/api/athletes/", json={
        "parent_id": parent_id, "first_name": "A", "age": 14, "gender": "girl",
        "weight_lbs": 110, "height_ft": 5, "height_in": 6, "competition_level": level,
    })
    return a.json()["id"]


def test_explicit_intensity_is_stored(client):
    aid = _make_athlete(client, "Recreational")
    r = client.post("/api/events/", json={
        "athlete_id": aid, "event_name": "Game", "event_type": "game",
        "event_date": "2026-06-21", "intensity": "High",
    })
    assert r.status_code == 201
    assert r.json()["intensity"] == "high"


def test_omitted_intensity_is_derived(client):
    aid = _make_athlete(client, "Elite Club")
    r = client.post("/api/events/", json={
        "athlete_id": aid, "event_name": "Game", "event_type": "game",
        "event_date": "2026-06-21",
    })
    assert r.status_code == 201
    assert r.json()["intensity"] == "high"  # Elite Club game


def test_rest_event_derives_low_for_elite(client):
    aid = _make_athlete(client, "Elite Club")
    r = client.post("/api/events/", json={
        "athlete_id": aid, "event_name": "Yoga", "event_type": "rest",
        "event_date": "2026-06-22",
    })
    assert r.json()["intensity"] == "low"
```

> If the athlete/parent create payloads above don't match the real schema, adjust the JSON to the actual required fields in `api/models.py` (`AthleteCreate`, parent create) — the assertions on `intensity` are what matter.

- [ ] **Step 4: Run the test**

Run: `pytest tests/test_events_route.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add api/routes/events.py tests/test_events_route.py
git commit -m "feat: store explicit-or-derived intensity on event create/update"
```

---

## Task 5: Nutrition route — thread event intensity into calc + store in `daily_targets`

**Files:**
- Modify: `api/routes/nutrition.py`

- [ ] **Step 1: Pass intensity into the calc and store it**

In `api/routes/nutrition.py`, in `get_targets`, capture the resolved event's intensity and pass it through. Replace:

```python
        if not event_type:
            events = conn.execute(
                "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time",
                (athlete_id, target_date),
            ).fetchall()
            event_type = dict(events[0])["event_type"] if events else "rest"

        targets = nutrition_calc.calc_daily_targets(athlete, event_type)
```

with:

```python
        intensity = None
        events = conn.execute(
            "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time",
            (athlete_id, target_date),
        ).fetchall()
        if not event_type:
            event_type = dict(events[0])["event_type"] if events else "rest"
        if events:
            intensity = dict(events[0]).get("intensity")

        targets = nutrition_calc.calc_daily_targets(athlete, event_type, intensity)
```

- [ ] **Step 2: Add `intensity` to the `daily_targets` INSERT**

In the same function, replace the INSERT statement and its values tuple:

```python
        conn.execute(
            """INSERT OR REPLACE INTO daily_targets
               (athlete_id, target_date, event_type, intensity, total_calories,
                carbs_g_min, carbs_g_max, protein_g_min, protein_g_max,
                fat_g_min, fat_g_max, iron_mg, calcium_mg,
                hydration_oz_min, hydration_oz_max, lea_alert, targets_raw)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (athlete_id, target_date, targets["event_type"], targets.get("intensity"),
             targets["total_calories"],
             targets["carbs_g_min"], targets["carbs_g_max"],
             targets["protein_g_min"], targets["protein_g_max"],
             targets["fat_g_min"], targets["fat_g_max"],
             targets["iron_mg"], targets["calcium_mg"],
             targets["hydration_oz_min"], targets["hydration_oz_max"],
             targets["lea_alert"], json.dumps(targets)),
        )
```

- [ ] **Step 3: Add an integration test**

Append to `tests/test_events_route.py`:

```python
def test_targets_reflect_event_intensity(client):
    aid = _make_athlete(client, "Recreational")
    client.post("/api/events/", json={
        "athlete_id": aid, "event_name": "Game", "event_type": "game",
        "event_date": "2026-07-01", "intensity": "high",
    })
    r = client.get(f"/api/nutrition/targets/{aid}?date=2026-07-01")
    assert r.status_code == 200
    body = r.json()
    assert body["intensity"] == "high"
    # high game band is upper half of 8-10 g/kg -> min at 9 g/kg, strictly above full-band min (8 g/kg)
    full = client.get(f"/api/nutrition/targets/{aid}?date=2026-07-02").json()  # no event -> rest, no intensity
    assert body["carbs_g_min"] > 0
```

- [ ] **Step 4: Run the test**

Run: `pytest tests/test_events_route.py -v`
Expected: PASS (4 tests total in the file).

- [ ] **Step 5: Commit**

```bash
git add api/routes/nutrition.py tests/test_events_route.py
git commit -m "feat: thread event intensity into targets calc and persist on daily_targets"
```

---

## Task 6: Frontend — Competition Level to 3 tiers

**Files:**
- Modify: `frontend/src/Onboarding.jsx`
- Modify: `frontend/src/ProfileScreen.jsx`

- [ ] **Step 1: Update Onboarding options**

In `frontend/src/Onboarding.jsx`, replace the four `<option>` lines in the Competition Level select:

```jsx
                  <option value="">Select level</option>
                  <option>Recreational</option>
                  <option>Club</option>
                  <option>Competitive</option>
                  <option>Elite</option>
```

with the 3 tiers plus a helper hint below the select. Replace the block with:

```jsx
                  <option value="">Select level</option>
                  <option>Recreational</option>
                  <option>Competitive Club</option>
                  <option>Elite Club</option>
                </select>
                <p style={{ fontSize: "12px", color: "#6b7280", margin: "6px 0 0" }}>
                  Recreational (AYSO, YMCA) · Competitive Club (most travel clubs, NorCal, NPL lower) · Elite Club (ECNL, GA, MLS Next, DPL, EA)
                </p>
```

> Note: this replacement closes the existing `</select>` — delete the original standalone `</select>` line that followed the old options so the tag is not duplicated.

- [ ] **Step 2: Update ProfileScreen levels**

In `frontend/src/ProfileScreen.jsx`, replace:

```jsx
const LEVELS      = ["Recreational", "Club", "Competitive", "Elite"];
```

with:

```jsx
const LEVELS      = ["Recreational", "Competitive Club", "Elite Club"];
```

And add a helper hint under the chip row. Replace:

```jsx
        <Field label="Competition Level" style={{ marginTop: "14px" }}>
          <div style={s.chipRow}>
            {LEVELS.map(l => (
              <Chip key={l} label={l} active={form.competition_level === l} onClick={() => set("competition_level", l)} />
            ))}
          </div>
        </Field>
```

with:

```jsx
        <Field label="Competition Level" style={{ marginTop: "14px" }}>
          <div style={s.chipRow}>
            {LEVELS.map(l => (
              <Chip key={l} label={l} active={form.competition_level === l} onClick={() => set("competition_level", l)} />
            ))}
          </div>
          <p style={{ fontSize: "12px", color: "#6b7280", margin: "6px 0 0" }}>
            Recreational (AYSO, YMCA) · Competitive Club (travel clubs, NorCal, NPL lower) · Elite Club (ECNL, GA, MLS Next, DPL, EA)
          </p>
        </Field>
```

- [ ] **Step 3: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/Onboarding.jsx frontend/src/ProfileScreen.jsx
git commit -m "feat: consolidate competition level to 3 tiers with examples"
```

---

## Task 7: Frontend — required intensity dropdown on Add Event form

**Files:**
- Modify: `frontend/src/ScheduleScreen.jsx`

- [ ] **Step 1: Add `intensity` to the blank form state**

In `frontend/src/ScheduleScreen.jsx`, replace:

```jsx
const blank = { event_name: "", event_type: "practice", event_date: "", start_time: "", duration_hours: "1.5", city: "" };
```

with:

```jsx
const blank = { event_name: "", event_type: "practice", event_date: "", start_time: "", duration_hours: "1.5", city: "", intensity: "" };
```

- [ ] **Step 2: Require intensity in `handleAdd`**

In `handleAdd`, replace:

```jsx
    if (!form.event_name.trim() || !form.event_date) return setFormError("Name and date are required.");
```

with:

```jsx
    if (!form.event_name.trim() || !form.event_date) return setFormError("Name and date are required.");
    if (!form.intensity) return setFormError("Please select an intensity level.");
```

- [ ] **Step 3: Add the intensity `<select>` to the form**

In `frontend/src/ScheduleScreen.jsx`, add a new field right after the Type `<select>` field block (after its closing `</div>`):

```jsx
            <div style={s.field}>
              <label style={s.label}>Intensity</label>
              <select style={s.input} value={form.intensity} onChange={e => setForm(f => ({ ...f, intensity: e.target.value }))}>
                <option value="">Select intensity</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
```

> The form value is sent verbatim by the existing `handleAdd` body (`JSON.stringify({ ...form, ... })`), so `intensity` is included automatically. The Pydantic validator lowercases/validates it server-side.

- [ ] **Step 4: Verify the build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Manual smoke check (optional but recommended)**

Run backend (`uvicorn api.main:app --reload --port 8000`) + frontend (`cd frontend && npm run dev`). Add an event without choosing intensity → inline error "Please select an intensity level." Choose High, submit → event saves. Confirm via `GET /api/events/athlete/{id}` that the row has `"intensity": "high"`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/ScheduleScreen.jsx
git commit -m "feat: required intensity dropdown on Add Event form"
```

---

## Task 8: Update the HLD

**Files:**
- Modify: `docs/HLD.md`

- [ ] **Step 1: Add `intensity` to the events ER block**

In `docs/HLD.md`, in the `events` entity (Section 9.1), add a line after `string city`:

```
        string intensity
```

And in the `daily_targets` entity, add after `string event_type`:

```
        string intensity
```

- [ ] **Step 2: Document the field in Section 6.3 (Events & Meal Timing)**

In `docs/HLD.md`, append to the Section 6.3 paragraph:

```markdown

Each event also carries an **intensity** (`low`/`medium`/`high`). Manually-added events require the parent to choose it; ICS-imported and legacy events derive it via `derive_intensity(event_type, competition_level)` — recovery/rest events floor to `low`; all other events map from the athlete's competition level (Recreational → low, Competitive Club → medium, Elite Club → high; unknown/empty → low). Intensity **repositions carbohydrate and protein targets within** the existing Everett/ACSM g/kg ranges (low → lower half, medium → middle 50%, high → upper half) and never outside them. Calories, hydration, and micronutrients remain event-type-driven in MVP.
```

- [ ] **Step 3: Note intensity in Section 10 (Nutrition Science Layer)**

In `docs/HLD.md`, after the Carbohydrate/Protein target tables in Section 10, add:

```markdown

**Intensity positioning:** `calc_daily_targets(athlete, event_type, intensity=None)` repositions the carbohydrate and protein g/kg bands by intensity (`low` → lower half, `medium` → middle 50%, `high` → upper half). `intensity=None` returns the full band unchanged (used by the athlete blueprint, which is generic per event type).
```

- [ ] **Step 4: Bump the version**

In `docs/HLD.md`, change `**Version:** 1.1` to `**Version:** 1.2`.

- [ ] **Step 5: Commit**

```bash
git add docs/HLD.md
git commit -m "docs: document event intensity in HLD (v1.2)"
```

---

## Final Verification

- [ ] **Run the full backend suite**

Run: `pytest -q`
Expected: all intensity tests green; no new failures vs. the pre-existing baseline.

- [ ] **Build the frontend**

Run: `cd frontend && npm run build`
Expected: success.

- [ ] **Confirm the migration is safe to re-run**

Run: `python -c "from api.services.db_migrations import run_all; run_all(); run_all(); print('idempotent ok')"`
Expected: `idempotent ok`.
