"""Onboarding-wizard `food_preferences` field:
migration (idempotent + column add), create/read round-trip through the API,
and AI-coach context integration (included when present, omitted when null)."""

import os
os.environ["DB_PATH"] = ":memory:"

import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from db.setup import init_db
from api.services.db_migrations import run_all, _add_food_preferences_to_athletes
from api.database import get_conn
from api.main import app
from api.services.coach_service import build_system_prompt


# ── Migration ────────────────────────────────────────────────────────────────

def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_food_preferences_migration_adds_column():
    conn = _mk_conn()
    conn.execute("CREATE TABLE athletes (id INTEGER PRIMARY KEY)")
    _add_food_preferences_to_athletes(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(athletes)").fetchall()}
    assert "food_preferences" in cols


def test_food_preferences_migration_is_idempotent():
    conn = _mk_conn()
    conn.execute("CREATE TABLE athletes (id INTEGER PRIMARY KEY)")
    _add_food_preferences_to_athletes(conn)
    _add_food_preferences_to_athletes(conn)  # second run must not raise
    cols = [r[1] for r in conn.execute("PRAGMA table_info(athletes)").fetchall()]
    assert cols.count("food_preferences") == 1


# ── Create + read round-trip ─────────────────────────────────────────────────

@pytest.fixture
def client():
    keepalive = get_conn()  # keep the shared in-memory DB alive across requests
    init_db()
    run_all()
    # An athlete can only be created under a consent-confirmed parent.
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO parents (full_name, email, consent_confirmed, consent_timestamp) "
        "VALUES (?, ?, 1, ?)",
        ("Test Parent", f"fp-{uuid.uuid4().hex}@test.com", "2026-06-24T00:00:00Z"),
    )
    conn.commit()
    with TestClient(app) as c:
        c.parent_id = cur.lastrowid
        yield c
    keepalive.close()


def _athlete_payload(parent_id, **overrides):
    body = {
        "parent_id": parent_id,
        "first_name": "Sam",
        "age": 15,
        "gender": "male",
        "weight_lbs": 130.0,
        "height_ft": 5,
        "height_in": 6.0,
        "position": "Midfielder",
        "competition_level": "competitive_club",
        "season_phase": "in_season",
        "allergies": "peanuts",
        "dietary_restrictions": None,
        "food_preferences": "prefers crunchy textures, dislikes mushy foods",
        "sweat_profile": "moderate",
    }
    body.update(overrides)
    return body


def test_food_preferences_round_trips_create_and_get(client):
    pref = "prefers crunchy textures, dislikes mushy foods"
    r = client.post("/api/athletes/", json=_athlete_payload(client.parent_id))
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["food_preferences"] == pref

    got = client.get(f"/api/athletes/{created['id']}")
    assert got.status_code == 200, got.text
    assert got.json()["food_preferences"] == pref


def test_food_preferences_nullable_on_create(client):
    r = client.post("/api/athletes/", json=_athlete_payload(client.parent_id, food_preferences=None))
    assert r.status_code == 201, r.text
    assert r.json()["food_preferences"] is None


# ── Coach context ────────────────────────────────────────────────────────────

def _coach_context(food_preferences):
    """Minimal valid context for build_system_prompt — only food_preferences varies."""
    return {
        "blueprint": {
            "name": "Sam",
            "age": 15,
            "allergies": "",
            "dietary_restrictions": "",
            "food_preferences": food_preferences,
            "blueprint_summary": "",
            "sweat_profile": "",
        },
        "schedule": {
            "window_label": "Breakfast",
            "window_time": "7:30 AM",
            "category_label": "Carb-forward",
            "event_name": None,
            "event_type": "rest",
            "event_start_time": None,
            "event_city": None,
        },
        "baseline": {
            "carbs_g_min": 200, "carbs_g_max": 250,
            "protein_g_min": 60, "protein_g_max": 80,
            "hydration_oz_min": 60, "hydration_oz_max": 80,
            "lea_alert": False,
        },
        "weather": None,
    }


def test_coach_prompt_includes_food_preferences_when_present():
    prompt = build_system_prompt(_coach_context("prefers crunchy textures"), "athlete")
    assert "Food preferences" in prompt
    assert "prefers crunchy textures" in prompt


def test_coach_prompt_omits_food_preferences_when_null():
    prompt = build_system_prompt(_coach_context(None), "athlete")
    assert "Food preferences" not in prompt


def test_coach_prompt_omits_food_preferences_when_empty():
    prompt = build_system_prompt(_coach_context(""), "athlete")
    assert "Food preferences" not in prompt
