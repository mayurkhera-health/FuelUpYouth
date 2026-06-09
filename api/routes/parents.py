from fastapi import APIRouter, HTTPException
from datetime import datetime
from api.models import ParentCreate, ParentResponse
from api.database import get_conn

router = APIRouter()


@router.post("/", response_model=ParentResponse, status_code=201)
def create_parent(data: ParentCreate):
    if not data.consent_confirmed:
        raise HTTPException(400, "Parental consent must be confirmed before creating an account.")
    conn = get_conn()
    try:
        ts = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO parents (full_name, email, consent_timestamp, consent_confirmed) VALUES (?, ?, ?, ?)",
            (data.full_name, data.email, ts, data.consent_confirmed),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM parents WHERE email = ?", (data.email,)).fetchone()
        return dict(row)
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(409, "A parent account with this email already exists.")
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@router.post("/{parent_id}/confirm")
def confirm_consent(parent_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM parents WHERE id = ?", (parent_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Parent not found.")
        conn.execute("UPDATE parents SET consent_confirmed = TRUE WHERE id = ?", (parent_id,))
        conn.commit()
        return {"message": "Consent confirmed. Welcome to FuelUp!", "parent_id": parent_id}
    finally:
        conn.close()


@router.get("/login", response_model=None)
def login(email: str):
    conn = get_conn()
    try:
        parent = conn.execute("SELECT * FROM parents WHERE email = ?", (email.strip().lower(),)).fetchone()
        if not parent:
            raise HTTPException(404, "No account found with that email address.")
        parent_dict = dict(parent)
        athletes = conn.execute(
            "SELECT * FROM athletes WHERE parent_id = ?", (parent_dict["id"],)
        ).fetchall()
        return {"parent": parent_dict, "athletes": [dict(a) for a in athletes]}
    finally:
        conn.close()


@router.delete("/test-reset")
def test_reset(email: str):
    """Delete all data for a test email — only permitted for test@gmail.com."""
    if email.strip().lower() != "test@gmail.com":
        raise HTTPException(403, "Test reset is only permitted for test@gmail.com.")
    conn = get_conn()
    try:
        parent = conn.execute("SELECT id FROM parents WHERE email = ?", (email.strip().lower(),)).fetchone()
        if parent:
            parent_id = dict(parent)["id"]
            athletes = conn.execute("SELECT id FROM athletes WHERE parent_id = ?", (parent_id,)).fetchall()
            for a in athletes:
                athlete_id = dict(a)["id"]
                conn.execute("DELETE FROM meal_logs WHERE athlete_id = ?", (athlete_id,))
                conn.execute("DELETE FROM events WHERE athlete_id = ?", (athlete_id,))
                conn.execute("DELETE FROM daily_targets WHERE athlete_id = ?", (athlete_id,))
            conn.execute("DELETE FROM athletes WHERE parent_id = ?", (parent_id,))
            conn.execute("DELETE FROM parents WHERE id = ?", (parent_id,))
            conn.commit()
        return {"message": "Test data cleared."}
    finally:
        conn.close()


@router.get("/{parent_id}", response_model=ParentResponse)
def get_parent(parent_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM parents WHERE id = ?", (parent_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Parent not found.")
        return dict(row)
    finally:
        conn.close()
