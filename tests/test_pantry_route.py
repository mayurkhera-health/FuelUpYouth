import os
os.environ["DB_PATH"] = ":memory:"
import pytest
from db.setup import init_db
from api.services.db_migrations import run_all
from api.database import get_conn

@pytest.fixture
def db():
    keep = get_conn(); init_db(); run_all()
    yield keep
    keep.close()

def test_pantry_list_items_table_exists(db):
    cols = [r[1] for r in db.execute("PRAGMA table_info(pantry_list_items)").fetchall()]
    assert cols, "pantry_list_items table missing"
    for c in ["id","athlete_id","week_start","food_id","name","cue_label",
              "purchase_unit","role","meal_context","must_have","checked"]:
        assert c in cols, f"missing column {c}"


from fastapi.testclient import TestClient
from api.main import app
import api.routes.pantry as pantry_route

@pytest.fixture
def client(db):
    with TestClient(app) as c:
        yield c

_counter = {"n": 0}

def _make_athlete(client):
    _counter["n"] += 1
    p = client.post("/api/parents/", json={"full_name":"P","email":f"pan{_counter['n']}@test.com","consent_confirmed":True})
    pid = p.json()["id"]
    a = client.post("/api/athletes/", json={"parent_id":pid,"first_name":"Ari","age":15,"gender":"girl",
        "weight_lbs":110,"height_ft":5,"height_in":6})
    return a.json()["id"]

def test_generate_happy_path(client, monkeypatch):
    aid = _make_athlete(client)
    monkeypatch.setattr(pantry_route.claude_ai, "prompt8_pantry_plan",
        lambda *a, **k: {"items":[{"food_id":"banana_ripe","meal_context":"pre_training_fuel","must_have":True}], "reasoning":"go"})
    r = client.post(f"/api/pantry/generate?athlete_id={aid}&week_start=2026-06-29")
    assert r.status_code == 200, r.text
    assert r.json()["item_count"] >= 1

def test_generate_ai_fail_uses_fallback_not_502(client, monkeypatch):
    aid = _make_athlete(client)
    monkeypatch.setattr(pantry_route.claude_ai, "prompt8_pantry_plan",
        lambda *a, **k: {"items": [], "reasoning": ""})
    r = client.post(f"/api/pantry/generate?athlete_id={aid}&week_start=2026-06-29")
    assert r.status_code == 200, r.text          # fallback, not 502
    assert r.json()["item_count"] >= 1


def test_suggest_replacement_ai_fail_uses_fallback(client, monkeypatch):
    aid = _make_athlete(client)
    monkeypatch.setattr(pantry_route.claude_ai, "prompt8_pantry_plan",
        lambda *a, **k: {"items":[{"food_id":"banana_ripe","meal_context":"snacks_everyday","must_have":False}], "reasoning":""})
    client.post(f"/api/pantry/generate?athlete_id={aid}&week_start=2026-06-29")
    monkeypatch.setattr(pantry_route.claude_ai, "prompt_suggest_replacement", lambda **k: {"food_id": None})
    r = client.post("/api/pantry/suggest-replacement", json={
        "athlete_id": aid, "week_start": "2026-06-29", "food_id": "banana_ripe",
        "food_name": "Banana (ripe)", "meal_context": "snacks_everyday"})
    assert r.status_code == 200, r.text
    # a same-role replacement (carb) should have been inserted by the fallback
    names = [i["food_id"] for g in r.json()["groups"] for i in g["items"]]
    assert "banana_ripe" not in names
