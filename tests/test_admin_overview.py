"""Plain-language /overview: aggregation, warning thresholds, health line,
report text, auth. Pure DB (no external calls)."""

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


def _wipe(conn):
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF")
    for (name,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
        conn.execute(f"DELETE FROM {name}")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")


def _add_family(conn, name, email, byga=None):
    pid = conn.execute("INSERT INTO parents (full_name, email, consent_timestamp, consent_confirmed) "
                       "VALUES (?, ?, 't', 1)", (name, email)).lastrowid
    conn.execute("INSERT INTO athletes (parent_id, first_name, age, gender, weight_lbs, height_ft, height_in, byga_ics_url) "
                 "VALUES (?, 'Kid', 12, 'M', 90, 5, 2, ?)", (pid, byga))
    conn.commit()
    return pid


@pytest.fixture
def ctx(monkeypatch):
    ka = get_conn()
    init_db()
    run_all()
    _wipe(ka)  # also clears the seeded health_checks → empty = "all healthy"
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setenv("ADMIN_SESSION_SECRET", "unit-test-signing-key")
    admin_auth._failed_logins.clear()
    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {c.post('/api/admin/login', json={'password': PASSWORD}).json()['token']}"})
        yield c, ka
    ka.close()


def _get(c):
    return c.get("/api/admin/overview").json()


def test_requires_token():
    with TestClient(app) as anon:
        assert anon.get("/api/admin/overview").status_code == 401


def test_families_zero_and_all_healthy(ctx):
    c, _ = ctx
    body = _get(c)
    assert body["health"]["status"] == "green"
    assert body["health"]["headline"] == "App is working normally"
    assert body["lines"][0]["text"] == "0 families using the app"


def test_active_users_warning_toggles(ctx):
    c, ka = ctx
    _add_family(ka, "A", "a@x.com")
    # no activity → ⚠️ on the active line
    fam_line = _get(c)["lines"][0]
    assert fam_line["warn"] is True
    assert fam_line["sub"] == "No athletes active in the last 7 days"
    # log activity today → warning clears
    aid = ka.execute("SELECT id FROM athletes LIMIT 1").fetchone()[0]
    ka.execute("INSERT INTO meal_logs (athlete_id, log_method) VALUES (?, 'text')", (aid,))
    ka.commit()
    fam_line2 = _get(c)["lines"][0]
    assert fam_line2["warn"] is False
    assert "1 athlete active" in fam_line2["sub"]


def test_calendar_warning_boundary(ctx):
    c, ka = ctx
    # 2 families, 1 connected → exactly 50% → NOT below 0.5 → no warning
    _add_family(ka, "A", "a@x.com", byga="http://x.ics")
    _add_family(ka, "B", "b@x.com")
    cal = _get(c)["lines"][1]
    assert cal["text"] == "1 of 2 families connected their team calendar"
    assert cal["warn"] is False
    # add a 3rd unconnected family → 1/3 = 33% → below 0.5 → warning
    _add_family(ka, "C", "c@x.com")
    cal2 = _get(c)["lines"][1]
    assert cal2["warn"] is True
    assert cal2["text"] == "1 of 3 families connected their team calendar"


def test_red_health_check_is_named_plainly(ctx):
    c, ka = ctx
    # The 9 checks are (re)seeded at app startup; flip one to red.
    ka.execute("UPDATE health_checks SET status='red', detail='92% used' WHERE check_name='disk_space'")
    ka.commit()
    h = _get(c)["health"]
    assert h["status"] == "red"
    assert h["headline"] == "Something needs attention"
    assert "storage space" in h["detail"].lower()  # plain name, not 'disk_space'
    assert "disk_space" not in h["detail"]


def test_report_body_is_paste_ready(ctx):
    c, ka = ctx
    _add_family(ka, "A", "a@x.com", byga="http://x.ics")  # connected
    _add_family(ka, "B", "b@x.com")                        # not connected
    ka.execute("INSERT INTO problem_reports (description) VALUES ('bug')")
    ka.execute("INSERT INTO feature_requests (suggestion) VALUES ('idea')")
    ka.commit()
    rb = _get(c)["report_body"]
    # No timestamp header (frontend adds local time); starts with the health line.
    assert rb.startswith("✅ App is working normally")
    assert "2 families using the app" in rb
    assert "⚠️ No athletes active in the last 7 days" in rb
    assert "1 of 2 families connected their team calendar" in rb  # 50% → no warning
    assert "No families have used a meal plan yet" in rb
    assert "1 problem report this week" in rb
    assert "1 new idea suggested this week" in rb
    # zero jargon
    for banned in ("HogQL", "PostHog", "DB", "endpoint", "sync adoption", "funnel"):
        assert banned not in rb
