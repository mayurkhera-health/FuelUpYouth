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
        conn = sqlite3.connect(raw, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL mode: readers never block writers, writers never block readers.
    # Without this, a single write lock from a background job blocks all
    # concurrent reads (FastAPI threadpool) → "database is locked" 500s on Today.
    conn.execute("PRAGMA journal_mode=WAL")
    # Retry for up to 10 s on lock contention instead of failing immediately.
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_read_conn():
    """Read-only SQLite connection for TeamCoach request handlers.
    Uses ?mode=ro URI flag on file DBs and a 3-second busy timeout.
    Never call conn.commit() on this connection — writes raise OperationalError.
    """
    raw = os.getenv("DB_PATH", _DEFAULT_DB)
    if raw == ":memory:":
        conn = sqlite3.connect("file::memory:?cache=shared", uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(f"file:{raw}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=3000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
