import os
os.environ.setdefault("TEAM_COACH_SESSION_SECRET", "test-secret")
os.environ.setdefault("ADMIN_SESSION_SECRET", "admin-secret")
os.environ.setdefault("ADMIN_PASSWORD", "adminpass")

import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.database import get_conn
from db.setup import init_db
from api.services.teamcoach_auth_service import hash_password, mint_token


@pytest.fixture(autouse=True)
def seed():
    init_db()
    conn = get_conn()
    pw_hash, salt = hash_password("pw")
    conn.execute(
        "INSERT OR IGNORE INTO coaches (id,name,email,password_hash,salt) "
        "VALUES (1,'Coach','c@c.com',?,?)", (pw_hash, salt)
    )
    conn.execute(
        "INSERT OR IGNORE INTO teams (id,name,season,threshold_pct) "
        "VALUES (1,'U16','Fall 2026',80)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO coach_team_access (coach_id,team_id) VALUES (1,1)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO parents (id,full_name,email,consent_timestamp) "
        "VALUES (1,'P','p@e.com','2026-01-01')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO athletes "
        "(id,parent_id,first_name,age,gender,weight_lbs,height_ft,height_in) "
        "VALUES (1,1,'Alice',15,'female',130,5,4)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO roster_membership (athlete_id,team_id,parent_consent_flag) "
        "VALUES (1,1,1)"
    )
    conn.commit()
    conn.close()


client = TestClient(app)
TOKEN = mint_token(coach_id=1, email="c@c.com")


def _auth():
    return {"Authorization": f"Bearer {TOKEN}"}


def test_list_teams():
    r = client.get("/api/team-coach/teams/", headers=_auth())
    assert r.status_code == 200
    teams = r.json()["teams"]
    assert len(teams) == 1
    assert teams[0]["name"] == "U16"
    assert teams[0]["threshold_pct"] == 80


def test_list_teams_no_auth_401():
    assert client.get("/api/team-coach/teams/").status_code == 401


def test_other_coach_sees_no_teams():
    other = mint_token(coach_id=99, email="x@x.com")
    r = client.get("/api/team-coach/teams/",
                   headers={"Authorization": f"Bearer {other}"})
    assert r.status_code == 200
    assert r.json()["teams"] == []


def test_get_roster():
    r = client.get("/api/team-coach/teams/1/roster", headers=_auth())
    assert r.status_code == 200
    roster = r.json()
    assert len(roster) == 1
    assert roster[0]["first_name"] == "Alice"
    assert roster[0]["join_status"] == "joined"
    assert roster[0]["logging_status"] == "no_data"
    assert "parent_consent_flag" in roster[0]


def test_roster_forbidden_for_other_coach():
    other = mint_token(coach_id=99, email="x@x.com")
    r = client.get("/api/team-coach/teams/1/roster",
                   headers={"Authorization": f"Bearer {other}"})
    assert r.status_code == 403


def test_get_engagement_empty():
    r = client.get("/api/team-coach/teams/1/engagement", headers=_auth())
    assert r.status_code == 200
    data = r.json()
    assert data["current_week"] is None
    assert data["last_updated"] is None


def test_roster_contains_no_nutrition_data():
    r = client.get("/api/team-coach/teams/1/roster", headers=_auth())
    raw = str(r.json()).lower()
    for forbidden in ["carb", "protein", "iron", "calori", "fuel_score",
                      "fuel_level", "ea_", "red_s", "ate", "complied", "performance"]:
        assert forbidden not in raw, f"Roster leaked forbidden field: {forbidden}"
