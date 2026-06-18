from fastapi import APIRouter, HTTPException
from api.database import get_conn

router = APIRouter()


@router.get("")
def get_report_config():
    """Return all tunable thresholds from report_config table."""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT key, value, description, updated_at FROM report_config ORDER BY key"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.put("")
def update_report_config(body: dict):
    """
    Update one or more report_config thresholds.
    Body: { key: new_value, ... }
    Only keys that already exist in the table are updated — unknown keys are ignored.
    """
    if not body:
        raise HTTPException(400, "Request body must contain at least one key-value pair")

    conn = get_conn()
    try:
        valid_keys = {
            r["key"]
            for r in conn.execute("SELECT key FROM report_config").fetchall()
        }
        updated = []
        for key, value in body.items():
            if key not in valid_keys:
                continue
            try:
                float_val = float(value)
            except (TypeError, ValueError):
                raise HTTPException(400, f"Value for '{key}' must be numeric")
            conn.execute(
                "UPDATE report_config SET value = ?, updated_at = datetime('now') WHERE key = ?",
                (float_val, key),
            )
            updated.append(key)
        conn.commit()
        rows = conn.execute(
            "SELECT key, value, description, updated_at FROM report_config ORDER BY key"
        ).fetchall()
        return {"updated": updated, "config": [dict(r) for r in rows]}
    finally:
        conn.close()
