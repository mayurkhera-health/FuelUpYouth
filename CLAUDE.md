# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Branch & Deployment Rules (CRITICAL — read before any backend work)

### Single source of truth
- `main` is the ONLY branch for backend production deployments
- All backend fixes, features, and hotfixes must be applied to `main`
- Never deploy from `FuelUp-Admin`, a worktree, or any other branch

### FuelUp-Admin
- `FuelUp-Admin` is NOT a deployment branch
- Do not apply fixes to `FuelUp-Admin` directly
- If a fix exists on `FuelUp-Admin` that is needed in production, cherry-pick it onto `main` — do not switch deployment branches
- Never run `flyctl deploy` from `FuelUp-Admin` or any worktree based on it

### Deployment command
Always deploy from `main`:
```bash
cd ~/FuelUpYouth
git checkout main
flyctl deploy --app fuelup-youth
```

### Before every deploy, confirm:
1. You are on `main` (`git branch` shows `* main`)
2. All intended fixes are committed to `main`
3. `git status` is clean
4. `tsc --noEmit` passes (for mobile changes)

### Why this rule exists
- v177 (Jun 30 2026) was deployed from `FuelUp-Admin` instead of `main`
- This broke parent signup because `/parents/exists` and `/onboarding/complete` only existed on `main`
- One deployment branch only — always `main`

## Commands

### Backend
```bash
source venv/bin/activate
python db/setup.py                          # initialize SQLite database (run once)
uvicorn api.main:app --reload --port 8000   # start FastAPI dev server
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # Vite dev server (reads VITE_API_URL from frontend/.env.local)
npm run build    # production build to frontend/dist/
npm run lint     # ESLint
```

### Deployment
```bash
fly deploy -a fuelup-youth                          # deploy to Fly.io
fly ssh console -a fuelup-youth -C "python db/setup.py"  # re-init DB on server
fly logs -a fuelup-youth                            # tail live logs
```

CI auto-deploys to Fly.io on every push to `main` via `.github/workflows/fly-deploy.yml`. Requires `FLY_API_TOKEN` set as a GitHub Actions secret.

## Architecture

### Overview
Single-VM deployment on Fly.io (region: `sjc`). Uvicorn serves both the FastAPI backend and the compiled React frontend as static files from the same process on port 8000.

```
api/main.py            — FastAPI app, routes registered, StaticFiles mounted last at /
api/routes/            — one file per domain (parents, athletes, events, nutrition,
                         meals, recipes, analysis, reports, notifications, meal_plans)
api/models.py          — all Pydantic request/response models
api/database.py        — get_conn() returns a sqlite3 connection to DB_PATH env var
api/services/          — business logic (nutrition_calc, claude_ai, meal_timing,
                         recipe_db, weather)
db/setup.py            — creates all SQLite tables; re-run is safe (CREATE IF NOT EXISTS)
frontend/src/          — React SPA (no router library; App.jsx uses useState for views)
frontend/.env.local    — VITE_API_URL=http://localhost:8000 (dev only, gitignored)
```

### Database
Raw SQLite via `api/database.py`. No ORM. All queries use `conn.execute()` with `?` parameters. Tables: `parents`, `athletes`, `events`, `meal_logs`, `push_subscriptions`, `meal_plans`, `daily_targets`. Django (`fuelupy/`, `manage.py`) is present in the repo but **not used** by the running application — it is an artifact of the initial scaffold.

### API → Frontend contract
All API routes use the `/api/` prefix. The React frontend sets `const API = import.meta.env.VITE_API_URL ?? ""` at the top of each screen file, so all fetch calls are `${API}/api/...`. In production `VITE_API_URL` is unset and calls are same-origin. The FastAPI `StaticFiles` mount at `/` serves `frontend/dist/index.html` for all non-API paths, enabling client-side navigation.

### Nutrition science layer
`api/services/nutrition_calc.py` computes daily targets (calories, carbs, protein, fat, hydration, iron, calcium) from athlete weight/age/gender and event type using a fixed formula (Everett 2025 RMR, never Harris-Benedict). `api/services/claude_ai.py` wraps Claude Sonnet (`claude-sonnet-4-6`) with a strict system prompt encoding the same science framework and always returns JSON. The system prompt in `claude_ai.py` is the authoritative source for all science rules — do not contradict it.

### Meal timing
`api/services/meal_timing.py` maps event type + start time to a timed protocol list (pre-game meal, pre-game snack, halftime, 30-min recovery window, etc.). `api/routes/meal_plans.py` maps each event type to a set of named meal slots (`SLOTS_BY_EVENT`) and maps slots to recipe timing categories (`SLOT_TO_CATEGORY`).

### Frontend screens
`App.jsx` owns the top-level view state (`login → onboarding → dashboard`). `Dashboard.jsx` renders `AppShell` with a selected athlete and tab. Each tab is a standalone screen component. `Blueprint.jsx` renders the athlete's AI-generated nutrition blueprint. There is no client-side routing library.

### Push notifications
`api/routes/notifications.py` sends Web Push via `pywebpush`. VAPID keys are stored as Fly.io secrets. The browser service worker is at `frontend/public/sw.js`. Subscription endpoints are stored in the `push_subscriptions` table.
