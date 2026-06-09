import urllib.request
from fastapi import APIRouter, HTTPException
from typing import List
from api.models import EventCreate, EventResponse
from api.database import get_conn

router = APIRouter()


@router.get("/fetch-ics")
def fetch_ics(url: str):
    if not url.startswith("http"):
        raise HTTPException(400, "Invalid URL.")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FuelUp/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        return {"content": content}
    except Exception as e:
        raise HTTPException(502, f"Could not fetch calendar: {str(e)}")


@router.post("/", response_model=EventResponse, status_code=201)
def create_event(data: EventCreate):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM athletes WHERE id = ?", (data.athlete_id,)).fetchone():
            raise HTTPException(404, "Athlete not found.")
        conn.execute(
            "INSERT INTO events (athlete_id, event_name, event_type, event_date, start_time, duration_hours, city) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data.athlete_id, data.event_name, data.event_type, data.event_date, data.start_time, data.duration_hours, data.city),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM events WHERE rowid = last_insert_rowid()").fetchone()
        return dict(row)
    finally:
        conn.close()


@router.get("/athlete/{athlete_id}", response_model=List[EventResponse])
def get_athlete_events(athlete_id: int, date: str = None):
    conn = get_conn()
    try:
        if date:
            rows = conn.execute(
                "SELECT * FROM events WHERE athlete_id = ? AND event_date = ? ORDER BY start_time",
                (athlete_id, date),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events WHERE athlete_id = ? ORDER BY event_date, start_time",
                (athlete_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: int):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Event not found.")
        return dict(row)
    finally:
        conn.close()


@router.delete("/{event_id}")
def delete_event(event_id: int):
    conn = get_conn()
    try:
        if not conn.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone():
            raise HTTPException(404, "Event not found.")
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        return {"message": "Event deleted.", "event_id": event_id}
    finally:
        conn.close()
