"""
Admin System Health endpoints (all behind require_admin):
  GET  /api/admin/health            — all checks + overall status
  GET  /api/admin/health/incidents  — transition history, newest first
  POST /api/admin/health/run        — run the 15-min suite on demand (1/min floor)
"""

import time

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_conn
from api.services import health_service
from api.services.admin_auth import require_admin

router = APIRouter()

_RUN_FLOOR_SECONDS = 60
_last_run = {"t": 0.0}


@router.get("/health")
def health(_: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        return health_service.get_health_snapshot(conn)
    finally:
        conn.close()


@router.get("/health/incidents")
def incidents(limit: int = 50, _: bool = Depends(require_admin)):
    limit = max(1, min(200, limit))
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM health_incidents ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return {"items": [dict(r) for r in rows]}
    finally:
        conn.close()


@router.post("/health/run")
def run_now(_: bool = Depends(require_admin)):
    now = time.monotonic()
    if now - _last_run["t"] < _RUN_FLOOR_SECONDS:
        raise HTTPException(429, "Health check was just run — try again in a moment.")
    _last_run["t"] = now
    health_service.run_health_tick()
    conn = get_conn()
    try:
        return health_service.get_health_snapshot(conn)
    finally:
        conn.close()
