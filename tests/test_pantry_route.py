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
