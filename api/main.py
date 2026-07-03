from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)
from pathlib import Path
from fastapi import FastAPI

from api.startup import run_startup

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Starlette ignores @app.on_event("startup") when a lifespan is set, so the
        # db_migrations.run_all() registered there never runs. Invoke it here (first,
        # before knowledge ingest) so schema migrations actually apply on deploy.
        from api.services import db_migrations
        db_migrations.run_all()
        run_startup()
    except Exception:
        logger.exception("Startup migrations/ingest failed — coach may be unavailable")

    # Start the 15-min notification scheduler HERE — @app.on_event("startup") is
    # ignored by Starlette when a lifespan handler is set.
    try:
        from api.services.notification_service import run_notification_tick
        from api.services.ics_sync import run_calendar_sync_tick
        from api.services.health_service import instrument_job, run_health_tick, run_health_daily
        # Wrap the two existing jobs so they record scheduler heartbeats — no change
        # to the jobs' own logic; the wrapper only stamps last_run/last_success.
        _scheduler.add_job(instrument_job("notifications", run_notification_tick), "interval", minutes=15,
                           id="notifications", replace_existing=True)
        _scheduler.add_job(instrument_job("calendar_sync", run_calendar_sync_tick), "interval", hours=6,
                           id="calendar_sync", replace_existing=True)
        # System Health: active probes every 15 min, one daily inference probe.
        _scheduler.add_job(run_health_tick, "interval", minutes=15,
                           id="health", replace_existing=True)
        _scheduler.add_job(run_health_daily, "cron", hour=9,
                           id="health_daily", replace_existing=True)
        if not _scheduler.running:
            _scheduler.start()
        logger.info("Schedulers started (notifications 15-min, calendar sync 6-hr, health 15-min + daily).")
    except Exception:
        logger.exception("Scheduler failed to start")

    yield


from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from api.routes import parents, athletes, events, nutrition, meals, recipes, analysis, reports, notifications, meal_plans, meal_plan_selections, today, water, knowledge, legal, library, auth, fuel_report, report_config, coach, shopping, support, onboarding, pantry, feedback, calendar, admin, admin_analytics, admin_health, admin_overview, admin_action_hub
from api.services import db_migrations
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(
    title="Fueling2Win Soccer Nutrition API",
    description="Science-backed pediatric sports nutrition platform for athletes ages 13-17. Educational food guidance — NOT medical nutrition therapy.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/auth",      tags=["0. Auth"])
app.include_router(parents.router,   prefix="/api/parents",   tags=["1. Parental Consent"])
app.include_router(athletes.router,  prefix="/api/athletes",  tags=["2. Athlete Profiles"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["2b. Onboarding"])
app.include_router(events.router,    prefix="/api/events",    tags=["3. Schedule"])
app.include_router(nutrition.router, prefix="/api/nutrition", tags=["4-6. Nutrition Targets + Timing"])
app.include_router(meals.router,     prefix="/api/meals",     tags=["7-8. Recipes + Meal Tracking"])
app.include_router(recipes.router,   prefix="/api/recipes",   tags=["7. Recipe Database"])
app.include_router(analysis.router,  prefix="/api/analysis",  tags=["9. Nutrient Gap Analysis"])
app.include_router(reports.router,       prefix="/api/reports",       tags=["11. Reports"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["12. Notifications"])
app.include_router(meal_plans.router,            prefix="/api/meal-plans",   tags=["10. Meal Planner"])
app.include_router(meal_plan_selections.router,  prefix="/api/meal-plan",    tags=["10b. Meal Plan Selections"])
app.include_router(today.router,        prefix="/api/athletes",     tags=["13. Today Screen"])
app.include_router(water.router,        prefix="/api/water-log",    tags=["14. Water Log"])
app.include_router(knowledge.router,    prefix="/api/knowledge",    tags=["15. Knowledge Base"])
app.include_router(legal.router,        prefix="/api/legal",        tags=["16. Legal Documents"])
app.include_router(library.router,      prefix="/api/library",      tags=["17. Content Library"])
app.include_router(fuel_report.router,  prefix="/api/athletes",     tags=["18. Fuel Report v2"])
app.include_router(report_config.router, prefix="/api/report-config", tags=["19. Report Config"])
app.include_router(coach.router,         prefix="/api/coach",         tags=["20. Nutrition Coach"])
app.include_router(shopping.router,      prefix="/api/shopping",      tags=["21. Shopping"])
app.include_router(support.router,       prefix="/api/support",       tags=["22. Support"])
app.include_router(pantry.router,        prefix="/api/pantry",        tags=["23. Pantry Planner"])
app.include_router(feedback.router,      prefix="/api/feedback",      tags=["24. Feature Requests"])
app.include_router(calendar.router,      prefix="/api/athletes",      tags=["25. Calendar Sync"])
app.include_router(admin.router,           prefix="/api/admin",           tags=["26. Admin"])
app.include_router(admin_analytics.router, prefix="/api/admin",           tags=["27. Admin Analytics"])
app.include_router(admin_health.router,    prefix="/api/admin",           tags=["28. Admin Health"])
app.include_router(admin_overview.router,  prefix="/api/admin",           tags=["29. Admin Overview"])
app.include_router(admin_action_hub.router, prefix="/api/admin",          tags=["30. Admin Action Hub"])


_scheduler = BackgroundScheduler()


@app.get("/api/info")
def root():
    return {
        "app": "Fueling2Win Soccer Nutrition Platform",
        "version": "1.0.0",
        "launch_date": "June 16, 2026",
        "built_by": "Purvi Shah MS, RDN | Food Explorers LLC",
        "science": "Everett MD 2025 | Boston Children's Hospital RDN | AAP | ACSM 2016",
        "disclaimer": "Fueling2Win provides educational food guidance — not medical nutrition therapy.",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


class SPAStaticFiles(StaticFiles):
    """Serve the built React SPA and fall back to index.html for client-side
    routes (e.g. /admin, /admin/library) so deep links / refreshes don't 404.
    The app has no router library — it reads window.location.pathname on boot —
    so every non-file path must return index.html. Genuine /api/* misses still
    return a JSON 404 (they are excluded from the fallback)."""

    async def get_response(self, path, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api"):
                response = await super().get_response("index.html", scope)
            else:
                raise
        # Cache policy: content-hashed build assets (/assets/index-<hash>.js) are
        # immutable and cache forever; everything else — index.html and the SPA
        # fallback — must revalidate every load so a new deploy shows up immediately
        # (previously index.html had no Cache-Control → browsers served it stale).
        if path.startswith("assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response


# Serve React frontend — must be last so API routes take precedence
_static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if _static_dir.exists():
    app.mount("/", SPAStaticFiles(directory=str(_static_dir), html=True), name="static")
