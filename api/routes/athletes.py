import json
from fastapi import APIRouter, HTTPException
from api.models import AthleteCreate, AthleteResponse
from api.database import get_conn
from api.services.nutrition_calc import calc_daily_targets
from api.services import claude_ai

router = APIRouter()


@router.post("/", response_model=AthleteResponse, status_code=201)
def create_athlete(data: AthleteCreate):
    if not (9 <= data.age <= 17):
        raise HTTPException(400, "Fueling2Win is designed for athletes ages 9-17.")
    conn = get_conn()
    try:
        parent = conn.execute(
            "SELECT * FROM parents WHERE id = ? AND consent_confirmed = TRUE", (data.parent_id,)
        ).fetchone()
        if not parent:
            raise HTTPException(403, "Parent consent must be confirmed before adding an athlete profile.")
        conn.execute(
            """INSERT INTO athletes
               (parent_id, first_name, age, gender, weight_lbs, height_ft, height_in,
                position, competition_level, sweat_profile, allergies, dietary_restrictions, supplement_use)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data.parent_id, data.first_name, data.age, data.gender, data.weight_lbs,
             data.height_ft, data.height_in, data.position, data.competition_level,
             data.sweat_profile, data.allergies, data.dietary_restrictions, data.supplement_use),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM athletes WHERE rowid = last_insert_rowid()").fetchone()
        athlete = dict(row)

        # Generate Blueprint (Prompt 0) — runs async-style but blocking is fine on creation
        try:
            event_types = ["rest", "practice", "game", "tournament", "strength"]
            targets_by_event = {et: calc_daily_targets(athlete, et) for et in event_types}
            blueprint = claude_ai.prompt0_athlete_blueprint(athlete, targets_by_event)
            blueprint_str = json.dumps(blueprint)
            conn2 = get_conn()
            conn2.execute(
                "UPDATE athletes SET blueprint_json=? WHERE id=?",
                (blueprint_str, athlete["id"])
            )
            conn2.commit()
            conn2.close()
            athlete["blueprint_json"] = blueprint_str
        except Exception:
            pass  # Blueprint failure must never block athlete creation

        return athlete
    finally:
        conn.close()


@router.get("/{athlete_id}", response_model=AthleteResponse)
def get_athlete(athlete_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        return dict(row)
    finally:
        conn.close()


@router.put("/{athlete_id}", response_model=AthleteResponse)
def update_athlete(athlete_id: int, data: AthleteCreate):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM athletes WHERE id = ?", (athlete_id,)).fetchone():
            raise HTTPException(404, "Athlete not found.")
        conn.execute(
            """UPDATE athletes SET
               first_name=?, age=?, gender=?, weight_lbs=?, height_ft=?, height_in=?,
               position=?, competition_level=?, sweat_profile=?, allergies=?,
               dietary_restrictions=?, supplement_use=?
               WHERE id=?""",
            (data.first_name, data.age, data.gender, data.weight_lbs, data.height_ft,
             data.height_in, data.position, data.competition_level, data.sweat_profile,
             data.allergies, data.dietary_restrictions, data.supplement_use, athlete_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        return dict(row)
    finally:
        conn.close()



@router.get("/{athlete_id}/blueprint")
def get_blueprint(athlete_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        athlete = dict(row)
        blueprint_str = athlete.get("blueprint_json")

        # If no blueprint stored yet, generate now (covers athletes created before this feature)
        if not blueprint_str:
            event_types = ["rest", "practice", "game", "tournament", "strength"]
            targets_by_event = {et: calc_daily_targets(athlete, et) for et in event_types}
            blueprint = claude_ai.prompt0_athlete_blueprint(athlete, targets_by_event)
            blueprint_str = json.dumps(blueprint)
            conn.execute(
                "UPDATE athletes SET blueprint_json=? WHERE id=?",
                (blueprint_str, athlete_id)
            )
            conn.commit()

        # Also attach _calculated for React to use numbers from
        event_types = ["rest", "practice", "game", "tournament", "strength"]
        gender = athlete.get("gender", "").lower()
        is_girl = gender in ("girl", "female", "f")
        calculated = {
            "rmr": round(
                11.1 * athlete["weight_lbs"] * 0.453592 + 8.4 * (athlete["height_ft"] * 12 + athlete["height_in"]) * 2.54
                - (537 if is_girl else 340)
            ),
            "iron_mg": 15 if is_girl else 11,
            "calcium_mg": 1300,
            "magnesium_mg": (360 if is_girl else 410) if athlete["age"] >= 14 else 240,
            "vitamin_d_iu": 1000,
            "ffm_kg": round(athlete["weight_lbs"] * 0.453592 * 0.85, 1),
            "targets": {et: calc_daily_targets(athlete, et) for et in event_types},
        }
        calculated["lea_threshold_kcal"] = round(30 * calculated["ffm_kg"])

        return {
            "athlete_id": athlete_id,
            "blueprint": json.loads(blueprint_str),
            "_calculated": calculated,
        }
    finally:
        conn.close()
