from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import parents, athletes, events, nutrition, meals, recipes, analysis, reports, notifications, meal_plans

app = FastAPI(
    title="FuelUp Youth Soccer Nutrition API",
    description="Science-backed pediatric sports nutrition platform for athletes ages 13-17. Educational food guidance — NOT medical nutrition therapy.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parents.router,   prefix="/api/parents",   tags=["1. Parental Consent"])
app.include_router(athletes.router,  prefix="/api/athletes",  tags=["2. Athlete Profiles"])
app.include_router(events.router,    prefix="/api/events",    tags=["3. Schedule"])
app.include_router(nutrition.router, prefix="/api/nutrition", tags=["4-6. Nutrition Targets + Timing"])
app.include_router(meals.router,     prefix="/api/meals",     tags=["7-8. Recipes + Meal Tracking"])
app.include_router(recipes.router,   prefix="/api/recipes",   tags=["7. Recipe Database"])
app.include_router(analysis.router,  prefix="/api/analysis",  tags=["9. Nutrient Gap Analysis"])
app.include_router(reports.router,       prefix="/api/reports",       tags=["11. Reports"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["12. Notifications"])
app.include_router(meal_plans.router,   prefix="/api/meal-plans",   tags=["10. Meal Planner"])


@app.get("/api/info")
def root():
    return {
        "app": "FuelUp Youth Soccer Nutrition Platform",
        "version": "1.0.0",
        "launch_date": "June 16, 2026",
        "built_by": "Purvi Shah MS, RDN | Food Explorers LLC",
        "science": "Everett MD 2025 | Boston Children's Hospital RDN | AAP | ACSM 2016",
        "disclaimer": "FuelUp provides educational food guidance — not medical nutrition therapy.",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# Serve React frontend — must be last so API routes take precedence
_static_dir = Path(__file__).parent.parent / "frontend" / "dist"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")
