"""Integration tests for intensity on the events route."""

import os
os.environ["DB_PATH"] = ":memory:"

import pytest
from fastapi.testclient import TestClient

from db.setup import init_db
from api.services.db_migrations import run_all
from api.database import get_conn
from api.main import app


@pytest.fixture
def client():
    keepalive = get_conn()  # keep the shared in-memory DB alive across requests
    init_db()
    run_all()
    with TestClient(app) as c:
        yield c
    keepalive.close()


_counter = {"n": 0}

def _make_athlete(client, level):
    _counter["n"] += 1
    email = f"intensity{_counter['n']}@example.com"
    p = client.post("/api/parents/", json={"full_name": "P", "email": email, "consent_confirmed": True})
    assert p.status_code == 201, p.text
    parent_id = p.json()["id"]
    a = client.post("/api/athletes/", json={
        "parent_id": parent_id, "first_name": "A", "age": 14, "gender": "girl",
        "weight_lbs": 110, "height_ft": 5, "height_in": 6, "competition_level": level,
    })
    assert a.status_code == 201, a.text
    return a.json()["id"]


def test_explicit_intensity_is_stored(client):
    aid = _make_athlete(client, "Recreational")
    r = client.post("/api/events/", json={
        "athlete_id": aid, "event_name": "Game", "event_type": "game",
        "event_date": "2026-06-21", "intensity": "High",
    })
    assert r.status_code == 201, r.text
    assert r.json()["intensity"] == "high"


def test_omitted_intensity_is_derived(client):
    aid = _make_athlete(client, "Elite Club")
    r = client.post("/api/events/", json={
        "athlete_id": aid, "event_name": "Game", "event_type": "game",
        "event_date": "2026-06-21",
    })
    assert r.status_code == 201, r.text
    assert r.json()["intensity"] == "high"  # Elite Club game


def test_rest_event_derives_low_for_elite(client):
    aid = _make_athlete(client, "Elite Club")
    r = client.post("/api/events/", json={
        "athlete_id": aid, "event_name": "Yoga", "event_type": "rest",
        "event_date": "2026-06-22",
    })
    assert r.status_code == 201, r.text
    assert r.json()["intensity"] == "low"
