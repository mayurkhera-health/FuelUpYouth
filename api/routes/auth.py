"""
Phase 1 — Unified auth endpoint.
Resolves parent OR athlete from a single email.
Keeps /api/parents/login and /api/athletes/* intact for backward compat.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.database import get_conn

router = APIRouter()


class LoginRequest(BaseModel):
    email: str


class AthleteCreateLoginRequest(BaseModel):
    email: str          # athlete's own email (becomes their login)
    parent_email: str   # parent's email — the gate


@router.post("/login")
def unified_login(data: LoginRequest):
    """
    Single login for both personas.
    Checks parents first (most common), then athlete_logins.
    Returns { role, ...session_data }.
    """
    email = data.email.strip().lower()
    conn = get_conn()
    try:
        # 1. Parent?
        parent = conn.execute(
            "SELECT * FROM parents WHERE lower(email) = ?", (email,)
        ).fetchone()
        if parent:
            parent_d = dict(parent)
            athletes = conn.execute(
                "SELECT * FROM athletes WHERE parent_id = ?", (parent_d["id"],)
            ).fetchall()
            return {
                "role": "parent",
                "parent": parent_d,
                "athletes": [dict(a) for a in athletes],
            }

        # 2. Athlete?
        al = conn.execute(
            "SELECT * FROM athlete_logins WHERE lower(email) = ?", (email,)
        ).fetchone()
        if al:
            athlete = conn.execute(
                "SELECT * FROM athletes WHERE id = ?", (dict(al)["athlete_id"],)
            ).fetchone()
            if not athlete:
                raise HTTPException(500, "Athlete profile not found.")
            return {"role": "athlete", "athlete": dict(athlete)}

        raise HTTPException(404, "No account found with that email address.")
    finally:
        conn.close()


@router.post("/athlete-create-login/{athlete_id}")
def create_athlete_login(athlete_id: int, data: AthleteCreateLoginRequest):
    """
    Phase 0c gate: no athlete login without a verified parent account.
    1. Verify parent exists by email.
    2. Verify athlete belongs to that parent.
    3. Create athlete_logins row.
    """
    email = data.email.strip().lower()
    parent_email = data.parent_email.strip().lower()
    conn = get_conn()
    try:
        # Gate 1: parent must exist
        parent = conn.execute(
            "SELECT id FROM parents WHERE lower(email) = ?", (parent_email,)
        ).fetchone()
        if not parent:
            raise HTTPException(
                403,
                "Ask your parent to set up FuelUp first — no parent account was found for that email.",
            )
        parent_id = dict(parent)["id"]

        # Gate 2: athlete must belong to this parent
        athlete = conn.execute(
            "SELECT * FROM athletes WHERE id = ? AND parent_id = ?",
            (athlete_id, parent_id),
        ).fetchone()
        if not athlete:
            raise HTTPException(
                403, "This athlete profile is not linked to that parent account."
            )

        # Create login credentials
        try:
            conn.execute(
                "INSERT INTO athlete_logins (email, athlete_id) VALUES (?, ?)",
                (email, athlete_id),
            )
            conn.commit()
        except Exception as e:
            if "UNIQUE" in str(e):
                raise HTTPException(409, "An account with that email already exists.")
            raise HTTPException(500, str(e))

        return {"role": "athlete", "athlete": dict(athlete)}
    finally:
        conn.close()
