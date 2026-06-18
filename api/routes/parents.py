import hashlib
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from api.models import ParentCreate, ParentResponse, OTPRequest, OTPVerify
from api.database import get_conn
from api.services.email import send_otp_email

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
        return {"message": "Consent confirmed. Welcome to Fueling2Win!", "parent_id": parent_id}
    finally:
        conn.close()


@router.post("/login")
def login(data: OTPRequest):
    email = data.email.strip().lower()
    conn = get_conn()
    try:
        parent = conn.execute("SELECT * FROM parents WHERE lower(email) = lower(?)", (email,)).fetchone()
        if not parent:
            raise HTTPException(404, "No account found with that email address.")
        parent_id = dict(parent)["id"]
        athletes = conn.execute("SELECT * FROM athletes WHERE parent_id = ?", (parent_id,)).fetchall()
        return {"parent": dict(parent), "athletes": [dict(a) for a in athletes]}
    finally:
        conn.close()


@router.post("/request-otp")
def request_otp(data: OTPRequest):
    email = data.email.strip().lower()
    conn = get_conn()
    try:
        parent = conn.execute("SELECT * FROM parents WHERE lower(email) = lower(?)", (email,)).fetchone()
        if not parent:
            raise HTTPException(404, "No account found with that email address.")
        parent_id = dict(parent)["id"]

        # Rate limit: block if a code was issued in the last 60 seconds
        cutoff = (datetime.utcnow() - timedelta(seconds=60)).isoformat()
        recent = conn.execute(
            "SELECT id FROM otp_codes WHERE parent_id = ? AND created_at > ? AND used = 0",
            (parent_id, cutoff),
        ).fetchone()
        if recent:
            raise HTTPException(429, "A code was already sent. Please wait 60 seconds before requesting another.")

        code = f"{random.randint(0, 999999):06d}"
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat()

        conn.execute(
            "INSERT INTO otp_codes (parent_id, code_hash, expires_at) VALUES (?, ?, ?)",
            (parent_id, code_hash, expires_at),
        )
        conn.commit()

        send_otp_email(email, code)
        return {"message": "A 6-digit code has been sent to your email."}
    finally:
        conn.close()


@router.post("/verify-otp")
def verify_otp(data: OTPVerify):
    email = data.email.strip().lower()
    code_hash = hashlib.sha256(data.code.strip().encode()).hexdigest()
    now = datetime.utcnow().isoformat()

    conn = get_conn()
    try:
        parent = conn.execute("SELECT * FROM parents WHERE lower(email) = lower(?)", (email,)).fetchone()
        if not parent:
            raise HTTPException(404, "No account found with that email address.")
        parent_id = dict(parent)["id"]

        row = conn.execute(
            """SELECT id FROM otp_codes
               WHERE parent_id = ? AND code_hash = ? AND used = 0 AND expires_at > ?
               ORDER BY created_at DESC LIMIT 1""",
            (parent_id, code_hash, now),
        ).fetchone()

        if not row:
            raise HTTPException(401, "Invalid or expired code. Please request a new one.")

        conn.execute("UPDATE otp_codes SET used = 1 WHERE id = ?", (dict(row)["id"],))
        conn.commit()

        athletes = conn.execute(
            "SELECT * FROM athletes WHERE parent_id = ?", (parent_id,)
        ).fetchall()
        return {"parent": dict(parent), "athletes": [dict(a) for a in athletes]}
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
