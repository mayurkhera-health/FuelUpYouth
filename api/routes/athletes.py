from fastapi import APIRouter, HTTPException
from api.models import AthleteCreate, AthleteResponse
from api.database import get_conn

router = APIRouter()

UNSAFE_SUPPLEMENTS = {
    "protein powder": "Protein powder is not recommended for adolescent athletes. Whole food protein sources are superior. (Boston Children's Hospital RDN)",
    "creatine": "Creatine is NOT approved for athletes under 18 — not recommended for pediatric use. (Boston Children's Hospital RDN)",
    "energy drink": "Energy drinks contain caffeine levels dangerous for adolescents and are linked to cardiac events in youth. (Boston Children's Hospital RDN, AAP)",
}


@router.post("/", response_model=AthleteResponse, status_code=201)
def create_athlete(data: AthleteCreate):
    if not (9 <= data.age <= 17):
        raise HTTPException(400, "FuelUp MVP is designed for athletes ages 9-17.")
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
        return dict(row)
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


@router.get("/{athlete_id}/supplement-check")
def supplement_check(athlete_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        supplement_use = (dict(row).get("supplement_use") or "").lower()
        flags = [msg for key, msg in UNSAFE_SUPPLEMENTS.items() if key in supplement_use]
        return {"athlete_id": athlete_id, "supplement_use": supplement_use, "flags": flags, "has_concerns": bool(flags)}
    finally:
        conn.close()
