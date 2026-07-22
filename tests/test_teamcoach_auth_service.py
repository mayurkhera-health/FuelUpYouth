import pytest
import os
from api.services import teamcoach_auth_service as svc


def test_hash_and_verify_password():
    pw_hash, salt = svc.hash_password("hunter2")
    assert svc.verify_password("hunter2", pw_hash, salt) is True
    assert svc.verify_password("wrong", pw_hash, salt) is False


def test_different_salts_each_call():
    _, s1 = svc.hash_password("same")
    _, s2 = svc.hash_password("same")
    assert s1 != s2


def test_mint_and_verify_token(monkeypatch):
    monkeypatch.setenv("TEAM_COACH_SESSION_SECRET", "test-secret-xyz")
    token = svc.mint_token(coach_id=7, email="coach@club.com")
    payload = svc.verify_token(token)
    assert payload is not None
    assert payload["coach_id"] == 7
    assert payload["email"] == "coach@club.com"


def test_expired_token_rejected(monkeypatch):
    monkeypatch.setenv("TEAM_COACH_SESSION_SECRET", "test-secret-xyz")
    token = svc.mint_token(coach_id=1, email="x@x.com", ttl_seconds=-1)
    assert svc.verify_token(token) is None


def test_tampered_token_rejected(monkeypatch):
    monkeypatch.setenv("TEAM_COACH_SESSION_SECRET", "test-secret-xyz")
    token = svc.mint_token(coach_id=1, email="x@x.com")
    bad = token[:-4] + "XXXX"
    assert svc.verify_token(bad) is None


def test_missing_secret_raises(monkeypatch):
    monkeypatch.delenv("TEAM_COACH_SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="TEAM_COACH_SESSION_SECRET"):
        svc.mint_token(coach_id=1, email="x@x.com")


def test_admin_token_does_not_verify_as_coach(monkeypatch):
    monkeypatch.setenv("TEAM_COACH_SESSION_SECRET", "coach-secret")
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "admin-secret")
    from api.services.admin_auth import mint_token as admin_mint
    admin_token = admin_mint()
    assert svc.verify_token(admin_token) is None
