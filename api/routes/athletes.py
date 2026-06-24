import json
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, HTTPException
from api.models import AthleteCreate, AthleteResponse
from api.database import get_conn
from api.services.nutrition_calc import calc_daily_targets
from api.services.fueling_targets import normalize_season_phase
from api.services import claude_ai

router = APIRouter()

_EVENT_TYPES = ["rest", "practice", "game", "tournament", "strength"]
# A generating task that hasn't written a result after this many seconds is
# considered dead (killed by a deploy or crashed without writing the error sentinel).
_STALE_GENERATING_SECONDS = 120


def _computed_calculated(athlete: dict) -> dict:
    """Derive the _calculated block from athlete physical stats. No LLM needed."""
    gender = athlete.get("gender", "").lower()
    is_girl = gender in ("girl", "female", "f")
    calculated = {
        "rmr": round(
            11.1 * athlete["weight_lbs"] * 0.453592
            + 8.4 * (athlete["height_ft"] * 12 + athlete["height_in"]) * 2.54
            - (537 if is_girl else 340)
        ),
        "iron_mg": 15 if is_girl else 11,
        "calcium_mg": 1300,
        "magnesium_mg": (360 if is_girl else 410) if athlete["age"] >= 14 else 240,
        "vitamin_d_iu": 1000,
        "ffm_kg": round(athlete["weight_lbs"] * 0.453592 * 0.85, 1),
        "targets": {et: calc_daily_targets(athlete, et) for et in _EVENT_TYPES},
    }
    calculated["lea_threshold_kcal"] = round(30 * calculated["ffm_kg"])
    return calculated


def generate_blueprint_bg(athlete_id: int) -> None:
    """
    Background task: calls Bedrock, writes blueprint or an error sentinel.
    Runs after the HTTP response is already sent — never blocks a request.
    """
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            return
        athlete = dict(row)

        # Write the in-progress sentinel before the blocking Bedrock call so
        # GET /blueprint can distinguish "task started" from "task not yet begun".
        started_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE athletes SET blueprint_json=? WHERE id=?",
            (json.dumps({"__status": "generating", "started_at": started_at}), athlete_id),
        )
        conn.commit()

        targets_by_event = {et: calc_daily_targets(athlete, et) for et in _EVENT_TYPES}
        blueprint = claude_ai.prompt0_athlete_blueprint(athlete, targets_by_event)
        conn.execute(
            "UPDATE athletes SET blueprint_json=? WHERE id=?",
            (json.dumps(blueprint), athlete_id),
        )
        conn.commit()
    except Exception as exc:
        try:
            conn.execute(
                "UPDATE athletes SET blueprint_json=? WHERE id=?",
                (json.dumps({"__status": "error", "message": str(exc)}), athlete_id),
            )
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()


@router.post("/", response_model=AthleteResponse, status_code=201)
def create_athlete(data: AthleteCreate, background_tasks: BackgroundTasks):
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
                position, competition_level, sweat_profile, allergies, dietary_restrictions, supplement_use,
                season_phase, food_preferences)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data.parent_id, data.first_name, data.age, data.gender, data.weight_lbs,
             data.height_ft, data.height_in, data.position, data.competition_level,
             data.sweat_profile, data.allergies, data.dietary_restrictions, data.supplement_use,
             normalize_season_phase(data.season_phase), data.food_preferences),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM athletes WHERE rowid = last_insert_rowid()").fetchone()
        athlete = dict(row)
        # Blueprint runs after response is sent — never blocks athlete creation.
        background_tasks.add_task(generate_blueprint_bg, athlete["id"])
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
        existing = conn.execute(
            "SELECT season_phase, food_preferences FROM athletes WHERE id = ?", (athlete_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Athlete not found.")
        # Preserve the stored season_phase when the client omits it (older app
        # builds don't send the field — don't clobber it back to the default).
        season_phase = normalize_season_phase(
            data.season_phase if data.season_phase is not None else existing["season_phase"]
        )
        # Same preserve-on-omit rule for food_preferences: an older build (or any
        # PUT that doesn't carry the field) must not null out an existing value.
        # A client clearing it sends "" (not None), which overwrites as intended.
        food_preferences = (
            data.food_preferences if data.food_preferences is not None else existing["food_preferences"]
        )
        conn.execute(
            """UPDATE athletes SET
               first_name=?, age=?, gender=?, weight_lbs=?, height_ft=?, height_in=?,
               position=?, competition_level=?, sweat_profile=?, allergies=?,
               dietary_restrictions=?, supplement_use=?, season_phase=?, food_preferences=?
               WHERE id=?""",
            (data.first_name, data.age, data.gender, data.weight_lbs, data.height_ft,
             data.height_in, data.position, data.competition_level, data.sweat_profile,
             data.allergies, data.dietary_restrictions, data.supplement_use,
             season_phase, food_preferences, athlete_id),
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

        # No blueprint_json at all — background task hasn't started yet.
        if not blueprint_str:
            raise HTTPException(
                404,
                detail={"status": "pending", "message": "Blueprint is being generated."},
            )

        try:
            blueprint_data = json.loads(blueprint_str)
        except (json.JSONDecodeError, TypeError):
            return {
                "athlete_id": athlete_id,
                "status": "error",
                "message": "Blueprint data is invalid.",
                "_calculated": _computed_calculated(athlete),
            }

        # Sentinel written by generate_blueprint_bg — check status.
        if isinstance(blueprint_data, dict) and "__status" in blueprint_data:
            sentinel_status = blueprint_data["__status"]

            if sentinel_status == "generating":
                # Detect stale tasks (killed by a deploy without writing a result).
                started_at_str = blueprint_data.get("started_at")
                is_stale = True  # assume stale if no timestamp
                if started_at_str:
                    try:
                        started = datetime.fromisoformat(started_at_str)
                        age_secs = (datetime.now(timezone.utc) - started).total_seconds()
                        is_stale = age_secs > _STALE_GENERATING_SECONDS
                    except Exception:
                        is_stale = True

                if is_stale:
                    return {
                        "athlete_id": athlete_id,
                        "status": "error",
                        "message": "Blueprint generation timed out. Tap Retry to try again.",
                        "_calculated": _computed_calculated(athlete),
                    }
                raise HTTPException(
                    404,
                    detail={"status": "pending", "message": "Blueprint is being generated."},
                )

            if sentinel_status == "error":
                return {
                    "athlete_id": athlete_id,
                    "status": "error",
                    "message": blueprint_data.get("message", "Blueprint generation failed."),
                    "_calculated": _computed_calculated(athlete),
                }

        # Valid blueprint object.
        return {
            "athlete_id": athlete_id,
            "status": "ready",
            "blueprint": blueprint_data,
            "_calculated": _computed_calculated(athlete),
        }
    finally:
        conn.close()


@router.post("/{athlete_id}/regenerate-blueprint", status_code=202)
def regenerate_blueprint(athlete_id: int, background_tasks: BackgroundTasks):
    """
    Re-trigger blueprint generation for an athlete whose prior attempt failed.
    Returns 202 immediately; Bedrock runs in the background.
    """
    conn = get_conn()
    try:
        row = conn.execute("SELECT id FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        background_tasks.add_task(generate_blueprint_bg, athlete_id)
        return {"status": "pending", "message": "Blueprint generation started."}
    finally:
        conn.close()
