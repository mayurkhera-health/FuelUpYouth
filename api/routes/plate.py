"""Performance Plate — per-window plate shape + allergy-filtered food options.

GET /api/plate/window?athlete_id=&window_key=
  → { window_key, plate | null, options[] }

Display-only. `plate` is null for nudge/hydration windows (between_games etc.).
Options are 4–5 short combo labels ({short_label, plate_sections}) drawn from the
recipe library, filtered by the athlete's allergies (safety) + dietary prefs.
"""
from fastapi import APIRouter, HTTPException, Query

from api.database import get_conn
from api.services import recipe_db
from api.services.plate_config import (
    performance_plate_enabled,
    plate_for_window,
    recipe_profile_for_window,
    parse_restrictions,
    normalize_allergens,
    select_options,
)

router = APIRouter()


@router.get("/window")
def get_window_plate(
    athlete_id: int = Query(...),
    window_key: str = Query(...),
):
    # Feature flag — ships dark. When off, no DB work: return an empty payload so
    # the client renders nothing (and does no per-window plate fetch overhead).
    if not performance_plate_enabled():
        return {"window_key": window_key, "plate": None, "options": []}

    plate = plate_for_window(window_key)
    if plate is None:
        # Nudge/hydration window — no plate, no options.
        return {"window_key": window_key, "plate": None, "options": []}

    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT allergies, dietary_restrictions FROM athletes WHERE id = ?",
            (athlete_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(404, f"Athlete {athlete_id} not found")
    row = dict(row)

    allergens = normalize_allergens(parse_restrictions(row.get("allergies")))
    dietary = parse_restrictions(row.get("dietary_restrictions"))
    profile = recipe_profile_for_window(window_key)

    recipes = recipe_db.get_valid_recipes(
        profile, allergies=allergens, dietary_restrictions=dietary
    )
    options = select_options(recipes, n=5)

    return {"window_key": window_key, "plate": plate, "options": options}
