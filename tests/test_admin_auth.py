"""Admin auth: token gating, login success/failure, rate limiting."""

import os
os.environ["DB_PATH"] = ":memory:"

import pytest
from fastapi.testclient import TestClient

from db.setup import init_db
from api.services.db_migrations import run_all
from api.database import get_conn
from api.services import admin_auth
from api.main import app

PASSWORD = "s3cret-admin"


@pytest.fixture
def client(monkeypatch):
    keepalive = get_conn()  # keep the shared in-memory DB alive across requests
    init_db()
    run_all()
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "unit-test-signing-key")
    admin_auth._failed_logins.clear()  # reset the in-memory throttle per test
    with TestClient(app) as c:
        yield c
    keepalive.close()


def _token(c):
    r = c.post("/api/admin/login", json={"password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def test_admin_routes_401_without_token(client):
    assert client.get("/api/admin/users").status_code == 401
    assert client.get("/api/admin/analytics/overview").status_code == 401
    assert client.get("/api/admin/analytics/funnel").status_code == 401


def test_login_wrong_password_401(client):
    r = client.post("/api/admin/login", json={"password": "nope"})
    assert r.status_code == 401


def test_login_success_returns_working_token(client):
    token = _token(client)
    assert token and "." in token
    r = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_bad_token_rejected(client):
    r = client.get("/api/admin/users", headers={"Authorization": "Bearer garbage.token"})
    assert r.status_code == 401


def test_login_not_configured_503(client, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    r = client.post("/api/admin/login", json={"password": "anything"})
    assert r.status_code == 503


def test_rate_limit_locks_after_five_failures(client):
    for _ in range(5):
        assert client.post("/api/admin/login", json={"password": "wrong"}).status_code == 401
    # 6th attempt is throttled — even with the correct password.
    r = client.post("/api/admin/login", json={"password": PASSWORD})
    assert r.status_code == 429
