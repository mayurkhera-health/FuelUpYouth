import os
import sqlite3
from pathlib import Path

_DEFAULT_DB = str(Path(__file__).resolve().parent.parent / "fuelup.db")

# Kept for backwards compatibility — callers that imported DB_PATH directly
# still work; runtime resolution happens inside get_conn().
DB_PATH = Path(os.getenv("DB_PATH", _DEFAULT_DB))

# Set by tests/conftest.py per-module to a unique named in-memory URI so each
# test module gets its own isolated SQLite database.  None → shared-cache
# fallback (production behaviour when DB_PATH=:memory: in unit tests without
# the conftest fixture).
_test_db_uri: str | None = None


def get_conn():
    raw = os.getenv("DB_PATH", _DEFAULT_DB)
    if raw == ":memory:":
        uri = _test_db_uri or "file::memory:?cache=shared"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(raw)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
