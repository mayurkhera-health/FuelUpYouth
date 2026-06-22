# Smooth Loading + Latency MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give users clear, consistent feedback during backend waits and make the slow AI calls cheaper/faster where it's low-risk — without building streaming.

**Architecture:** Two independent layers. **Layer A (frontend, Tasks F1–F7):** a shared `<LoadingState>` + `<ErrorState>`, a contextual-message registry, a `useRotatingMessage` hook, the blueprint-polling bug fix, and wiring across screens. **Layer B (backend, Tasks B1–B4):** one Bedrock retry, an in-memory weather TTL cache, a `fly.toml` warm-start, and a RAG classify/retrieve overlap.

**Tech Stack:** React 19 (Vite, no router, inline-style components), FastAPI + raw sqlite3, AWS Bedrock (boto3), Fly.io.

**Source spec:** [`docs/superpowers/specs/2026-06-21-loading-latency-ux-design.md`](../specs/2026-06-21-loading-latency-ux-design.md)

---

## Testing Approach (read first)

- **Backend (Tasks B1, B2, B4): full TDD with `pytest`.** The repo has an established pytest suite (`tests/*.py`), no `conftest.py`; tests self-bootstrap with `sys.path.insert(0, str(Path(__file__).parent.parent))`. Follow that pattern.
- **Frontend (Tasks F1–F7): verification-based, not unit-tested.** The frontend has **no test runner** (no vitest/jest/testing-library in `frontend/package.json`). Standing up a React 19 test toolchain is out of scope for this MVP pass. Each frontend task is verified by: (1) `cd frontend && npm run build` succeeds, (2) `npm run lint` is clean, (3) the stated manual behavior check. The design spec §9 listed frontend unit tests — those are **deferred** with the test-runner setup; this is a deliberate scope decision, not an omission.
- **Run the full backend suite** (`source venv/bin/activate && python -m pytest -q`) after each backend task to confirm no regressions.

---

## File Structure

**New (frontend):**
- `frontend/src/components/LoadingState.jsx` — spinner + message; the one loading primitive. Depends on the global `spin` keyframe (already defined in `frontend/src/index.css:86` and `frontend/index.html:13`).
- `frontend/src/components/ErrorState.jsx` — friendly error line + optional Retry button.
- `frontend/src/constants/loadingMessages.js` — task-keyed copy map (string or array).
- `frontend/src/hooks/useRotatingMessage.js` — cycles an array while a fetch is active; holds on the last item. (New `hooks/` dir.)

**Modified (frontend):** `Blueprint.jsx` (polling fix + wiring), `MealPlannerScreen.jsx`, `ReportsScreen.jsx`, `HydrationScreen.jsx`, `RecipesScreen.jsx`, `HomeScreen.jsx`, `pages/Today.jsx`, `ScheduleScreen.jsx`.

**Modified (backend):** `api/services/bedrock_client.py` (retry + `_bedrock_config()`), `api/services/weather.py` (TTL cache), `api/services/knowledge/answer.py` (overlap).

**Modified (infra):** `fly.toml`.

**New tests (backend):** `tests/test_weather_cache.py`, `tests/test_bedrock_retry.py`, `tests/test_rag_overlap.py`.

---

## Task F1: `<LoadingState>` component

**Files:**
- Create: `frontend/src/components/LoadingState.jsx`

- [ ] **Step 1: Create the component**

```jsx
// frontend/src/components/LoadingState.jsx
export default function LoadingState({ message = "Loading…", subtle = false }) {
  return (
    <div style={subtle ? styles.inline : styles.center}>
      <div style={styles.spinner} />
      <p style={subtle ? styles.textInline : styles.text}>{message}</p>
    </div>
  );
}

const styles = {
  center: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "60px 20px", gap: "16px" },
  inline: { display: "flex", alignItems: "center", gap: "10px", padding: "8px 0" },
  spinner: { width: "40px", height: "40px", border: "3px solid #e5e7eb", borderTopColor: "#2d6a4f", borderRadius: "50%", animation: "spin 0.8s linear infinite", flexShrink: 0 },
  text: { color: "#4a6358", fontSize: "19px", margin: 0 },
  textInline: { color: "#4a6358", fontSize: "16px", margin: 0 },
};
```

- [ ] **Step 2: Verify build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: build succeeds, no new lint errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/LoadingState.jsx
git commit -m "feat(ui): shared LoadingState component"
```

---

## Task F2: `<ErrorState>` component

**Files:**
- Create: `frontend/src/components/ErrorState.jsx`

- [ ] **Step 1: Create the component**

```jsx
// frontend/src/components/ErrorState.jsx
export default function ErrorState({ message = "Something went wrong.", onRetry }) {
  return (
    <div style={styles.center}>
      <p style={styles.text}>⚠ {message}</p>
      {onRetry && (
        <button style={styles.btn} onClick={onRetry}>Try again</button>
      )}
    </div>
  );
}

const styles = {
  center: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 20px", gap: "14px" },
  text: { color: "#dc2626", fontSize: "18px", margin: 0, textAlign: "center" },
  btn: { background: "#2d6a4f", color: "#fff", border: "none", borderRadius: "10px", padding: "10px 18px", fontSize: "16px", fontWeight: "700", cursor: "pointer" },
};
```

- [ ] **Step 2: Verify build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: build succeeds, no new lint errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ErrorState.jsx
git commit -m "feat(ui): shared ErrorState component with retry"
```

---

## Task F3: Contextual message registry

**Files:**
- Create: `frontend/src/constants/loadingMessages.js`

- [ ] **Step 1: Create the registry**

```js
// frontend/src/constants/loadingMessages.js
// Generic-encouraging copy ONLY. Never reference a number, score, grams, or calories.
export const LOADING_MESSAGES = {
  blueprint:      ["Crunching your numbers…", "Personalizing your plan…", "Almost ready…"],
  photo_analysis: ["Reading your photo…", "Looking up nutrition…", "Almost there…"],
  voice_analysis: ["Listening to your meal…", "Looking up nutrition…"],
  meal_plan_gen:  ["Building your week…", "Matching recipes to your schedule…", "Finishing up…"],
  gap_analysis:   ["Checking today's fuel…", "Comparing to your targets…"],
  coach:          ["Thinking…", "Pulling from trusted sources…"],
  rag_ask:        ["Thinking…", "Pulling from trusted sources…"],
  recipe_swap:    ["Finding a better match…"],
  hydration:      ["Reading the forecast…", "Calculating your sweat plan…"],
  reports:        ["Reviewing the week…", "Writing your summary…"],
  generic:        ["Loading…"],
};
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/constants/loadingMessages.js
git commit -m "feat(ui): contextual loading message registry"
```

---

## Task F4: `useRotatingMessage` hook

**Files:**
- Create: `frontend/src/hooks/useRotatingMessage.js`

- [ ] **Step 1: Create the hook**

```js
// frontend/src/hooks/useRotatingMessage.js
import { useState, useEffect } from "react";

/**
 * Cycles through `messages` every `intervalMs` while `active` is true.
 * Holds on the LAST message (never loops — looping implies a stall).
 * Resets to the first message when `active` becomes false.
 * A string or single-item array is returned as-is with no timer.
 */
export function useRotatingMessage(messages, { intervalMs = 2500, active = true } = {}) {
  const list = Array.isArray(messages) ? messages : [messages];
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active) { setIndex(0); return; }
    if (list.length <= 1) return;
    const id = setInterval(() => {
      setIndex((i) => (i < list.length - 1 ? i + 1 : i));
    }, intervalMs);
    return () => clearInterval(id);
  }, [active, intervalMs, list.length]);

  return list[Math.min(index, list.length - 1)];
}
```

- [ ] **Step 2: Verify build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: build succeeds, no new lint errors (the hook obeys exhaustive-deps: `list.length`, `active`, `intervalMs`).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useRotatingMessage.js
git commit -m "feat(ui): useRotatingMessage hook"
```

---

## Task F5: Blueprint polling fix (highest-value)

**Context — the actual endpoint contract** (`api/routes/athletes.py:146-216`), which the current code gets wrong:
- **Still generating (fresh):** HTTP **404**, body `{"detail": {"status": "pending", "message": "..."}}`.
- **Not started yet:** HTTP **404**, same `detail.status === "pending"`.
- **Stale/failed/invalid:** HTTP **200**, body `{"status": "error", "message": "...", ...}`.
- **Ready:** HTTP **200**, body `{"status": "ready", "blueprint": {...}, "_calculated": {...}}`.

The current `Blueprint.jsx` treats the 404 as a hard error ("Failed to load Blueprint") and never polls — that is the first-run bug. Fix: poll while `detail.status === "pending"`, render on `ready`, show ErrorState on `error`.

**Files:**
- Modify: `frontend/src/Blueprint.jsx` (imports near line 1; state at 262-264; effect at 266-273; loading/error renders at 275-285)

- [ ] **Step 1: Add imports**

At the top of `frontend/src/Blueprint.jsx`, after the existing `import { useEffect, useState } from "react";` line, add:

```jsx
import LoadingState from "./components/LoadingState";
import ErrorState from "./components/ErrorState";
import { LOADING_MESSAGES } from "./constants/loadingMessages";
import { useRotatingMessage } from "./hooks/useRotatingMessage";
```

- [ ] **Step 2: Add a reload key to state**

Replace the state block (currently lines ~262-264):

```jsx
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
```

with:

```jsx
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const loadingMsg = useRotatingMessage(LOADING_MESSAGES.blueprint, { active: loading });
```

- [ ] **Step 3: Replace the fetch effect with a polling effect**

Replace the entire `useEffect` (currently lines ~266-273) with:

```jsx
  useEffect(() => {
    if (!athlete?.id) return;
    let timer = null;
    let cancelled = false;
    const startedAt = Date.now();
    const POLL_MS = 2500;
    const MAX_MS = 40000;

    setLoading(true);
    setError(null);
    setData(null);

    const poll = async () => {
      try {
        const r = await fetch(`${API}/api/athletes/${athlete.id}/blueprint`, { cache: "no-store" });

        if (r.status === 404) {
          const body = await r.json().catch(() => ({}));
          if (body?.detail?.status === "pending") {
            if (Date.now() - startedAt > MAX_MS) {
              if (!cancelled) { setError("This is taking longer than expected. Please try again."); setLoading(false); }
              return;
            }
            timer = setTimeout(poll, POLL_MS);
            return;
          }
          if (!cancelled) { setError("Athlete not found."); setLoading(false); }
          return;
        }

        if (!r.ok) {
          if (!cancelled) { setError("Failed to load Blueprint"); setLoading(false); }
          return;
        }

        const json = await r.json();
        if (cancelled) return;
        if (json.status === "error") {
          setError(json.message || "We couldn't build your blueprint. Please try again.");
          setLoading(false);
          return;
        }
        setData(json);
        setLoading(false);
      } catch (e) {
        if (!cancelled) { setError(String(e)); setLoading(false); }
      }
    };

    poll();
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [athlete?.id, reloadKey]);
```

- [ ] **Step 4: Replace the loading and error renders**

Replace the loading + error blocks (currently lines ~275-285):

```jsx
  if (loading) return (
    <div style={s.center}>
      <div style={s.spinner} />
      <p style={s.loadingText}>Building your Nutrition Blueprint…</p>
    </div>
  );
  if (error) return (
    <div style={s.center}>
      <p style={{ color: "#dc2626", textAlign: "center" }}>⚠ {error}</p>
    </div>
  );
```

with:

```jsx
  if (loading) return <LoadingState message={loadingMsg} />;
  if (error) return <ErrorState message={error} onRetry={() => setReloadKey((k) => k + 1)} />;
```

- [ ] **Step 5: Verify build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: build succeeds; no unused-var warnings (the old `s.spinner`/`s.loadingText` styles may now be unused — leave them, they're harmless, or remove if lint flags them as errors).

- [ ] **Step 6: Manual behavior check**

Run the app (`cd frontend && npm run dev` against a backend with a freshly-created athlete). Expected: the Blueprint tab shows the rotating "Crunching your numbers… → Personalizing… → Almost ready…" copy with a spinner while generating, then renders the blueprint — **no error flash**. Forcing an error response shows ErrorState with a working "Try again".

- [ ] **Step 7: Commit**

```bash
git add frontend/src/Blueprint.jsx
git commit -m "fix(blueprint): poll while generating instead of erroring; rotating copy + retry"
```

---

## Task F6: Wire shared loading into the AI screens

Apply the same pattern to the four screens with slow on-demand AI calls. For each: import the four helpers (paths are relative to `frontend/src/`, so `./components/...`, `./constants/...`, `./hooks/...`), add a `useRotatingMessage` line driven by that screen's pending flag, and replace the bare text loader with `<LoadingState message={...} />`. Keep existing `<ErrorState>`-equivalent error boxes, or swap them to `<ErrorState>` where an inline error already exists.

**Files:**
- Modify: `frontend/src/MealPlannerScreen.jsx`, `frontend/src/ReportsScreen.jsx`, `frontend/src/HydrationScreen.jsx`, `frontend/src/RecipesScreen.jsx`

- [ ] **Step 1: MealPlannerScreen — locate and replace the loader**

Add imports (after the file's existing React import):
```jsx
import LoadingState from "./components/LoadingState";
import { LOADING_MESSAGES } from "./constants/loadingMessages";
import { useRotatingMessage } from "./hooks/useRotatingMessage";
```
Add near the other `useState`s in the component:
```jsx
const planMsg = useRotatingMessage(LOADING_MESSAGES.meal_plan_gen, { active: loading });
```
Find the current loading branch (grep `Loading plan…`): `<div style={s.loadingMsg}>Loading plan…</div>`. Replace it with:
```jsx
<LoadingState message={planMsg} />
```

- [ ] **Step 2: ReportsScreen — show LoadingState while a report runs**

Add the three imports (as above). The screen uses per-report `loading.daily` / `loading.weekly` / `loading.tournament` flags and only changes button text today. For each report's result area, while its flag is true, render a `<LoadingState>` with rotating `reports` copy. Add:
```jsx
import LoadingState from "./components/LoadingState";
import { LOADING_MESSAGES } from "./constants/loadingMessages";
import { useRotatingMessage } from "./hooks/useRotatingMessage";
```
```jsx
const anyReportLoading = loading.daily || loading.weekly || loading.tournament;
const reportMsg = useRotatingMessage(LOADING_MESSAGES.reports, { active: anyReportLoading });
```
In each report section, where the result renders, add a leading branch: when that section's loading flag is true and there's no result yet, render `<LoadingState message={reportMsg} />`. Keep the existing button-text change ("Analyzing…"/"Generating…") — it complements the panel spinner.

- [ ] **Step 3: HydrationScreen — events loader + calc loader**

Add the three imports. Add:
```jsx
const hydrationMsg = useRotatingMessage(LOADING_MESSAGES.hydration, { active: loading });
```
Find the events loader (grep `Loading events…`): `<p style={s.hint}>Loading events…</p>` → replace with `<LoadingState message="Loading events…" subtle />`. For the sweat-plan calculation result area, while `loading` is true render `<LoadingState message={hydrationMsg} />` above/instead of the empty result. Keep the existing "Calculating…" button label.

- [ ] **Step 4: RecipesScreen — list loader + swap**

Add the three imports. Find the list loader (grep `Loading recipes…`): `<p style={s.empty}>Loading recipes…</p>` → replace with `<LoadingState message="Loading recipes…" />`. The per-recipe swap already shows "Finding swap…" on the button; leave it (single-line, no rotation needed — `LOADING_MESSAGES.recipe_swap` is a one-item list).

- [ ] **Step 5: Verify build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: build succeeds; no new lint errors.

- [ ] **Step 6: Manual behavior check**

Each of the four screens shows a moving spinner + message during its load/generation (not a static text line). No screen appears frozen.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/MealPlannerScreen.jsx frontend/src/ReportsScreen.jsx frontend/src/HydrationScreen.jsx frontend/src/RecipesScreen.jsx
git commit -m "feat(ui): shared LoadingState + rotating copy across AI screens"
```

---

## Task F7: Consistency + error states on the remaining screens

Bring the fast/data screens onto the shared component and give the silent-`.catch()` screens a visible, recoverable error.

**Files:**
- Modify: `frontend/src/HomeScreen.jsx`, `frontend/src/pages/Today.jsx`, `frontend/src/ScheduleScreen.jsx`

- [ ] **Step 1: HomeScreen — replace spinner + add error state**

Add imports:
```jsx
import LoadingState from "./components/LoadingState";
import ErrorState from "./components/ErrorState";
import { LOADING_MESSAGES } from "./constants/loadingMessages";
```
Add an error state alongside the existing `loading` state:
```jsx
const [loadError, setLoadError] = useState(false);
```
In the fetch's `.catch(...)` (currently silent), set `setLoadError(true)` and `setLoading(false)`. Replace the existing spinner block (grep `Loading today's plan…`) with:
```jsx
if (loading) return <LoadingState message={LOADING_MESSAGES.generic[0]} />;
if (loadError) return <ErrorState message="Couldn't load today's plan." onRetry={() => { setLoadError(false); /* re-trigger existing load() */ }} />;
```
Wire `onRetry` to whatever function the screen already uses to fetch (e.g. re-run the effect via a `reloadKey` state if there's no standalone `load()` — mirror the Task F5 `reloadKey` pattern).

- [ ] **Step 2: Today.jsx — same treatment**

Add imports (paths from `frontend/src/pages/` are `../components/...`, `../constants/...`):
```jsx
import LoadingState from "../components/LoadingState";
import ErrorState from "../components/ErrorState";
import { LOADING_MESSAGES } from "../constants/loadingMessages";
```
Replace the existing spinner block (grep `Loading today's briefing…`) with `<LoadingState message={LOADING_MESSAGES.generic[0]} />`. Add a `loadError` state, set it in the currently-silent `.catch`, and render `<ErrorState ... onRetry={...} />` when set.

- [ ] **Step 3: ScheduleScreen — replace the text loader**

Add imports (`./components/...`). Replace the loader (grep `Loading schedule…`): `<p style={s.empty}>Loading schedule…</p>` → `<LoadingState message="Loading schedule…" />`. (Schedule already surfaces import/parse errors; no new error state needed.)

- [ ] **Step 4: Verify build + lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: build succeeds; no new lint errors.

- [ ] **Step 5: Manual behavior check**

Home/Today show the shared spinner; killing the backend makes Home and Today show ErrorState with a working "Try again" instead of a blank screen.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/HomeScreen.jsx frontend/src/pages/Today.jsx frontend/src/ScheduleScreen.jsx
git commit -m "feat(ui): consistent loading + recoverable errors on Home/Today/Schedule"
```

---

## Task B1: One retry on Bedrock

**Files:**
- Modify: `api/services/bedrock_client.py:26-35`
- Test: `tests/test_bedrock_retry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bedrock_retry.py
"""Bedrock client retries transient failures exactly once."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.bedrock_client import _bedrock_config


def test_bedrock_config_allows_one_retry():
    cfg = _bedrock_config()
    # standard mode: max_attempts is TOTAL attempts, so 2 == one retry
    assert cfg.retries["max_attempts"] == 2
    assert cfg.retries["mode"] == "standard"
    assert cfg.read_timeout == 30
    assert cfg.connect_timeout == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && python -m pytest tests/test_bedrock_retry.py -v`
Expected: FAIL with `ImportError: cannot import name '_bedrock_config'`.

- [ ] **Step 3: Add `_bedrock_config()` and use it**

In `api/services/bedrock_client.py`, replace the `_client()` function (lines 26-35):

```python
def _client():
    return boto3.client(
        "bedrock-runtime",
        region_name=_region(),
        config=Config(
            read_timeout=30,
            connect_timeout=10,
            retries={"max_attempts": 0},
        ),
    )
```

with:

```python
def _bedrock_config() -> Config:
    # max_attempts is TOTAL attempts in "standard" mode → 2 means one retry.
    # Standard mode retries only transient errors (throttling, 5xx, timeouts).
    return Config(
        read_timeout=30,
        connect_timeout=10,
        retries={"max_attempts": 2, "mode": "standard"},
    )


def _client():
    return boto3.client(
        "bedrock-runtime",
        region_name=_region(),
        config=_bedrock_config(),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && python -m pytest tests/test_bedrock_retry.py -v`
Expected: PASS.

> Implementer note: confirm the installed botocore treats `max_attempts` as total attempts in `standard` mode (it does as of botocore ≥1.x). If a pinned legacy version differs, the intent is exactly **one** retry on transient errors — adjust the value, keep the test asserting that intent.

- [ ] **Step 5: Run full suite + commit**

```bash
source venv/bin/activate && python -m pytest -q
git add api/services/bedrock_client.py tests/test_bedrock_retry.py
git commit -m "feat(bedrock): one retry on transient failures"
```

---

## Task B2: Weather TTL cache

**Files:**
- Modify: `api/services/weather.py:33-50`
- Test: `tests/test_weather_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_weather_cache.py
"""get_weather caches results per city for a TTL window."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.services.weather as weather


def _stub_fetch(monkeypatch):
    calls = {"n": 0}

    def fake_fetch(city):
        calls["n"] += 1
        return {"temp_f": 70.0, "humidity": 50, "description": "clear", "error": None}

    monkeypatch.setattr(weather, "_fetch_weather", fake_fetch)
    return calls


def test_second_call_within_ttl_is_cached(monkeypatch):
    weather._weather_cache.clear()
    calls = _stub_fetch(monkeypatch)
    monkeypatch.setattr(weather, "_now", lambda: 1000.0)

    a = weather.get_weather("Denver")
    b = weather.get_weather("Denver")

    assert a == b
    assert calls["n"] == 1  # second call served from cache


def test_call_after_ttl_refetches(monkeypatch):
    weather._weather_cache.clear()
    calls = _stub_fetch(monkeypatch)

    monkeypatch.setattr(weather, "_now", lambda: 1000.0)
    weather.get_weather("Denver")
    # advance past the 30-min TTL
    monkeypatch.setattr(weather, "_now", lambda: 1000.0 + weather._WEATHER_TTL_SECONDS + 1)
    weather.get_weather("Denver")

    assert calls["n"] == 2


def test_errors_are_not_cached(monkeypatch):
    weather._weather_cache.clear()
    monkeypatch.setattr(weather, "_now", lambda: 1000.0)

    def err_fetch(city):
        return {"temp_f": None, "humidity": None, "description": "unknown", "error": "boom"}

    monkeypatch.setattr(weather, "_fetch_weather", err_fetch)
    weather.get_weather("Denver")
    assert "denver" not in weather._weather_cache
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && python -m pytest tests/test_weather_cache.py -v`
Expected: FAIL (`_fetch_weather` / `_weather_cache` / `_now` / `_WEATHER_TTL_SECONDS` don't exist).

- [ ] **Step 3: Refactor `weather.py` for a cached fetch**

In `api/services/weather.py`, add `import time` at the top (alongside `import os` / `import requests`), then replace the `get_weather` function (lines 33-50) with:

```python
_WEATHER_TTL_SECONDS = 1800  # 30 minutes
_weather_cache: dict[str, tuple[float, dict]] = {}  # city(lower) -> (fetched_at, result)


def _now() -> float:
    return time.monotonic()


def _fetch_weather(city: str) -> dict:
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return {"temp_f": None, "humidity": None, "description": "unknown", "error": "No API key configured"}
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=imperial"
    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()
        if resp.status_code != 200:
            return {"temp_f": None, "humidity": None, "description": "unknown", "error": data.get("message", "API error")}
        return {
            "temp_f": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "error": None,
        }
    except Exception as e:
        return {"temp_f": None, "humidity": None, "description": "unknown", "error": str(e)}


def get_weather(city: str) -> dict:
    """Cached weather lookup. Successful results are cached per city for the TTL;
    error results are never cached (so a transient failure self-heals next call).
    In-memory, per-process — correct for the single-VM deployment."""
    key = (city or "").strip().lower()
    cached = _weather_cache.get(key)
    if cached and (_now() - cached[0]) < _WEATHER_TTL_SECONDS:
        return cached[1]
    result = _fetch_weather(city)
    if not result.get("error"):
        _weather_cache[key] = (_now(), result)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && python -m pytest tests/test_weather_cache.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Run full suite + commit**

```bash
source venv/bin/activate && python -m pytest -q
git add api/services/weather.py tests/test_weather_cache.py
git commit -m "feat(weather): in-memory TTL cache for get_weather"
```

---

## Task B3: Fly.io warm start

**Files:**
- Modify: `fly.toml` (the `[http_service]` block)

- [ ] **Step 1: Change one line**

In `fly.toml`, under `[http_service]`, change:

```toml
  min_machines_running = 0
```

to:

```toml
  min_machines_running = 1
```

Leave `auto_stop_machines = 'stop'` and `auto_start_machines = true` as-is.

- [ ] **Step 2: Validate config**

Run: `fly config validate`
Expected: "Configuration is valid".

- [ ] **Step 3: Commit**

```bash
git add fly.toml
git commit -m "chore(infra): keep one machine warm to remove cold-start latency"
```

> Deploy note (not a code step): the warm-start takes effect on the next `fly deploy`. One always-on machine carries a small ongoing Fly.io cost (approved).

---

## Task B4: RAG classify + retrieve overlap

**Context:** `answer_with_knowledge` (`api/services/knowledge/answer.py:443`) runs `_classify_coach_path` (~1 s) then `retrieve` (~1–1.5 s incl. embed) then `_call_bedrock`, all serial. `_classify_coach_path` and `retrieve` both depend only on `contextual_question`, so retrieval can run **concurrently** with classification; only the knowledge path consumes it (recipe/out-of-scope discard it). Saves ~1 s on the common path at the cost of one speculative embed on the other paths.

**Files:**
- Modify: `api/services/knowledge/answer.py` (top-of-file import; the `answer_with_knowledge` body, lines ~455-505)
- Test: `tests/test_rag_overlap.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag_overlap.py
"""answer_with_knowledge overlaps classify+retrieve without changing output."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.services.knowledge.answer as ans


def test_knowledge_path_output_unchanged(monkeypatch):
    calls = {"retrieve": 0}

    monkeypatch.setattr(ans, "_detect_safety_flag", lambda q: False)
    monkeypatch.setattr(ans, "_classify_coach_path", lambda q, a: {"path": "knowledge"})
    monkeypatch.setattr(ans, "_maybe_calculate", lambda q, a: None)

    def fake_retrieve(question, top_n=5):
        calls["retrieve"] += 1
        return [{"heading": "h", "content": "c", "title": "T", "source": "Boston Children's Hospital"}]

    monkeypatch.setattr(ans, "retrieve", fake_retrieve)
    monkeypatch.setattr(ans, "_build_system_prompt", lambda chunks, calc: "SYSTEM")
    monkeypatch.setattr(ans, "_call_bedrock", lambda system, q: "**Answer.**")
    monkeypatch.setattr(ans, "list_sources", lambda: [])

    out = ans.answer_with_knowledge("what should I eat before a game?", {"id": 1})

    assert out["answer"] == "**Answer.**"
    assert calls["retrieve"] == 1


def test_recipe_path_does_not_consume_retrieve(monkeypatch):
    calls = {"retrieve": 0}

    monkeypatch.setattr(ans, "_detect_safety_flag", lambda q: False)
    monkeypatch.setattr(ans, "_classify_coach_path", lambda q, a: {"path": "recipe", "recipe_category": "pre_game"})
    monkeypatch.setattr(ans, "_maybe_calculate", lambda q, a: None)

    def fake_retrieve(question, top_n=5):
        calls["retrieve"] += 1
        return []

    monkeypatch.setattr(ans, "retrieve", fake_retrieve)
    monkeypatch.setattr(ans, "_answer_with_recipe", lambda q, a, c: {"answer": "RECIPE", "citations": []})

    out = ans.answer_with_knowledge("give me a pre game snack", {"id": 1})

    assert out["answer"] == "RECIPE"
    # speculative retrieve may have started, but its result is never used on the recipe path
```

- [ ] **Step 2: Run test to verify it fails (or is brittle on serial code)**

Run: `source venv/bin/activate && python -m pytest tests/test_rag_overlap.py -v`
Expected: the knowledge-path test PASSES on current serial code (output identical), but this test pins the contract before we refactor. If it errors on a monkeypatch target name mismatch, fix the patch target to the real symbol in `answer.py` before proceeding.

- [ ] **Step 3: Add the overlap**

In `api/services/knowledge/answer.py`, add at the top with the other imports:

```python
from concurrent.futures import ThreadPoolExecutor
```

Then in `answer_with_knowledge`, replace the section from the classify call through the `retrieve` try/except (current lines ~469-496):

```python
    route = _classify_coach_path(contextual_question, athlete)
    if route["path"] == "out_of_scope":
        return _answer_out_of_scope(contextual_question, athlete)

    category_for_recipe = None
    if prefer_recipe and recipe_category:
        category_for_recipe = recipe_category
    elif route["path"] == "recipe" and route.get("recipe_category"):
        category_for_recipe = route["recipe_category"]
    elif recipe_category and _looks_like_meal_request(contextual_question):
        category_for_recipe = recipe_category

    if category_for_recipe:
        return _answer_with_recipe(contextual_question, athlete, category_for_recipe)

    calc_result = _maybe_calculate(contextual_question, athlete)

    try:
        chunks = retrieve(contextual_question, top_n=5)
    except Exception:
        logger.exception("Knowledge retrieval failed for question=%r", question[:80])
        return {
            "answer": _FALLBACK,
            "format": "markdown",
            "citations": [],
            "calculation": calc_result,
            "sources": list_sources(),
        }
```

with:

```python
    # Speculatively start retrieval concurrently with classification. Only the
    # knowledge path consumes the result; recipe/out_of_scope discard it (one
    # wasted embed, fractions of a cent) in exchange for ~1s on the common path.
    with ThreadPoolExecutor(max_workers=1) as _pool:
        retrieve_future = _pool.submit(lambda: retrieve(contextual_question, top_n=5))

        route = _classify_coach_path(contextual_question, athlete)
        if route["path"] == "out_of_scope":
            return _answer_out_of_scope(contextual_question, athlete)

        category_for_recipe = None
        if prefer_recipe and recipe_category:
            category_for_recipe = recipe_category
        elif route["path"] == "recipe" and route.get("recipe_category"):
            category_for_recipe = route["recipe_category"]
        elif recipe_category and _looks_like_meal_request(contextual_question):
            category_for_recipe = recipe_category

        if category_for_recipe:
            return _answer_with_recipe(contextual_question, athlete, category_for_recipe)

        calc_result = _maybe_calculate(contextual_question, athlete)

        try:
            chunks = retrieve_future.result()
        except Exception:
            logger.exception("Knowledge retrieval failed for question=%r", question[:80])
            return {
                "answer": _FALLBACK,
                "format": "markdown",
                "citations": [],
                "calculation": calc_result,
                "sources": list_sources(),
            }
```

The code after this point (`if not chunks:` … `_build_system_prompt` … `_call_bedrock`) is unchanged and runs after the `with` block exits.

- [ ] **Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && python -m pytest tests/test_rag_overlap.py -v`
Expected: PASS (2 tests). Output is identical to the serial version; `retrieve` is invoked exactly once on the knowledge path.

- [ ] **Step 5: Run full suite + commit**

```bash
source venv/bin/activate && python -m pytest -q
git add api/services/knowledge/answer.py tests/test_rag_overlap.py
git commit -m "perf(rag): overlap classify and retrieve on the knowledge path"
```

---

## Final Verification

- [ ] `cd frontend && npm run build && npm run lint` — clean.
- [ ] `source venv/bin/activate && python -m pytest -q` — all green (3 new backend test files pass; no regressions).
- [ ] Manual smoke: fresh athlete → Blueprint shows rotating generating copy then renders (no error flash); each AI screen shows a moving spinner; Home/Today show ErrorState + Retry when the backend is down.
- [ ] Use **superpowers:finishing-a-development-branch** to open the PR.

---

## Self-Review (completed during authoring)

**Spec coverage:** A1 `<LoadingState>` → F1. A2 registry → F3. A3 `useRotatingMessage` → F4. A4 blueprint polling → F5. A5 `<ErrorState>` → F2 + wired in F5/F7. Screen wiring (§5.6) → F6/F7. Escalation (§5.7) → folded into F5's 40 s cap + the blueprint "taking longer" copy; the generic per-screen 10 s escalation line is **descoped to the rotating-copy mechanism** (rotating messages already signal progress) to avoid an extra timer abstraction in the MVP — call out if you want the explicit 10 s line restored. B1 retry → B1. B2 weather cache → B2. B3 warm start → B3. B4 RAG overlap → B4. Non-goals (streaming, token trimming, Redis, skeletons) → not implemented, per spec.

**Placeholder scan:** none — every code step shows complete code or an exact grep anchor + replacement.

**Type/name consistency:** `useRotatingMessage(messages, { active })`, `LOADING_MESSAGES.<key>`, `<LoadingState message subtle />`, `<ErrorState message onRetry />`, `_bedrock_config()`, `_fetch_weather`/`_weather_cache`/`_now`/`_WEATHER_TTL_SECONDS`, `retrieve_future` — used consistently across tasks.

**Known approximation:** F6/F7 reference current loader strings (e.g. `Loading plan…`, `Loading recipes…`) as grep anchors from a code audit rather than line numbers; the implementer greps the anchor before editing. F5 and all backend tasks use exact, verified current code.
