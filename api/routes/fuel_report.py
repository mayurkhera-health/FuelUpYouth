from fastapi import APIRouter, HTTPException, Query
from api.services.fuel_report_service import build_fuel_report

router = APIRouter()


@router.get("/{athlete_id}/fuel-report")
def get_fuel_report(
    athlete_id: int,
    week_start: str | None = Query(None, description="ISO Monday date, e.g. 2026-06-09"),
):
    """
    Fuel Report v2 — training load + confirmation tap rates.
    No meal logging required. Meaningful at zero taps.
    Safety flag is PARENT-ONLY and fires only when load is high AND rate is low.
    """
    report = build_fuel_report(athlete_id, week_start=week_start)
    if report is None:
        raise HTTPException(404, "Athlete not found")
    return report


@router.post("/{athlete_id}/confirmations")
def record_confirmation(
    athlete_id: int,
    body: dict,
):
    """
    Record a YES tap for a fuel window.
    Body: { window_key, window_type, log_date }
    window_type must be one of: pre_fuel, recovery
    Idempotent — double-taps are silently ignored (UNIQUE constraint).
    """
    window_key  = body.get("window_key")
    window_type = body.get("window_type")
    log_date    = body.get("log_date")

    if not all([window_key, window_type, log_date]):
        raise HTTPException(400, "window_key, window_type, and log_date are required")
    if window_type not in ("pre_fuel", "recovery", "hydration"):
        raise HTTPException(400, f"Invalid window_type: {window_type}")

    from api.database import get_conn
    from api.services import streak_service
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO confirmations (athlete_id, log_date, window_key, window_type) "
            "VALUES (?, ?, ?, ?)",
            (athlete_id, log_date, window_key, window_type),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM confirmations WHERE athlete_id = ? AND window_key = ? AND log_date = ?",
            (athlete_id, window_key, log_date),
        ).fetchone()
        streak = streak_service.register_confirmation(athlete_id, conn, today=log_date)
        return {**dict(row), "streak": streak}
    finally:
        conn.close()


@router.delete("/{athlete_id}/confirmations")
def unrecord_confirmation(
    athlete_id: int,
    window_key: str = Query(...),
    log_date:   str = Query(...),
):
    """
    Undo a YES tap (user changed their mind).
    """
    from api.database import get_conn
    conn = get_conn()
    try:
        conn.execute(
            "DELETE FROM confirmations WHERE athlete_id = ? AND window_key = ? AND log_date = ?",
            (athlete_id, window_key, log_date),
        )
        conn.commit()
        return {"deleted": True}
    finally:
        conn.close()
