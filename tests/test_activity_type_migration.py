import os
os.environ["DB_PATH"] = ":memory:"
import sqlite3
from api.services.db_migrations import _add_activity_type_to_events


def test_adds_activity_type_column_idempotently():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, event_type TEXT)")
    _add_activity_type_to_events(conn)            # first run adds it
    _add_activity_type_to_events(conn)            # second run is a no-op (idempotent)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
    assert "activity_type" in cols
    # default is NULL (untagged)
    conn.execute("INSERT INTO events (event_type) VALUES ('practice')")
    row = conn.execute("SELECT activity_type FROM events").fetchone()
    assert row[0] is None
