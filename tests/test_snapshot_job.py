import pytest
from api.database import get_conn
from db.setup import init_db
from api.services.snapshot_job import generate_snapshot, generate_all_snapshots


@pytest.fixture(autouse=True)
def seed():
    init_db()
    conn = get_conn()
    conn.execute("DELETE FROM fueling_window_log WHERE athlete_id IN (1,2)")
    conn.execute("INSERT OR IGNORE INTO parents (id,full_name,email,consent_timestamp) VALUES (1,'P','p@e.com','2026-01-01')")
    conn.execute("INSERT OR IGNORE INTO athletes (id,parent_id,first_name,age,gender,weight_lbs,height_ft,height_in) VALUES (1,1,'Alice',15,'female',130,5,4)")
    conn.execute("INSERT OR IGNORE INTO athletes (id,parent_id,first_name,age,gender,weight_lbs,height_ft,height_in) VALUES (2,1,'Bob',14,'male',140,5,6)")
    conn.execute("INSERT OR IGNORE INTO teams (id,name,season,threshold_pct) VALUES (1,'U16','S',80)")
    conn.execute("INSERT OR IGNORE INTO roster_membership (athlete_id,team_id,parent_consent_flag) VALUES (1,1,1)")
    conn.execute("INSERT OR IGNORE INTO roster_membership (athlete_id,team_id,parent_consent_flag) VALUES (2,1,1)")
    conn.commit()
    conn.close()


def _log(athlete_id: int, date: str, slot: str, completed: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO fueling_window_log "
        "(athlete_id,date,window_slot,applicable,completed) VALUES (?,?,?,1,?)",
        (athlete_id, date, slot, completed),
    )
    conn.commit()
    conn.close()


def test_empty_logs_zero_above_threshold():
    result = generate_snapshot(1, week_start="2026-07-21")
    assert result["roster_count"] == 2
    assert result["players_above_threshold"] == 0


def test_athlete_above_threshold_counted():
    # Alice logs 5/6 slots = 83% — above 80% threshold
    for slot in ["everyday", "fuel_before", "top_up", "during", "recharge"]:
        _log(1, "2026-07-21", slot, 1)
    _log(1, "2026-07-21", "rebuild", 0)
    result = generate_snapshot(1, week_start="2026-07-21")
    assert result["players_above_threshold"] == 1


def test_athlete_below_threshold_not_counted():
    # Bob logs 1/6 = 17% — below 80%
    _log(2, "2026-07-21", "everyday", 1)
    result = generate_snapshot(1, week_start="2026-07-21")
    assert result["players_above_threshold"] == 0


def test_snapshot_upserted_to_db():
    generate_snapshot(1, week_start="2026-07-14")
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM team_engagement_snapshot WHERE team_id=1 AND week_start='2026-07-14'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["roster_count"] == 2


def test_snapshot_upsert_updates_existing():
    generate_snapshot(1, week_start="2026-07-14")
    _log(1, "2026-07-14", "everyday", 1)
    _log(1, "2026-07-14", "fuel_before", 1)
    _log(1, "2026-07-14", "top_up", 1)
    _log(1, "2026-07-14", "during", 1)
    _log(1, "2026-07-14", "recharge", 1)
    generate_snapshot(1, week_start="2026-07-14")
    conn = get_conn()
    row = conn.execute(
        "SELECT players_above_threshold FROM team_engagement_snapshot "
        "WHERE team_id=1 AND week_start='2026-07-14'"
    ).fetchone()
    conn.close()
    assert row["players_above_threshold"] == 1


def test_generate_all_snapshots_no_error():
    generate_all_snapshots()


def test_unknown_team_returns_not_found():
    result = generate_snapshot(9999, week_start="2026-07-21")
    assert result["status"] == "team_not_found"
