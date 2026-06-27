import os
os.environ["DB_PATH"] = ":memory:"
from datetime import datetime
from api.services.day_layout import build_day_layout, day_layout_v2_enabled


def test_flag_helper_reads_env(monkeypatch):
    monkeypatch.setenv("DAY_LAYOUT_V2", "true")
    assert day_layout_v2_enabled() is True
    monkeypatch.delenv("DAY_LAYOUT_V2", raising=False)
    assert day_layout_v2_enabled() is False


def test_to_template_windows_shape():
    from api.services.day_layout import cards_to_template_windows
    ev = {"id": 1, "event_type": "practice", "activity_type": "practice",
          "event_date": "2026-06-27", "start_time": "15:00", "duration_hours": 1.0}
    res = build_day_layout([ev], {"id": 1, "weight_lbs": 120, "height_ft": 5,
                                  "height_in": 4, "gender": "boy", "age": 14},
                           now=datetime(2026, 6, 27, 6, 0))
    tw = cards_to_template_windows(res["cards"])
    assert tw and all({"key", "label", "category", "sort_time"} <= set(w) for w in tw)
    # event marker maps to a nudge-only (non-tappable) window
    ev_win = next(w for w in tw if w["category"] == "event")
    assert ev_win["is_nudge_only"] is True


# ── Flag-ON integration test: exercises the real build_today_view seam ─────────

import pytest

TARGET_DATE = "2026-06-27"


@pytest.fixture
def db_conn():
    """In-memory DB fixture: init schema + run migrations, yield connection."""
    from db.setup import init_db
    from api.services.db_migrations import run_all
    from api.database import get_conn
    keepalive = get_conn()
    init_db()
    run_all()
    yield keepalive
    keepalive.close()


_seed_counter = {"n": 0}


def _seed_athlete_and_event(conn):
    """Insert a parent + athlete + single afternoon practice for TARGET_DATE."""
    _seed_counter["n"] += 1
    email = f"dl_integration_{_seed_counter['n']}@example.com"
    conn.execute(
        "INSERT INTO parents (full_name, email, consent_timestamp, consent_confirmed) "
        "VALUES (?, ?, datetime('now'), 1)",
        ("Test Parent", email),
    )
    parent_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.execute(
        "INSERT INTO athletes (parent_id, first_name, age, gender, weight_lbs, height_ft, height_in) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (parent_id, "Tester", 14, "boy", 120, 5, 4),
    )
    athlete_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.execute(
        "INSERT INTO events (athlete_id, event_name, event_type, event_date, start_time, duration_hours) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (athlete_id, "Afternoon Practice", "practice", TARGET_DATE, "15:00", 1.0),
    )
    conn.commit()
    return athlete_id


def test_build_today_view_flag_on_macro_focus(monkeypatch, db_conn):
    """
    C1 regression: with DAY_LAYOUT_V2=true, at least one tappable window must
    have a macro_focus that isn't 'Fuel Window' (e.g. 'High Carbs' for fuel_before).
    """
    monkeypatch.setenv("DAY_LAYOUT_V2", "true")
    from api.services.today_service import build_today_view

    athlete_id = _seed_athlete_and_event(db_conn)
    result = build_today_view(athlete_id, db_conn, today=TARGET_DATE)

    windows = result["windows"]
    assert windows, "Expected at least one window"

    macro_focuses = [w.get("macro_focus") for w in windows]
    assert any(mf and mf != "Fuel Window" for mf in macro_focuses), (
        f"All macro_focus values are 'Fuel Window' — C1 fix did not take effect. "
        f"Got: {macro_focuses}"
    )


def test_build_today_view_flag_on_event_marker(monkeypatch, db_conn):
    """
    C2 regression: with DAY_LAYOUT_V2=true, the event marker card must appear
    in the merged windows list with window_type='event' and status='event'.
    """
    monkeypatch.setenv("DAY_LAYOUT_V2", "true")
    from api.services.today_service import build_today_view

    athlete_id = _seed_athlete_and_event(db_conn)
    result = build_today_view(athlete_id, db_conn, today=TARGET_DATE)

    windows = result["windows"]
    event_windows = [w for w in windows if w.get("window_type") == "event" or w.get("status") == "event"]
    assert event_windows, (
        f"No event-marker window found in windows list — C2 fix did not take effect. "
        f"window_types present: {[w.get('window_type') for w in windows]}"
    )
