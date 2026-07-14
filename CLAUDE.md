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
Always deploy from the main worktree via the guarded wrapper (checks you're on
`main`, a clean tree, and reminds you about the `PERFORMANCE_PLATE_ENABLED` flag —
the plate ships DARK and deploy alone does NOT enable it):
```bash
cd ~/FuelUpYouth-main
./scripts/deploy.sh
```
Raw command it wraps (do not run directly unless the wrapper is unavailable):
`flyctl deploy --app fuelup-youth`

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

## Test suite baseline — `feat/fueliq` (established 2026-07-14)

Run: `python3 -m pytest tests/ --tb=no -q` from `~/FuelUpYouth-main`

**Baseline result: 24 failed / 580 passed / 14 errors**

When adding Phase work on this branch, diff against this list. A test not in this list that starts failing is a regression introduced by the new work and must be fixed before the phase is considered done.

### Pre-existing FAILED tests (24)

```
tests/test_admin_analytics_activity.py::test_activity_resolves_names_with_unknown_fallback
tests/test_admin_family_engagement.py::test_engagement_empty_for_fresh_athlete
tests/test_admin_overview.py::test_active_users_warning_toggles
tests/test_admin_overview.py::test_growth_section_new_families
tests/test_admin_overview.py::test_metric_gauge_fields
tests/test_fuel_gauge.py::test_event_day_has_all_five_metrics
tests/test_fuel_gauge.py::test_event_day_split_excludes_everyday_and_reaches_100
tests/test_fuel_gauge.py::test_flag_off_payload_is_byte_identical_to_production
tests/test_fuel_gauge.py::test_fuel_targets_shape_when_flag_on
tests/test_fuel_gauge.py::test_split_unknown_category_contributes_zero_and_logs
tests/test_fueliq_daily_challenge_route.py::test_daily_challenge_verdict_flow_end_to_end  ← see isolation note below
tests/test_ics_sync.py::test_update_changed_event_only
tests/test_login_alerts.py::test_first_ever_explicit_login_reads_as_new
tests/test_login_alerts.py::test_new_signup_via_onboarding_alerts
tests/test_notification_service.py::TestSendExpoPush::test_different_recipient_is_independent
tests/test_notification_service.py::TestSendNotificationGuarded::test_duplicate_send_returns_false_and_does_not_push
tests/test_notification_service.py::TestSendNotificationGuarded::test_first_send_returns_true_and_calls_push
tests/test_plate_route.py::test_window_returns_plate_and_options
tests/test_recipe_generator.py::test_generate_recipe_agent_picks_from_library
tests/test_recipe_generator.py::test_generate_recipe_falls_back_on_invalid_agent_id
tests/test_recipe_generator.py::test_get_valid_recipes_returns_halftime_options
tests/test_today_service.py::test_mission_items_iron_critical_for_girls
tests/test_window_templates.py::test_early_morning_game_6am
tests/test_window_templates.py::test_evening_practice_7_30pm
tests/test_window_templates.py::test_max_taps_not_exceeded
tests/test_window_templates.py::test_tournament_close_gap
tests/test_window_templates.py::test_tournament_wide_gap
```

### Pre-existing ERROR tests (14) — shared in-memory DB state contamination

```
tests/test_auth_flow.py::test_athlete_with_no_login_cannot_log_in
tests/test_auth_flow.py::test_create_login_rejects_duplicate_for_same_athlete
tests/test_auth_flow.py::test_create_login_rejects_email_already_taken
tests/test_auth_flow.py::test_create_login_requires_athlete_belongs_to_parent
tests/test_auth_flow.py::test_create_login_requires_existing_parent
tests/test_auth_flow.py::test_login_parent_is_case_insensitive
tests/test_auth_flow.py::test_login_parent_with_no_athletes_returns_empty_list
tests/test_auth_flow.py::test_login_resolves_athlete_after_login_created
tests/test_auth_flow.py::test_login_resolves_parent_with_athletes
tests/test_auth_flow.py::test_login_unknown_email_404
tests/test_auth_flow.py::test_parent_takes_precedence_over_athlete_login
tests/test_blueprint_route.py::test_blueprint_get_does_not_500_for_age_ge_14
tests/test_fueliq_daily_challenge_route.py::test_daily_challenge_verdict_404_when_nothing_scheduled  ← see isolation note below
tests/test_fueliq_daily_challenge_route.py::test_daily_challenge_verdict_does_not_appear_in_fueliq_hub_score  ← see isolation note below
```

### Known isolation issue — `test_fueliq_daily_challenge_route`

Three tests in `tests/test_fueliq_daily_challenge_route.py` behave differently depending on run order:
- `test_daily_challenge_verdict_flow_end_to_end` — FAILS under full suite, PASSES individually
- `test_daily_challenge_verdict_404_when_nothing_scheduled` — ERROR under full suite, PASSES individually
- `test_daily_challenge_verdict_does_not_appear_in_fueliq_hub_score` — ERROR under full suite, PASSES individually

Root cause: shared in-memory SQLite DB contaminated by earlier test suites (likely `test_fueliq_route.py` leaving uncommitted state). Not urgent — fix when the daily challenge tests need to be extended. Do not count these as Phase regressions.
