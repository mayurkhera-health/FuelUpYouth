"""Admin Analytics: DB-backed cards + funnel always available; Mixpanel mocked
both ways (success + unavailable). Dashboard must never depend on Mixpanel."""

import os
os.environ["DB_PATH"] = ":memory:"

import pytest
from fastapi.testclient import TestClient

from db.setup import init_db
from api.services.db_migrations import run_all
from api.database import get_conn
from api.services import admin_auth, mixpanel_client
from api.main import app

PASSWORD = "s3cret-admin"


def _wipe(conn):
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    for (name,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
        conn.execute(f"DELETE FROM {name}")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")


@pytest.fixture
def client(monkeypatch):
    keepalive = get_conn()
    init_db()
    run_all()
    _wipe(keepalive)  # clean slate — shared in-memory DB persists across tests
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "unit-test-signing-key")
    monkeypatch.delenv("MIXPANEL_API_SECRET", raising=False)
    admin_auth._failed_logins.clear()
    mixpanel_client._cache.clear()
    mixpanel_client._last_forced.clear()

    # Two families; one athlete connected + has a meal plan → funnel + sync %.
    p1 = keepalive.execute(
        "INSERT INTO parents (full_name, email, consent_timestamp, consent_confirmed) "
        "VALUES ('A','a@x.com','t',1)").lastrowid
    a1 = keepalive.execute(
        "INSERT INTO athletes (parent_id, first_name, age, gender, weight_lbs, height_ft, height_in, byga_ics_url) "
        "VALUES (?, 'Ann', 12, 'F', 90, 5, 2, 'https://byga/a.ics')", (p1,)).lastrowid
    keepalive.execute("INSERT INTO meal_plans (athlete_id, plan_date, slot_name) VALUES (?, date('now'), 'lunch')", (a1,))
    keepalive.execute("INSERT INTO events (athlete_id, event_name, event_type, event_date, source) "
                      "VALUES (?, 'M', 'game', date('now'), 'byga')", (a1,))
    keepalive.execute("INSERT INTO events (athlete_id, event_name, event_type, event_date, source) "
                      "VALUES (?, 'M', 'game', date('now'), 'manual')", (a1,))
    p2 = keepalive.execute(
        "INSERT INTO parents (full_name, email, consent_timestamp, consent_confirmed) "
        "VALUES ('B','b@x.com','t',1)").lastrowid
    keepalive.execute("INSERT INTO athletes (parent_id, first_name, age, gender, weight_lbs, height_ft, height_in) "
                      "VALUES (?, 'Bob', 13, 'M', 100, 5, 4)", (p2,))
    keepalive.commit()

    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {c.post('/api/admin/login', json={'password': PASSWORD}).json()['token']}"})
        yield c
    keepalive.close()


def test_overview_db_cards(client):
    body = client.get("/api/admin/analytics/overview").json()
    assert body["mixpanel_available"] is False
    assert body["cards"]["families_total"]["value"] == 2
    # 2 athletes, 1 connected → 50%
    assert body["cards"]["sync_adoption"]["percent"] == 50
    assert body["cards"]["sync_adoption"]["connected"] == 1
    assert body["app_health"]["event_sources"] == {"byga": 1, "manual": 1}


def test_overview_mixpanel_unavailable_is_graceful(client):
    body = client.get("/api/admin/analytics/overview").json()
    assert body["signups_over_time"]["mixpanel"]["available"] is False
    # DB signup series still present.
    assert isinstance(body["signups_over_time"]["points"], list)


def test_deleted_parents_excluded_from_metrics(client):
    from api.database import get_conn
    conn = get_conn()
    conn.execute("ALTER TABLE parents ADD COLUMN account_status TEXT")
    # Mark family B (Bob, no calendar) as hard-deleted.
    conn.execute("UPDATE parents SET account_status = 'hard_deleted' WHERE email = 'b@x.com'")
    conn.commit()
    conn.close()
    ov = client.get("/api/admin/analytics/overview").json()
    assert ov["cards"]["families_total"]["value"] == 1        # was 2
    # Only Ann remains; she is connected → 1/1 = 100%.
    assert ov["cards"]["sync_adoption"]["total"] == 1
    assert ov["cards"]["sync_adoption"]["percent"] == 100
    fn = client.get("/api/admin/analytics/funnel").json()
    assert {s["label"]: s["value"] for s in fn["steps"]}["Signed up"] == 1


def test_funnel_steps_are_db_derived(client):
    body = client.get("/api/admin/analytics/funnel").json()
    labels = [s["label"] for s in body["steps"]]
    assert labels == ["Signed up", "Created athlete", "Connected calendar", "Built meal plan"]
    values = {s["label"]: s["value"] for s in body["steps"]}
    assert values["Signed up"] == 2
    assert values["Created athlete"] == 2
    assert values["Connected calendar"] == 1
    assert values["Built meal plan"] == 1


def test_top_events_unavailable_without_creds(client):
    body = client.get("/api/admin/analytics/events").json()
    assert body["available"] is False


def test_retention_falls_back_to_db_wau(client):
    body = client.get("/api/admin/analytics/retention").json()
    assert body["source"] == "db_wau_fallback"
    assert isinstance(body["points"], list) and len(body["points"]) == 8


def test_mixpanel_success_path_mocked(client, monkeypatch):
    monkeypatch.setenv("MIXPANEL_API_SECRET", "fake-secret")
    mixpanel_client._cache.clear()

    def fake_query(path, params):
        if path == "events":
            return {"data": {"values": {"Sign Up": {"2026-07-01": 5, "2026-07-02": 3}}}}
        return {}

    monkeypatch.setattr(mixpanel_client, "_query", fake_query)
    body = client.get("/api/admin/analytics/events").json()
    assert body["available"] is True
    assert "Sign Up" in body["data"]["data"]["values"]


def test_discover_endpoint_lists_current_map(client, monkeypatch):
    monkeypatch.setenv("MIXPANEL_API_SECRET", "fake-secret")
    mixpanel_client._cache.clear()
    monkeypatch.setattr(mixpanel_client, "_query", lambda path, params: ["Sign Up", "Athlete Created"])
    body = client.get("/api/admin/analytics/discover").json()
    assert body["discovered"]["available"] is True
    assert body["discovered"]["data"]["events"] == ["Sign Up", "Athlete Created"]
    assert "signup" in body["current_event_map"]
