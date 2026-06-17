import os
import sqlite3
from pathlib import Path

_DEFAULT_DB = str(Path(__file__).resolve().parent.parent / "fuelup.db")

# Kept for backwards compatibility — callers that imported DB_PATH directly
# still work; runtime resolution happens inside get_conn().
DB_PATH = Path(os.getenv("DB_PATH", _DEFAULT_DB))


def get_conn():
    raw = os.getenv("DB_PATH", _DEFAULT_DB)
    if raw == ":memory:":
        # Use a named shared-cache URI so every get_conn() call in the same
        # process sees the same in-memory database (important for tests).
        conn = sqlite3.connect(
            "file::memory:?cache=shared", uri=True, check_same_thread=False
        )
    else:
        conn = sqlite3.connect(raw)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
