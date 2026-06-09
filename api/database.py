import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "fuelup.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
