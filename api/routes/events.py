import urllib.request
from fastapi import APIRouter, HTTPException
from typing import List
from api.models import EventCreate, EventUpdate, EventResponse
from api.database import get_conn
from api.services.window_templates import on_event_added_or_changed
from api.services.nutrition_calc import derive_intensity

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
        athlete = conn.execute(
            "SELECT id, competition_level FROM athletes WHERE id = ?", (data.athlete_id,)
        ).fetchone()
        if not athlete:
            raise HTTPException(404, "Athlete not found.")

        intensity = data.intensity or derive_intensity(data.event_type, athlete["competition_level"])

        conn.execute(
            "INSERT INTO events (athlete_id, event_name, event_type, event_date, start_time, duration_hours, city, venue_name, address, latitude, longitude, intensity) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (data.athlete_id, data.event_name, data.event_type, data.event_date, data.start_time, data.duration_hours,
             data.city, data.venue_name, data.address, data.latitude, data.longitude, intensity),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM events WHERE rowid = last_insert_rowid()").fetchone()
        on_event_added_or_changed(data.athlete_id, data.event_date, conn)
        return dict(row)
    finally:
        conn.close()


@router.put("/{event_id}", response_model=EventResponse)
def update_event(event_id: int, data: EventUpdate):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Event not found.")
        existing = dict(row)

        new_name     = data.event_name     if data.event_name     is not None else existing["event_name"]
        new_type     = data.event_type     if data.event_type     is not None else existing["event_type"]
        new_date     = data.event_date     if data.event_date     is not None else existing["event_date"]
        new_start    = data.start_time     if data.start_time     is not None else existing["start_time"]
        new_dur      = data.duration_hours if data.duration_hours is not None else existing["duration_hours"]
        new_city     = data.city           if data.city           is not None else existing["city"]
        new_venue    = data.venue_name     if data.venue_name     is not None else existing["venue_name"]
        new_address  = data.address        if data.address        is not None else existing["address"]
        new_lat      = data.latitude       if data.latitude       is not None else existing["latitude"]
        new_lng      = data.longitude      if data.longitude      is not None else existing["longitude"]
        if data.intensity is not None:
            new_intensity = data.intensity
        elif existing["intensity"]:
            new_intensity = existing["intensity"]
        else:
            athlete = conn.execute(
                "SELECT competition_level FROM athletes WHERE id = ?", (existing["athlete_id"],)
            ).fetchone()
            level = athlete["competition_level"] if athlete else None
            new_intensity = derive_intensity(new_type, level)

        conn.execute(
            "UPDATE events SET event_name=?, event_type=?, event_date=?, start_time=?, duration_hours=?, "
            "city=?, venue_name=?, address=?, latitude=?, longitude=?, intensity=? WHERE id=?",
            (new_name, new_type, new_date, new_start, new_dur,
             new_city, new_venue, new_address, new_lat, new_lng, new_intensity, event_id),
        )
        conn.commit()
        updated = dict(conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone())
        on_event_added_or_changed(existing["athlete_id"], new_date, conn)
        # Also recalculate old date if date changed
        if data.event_date and data.event_date != existing["event_date"]:
            on_event_added_or_changed(existing["athlete_id"], existing["event_date"], conn)
        return updated
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
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Event not found.")
        ev = dict(row)
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        on_event_added_or_changed(ev["athlete_id"], ev["event_date"], conn)
        return {"message": "Event deleted.", "event_id": event_id}
    finally:
        conn.close()
