"""
Admin Module — auth + family-centric Users management.

Every route except /login is guarded by the require_admin dependency (applied on
the router via dependencies=[...] in main.py is NOT possible here because /login
must stay open, so guards are applied per-route below).

Delete strategy: HARD delete. There is no is_deleted column anywhere in the
schema and ~20 tables reference athlete_id/parent_id, so a soft-delete flag would
require filtering every user-facing query app-wide. Instead we hard-delete every
child row across all referencing tables inside a single transaction, after
showing the operator an accurate cascade preview. Missing tables (schema drift
across environments, e.g. account_athlete only exists post phase-0 migration) are
skipped defensively via _table_exists.
"""

import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from api.database import get_conn
from api.services import admin_auth
from api.services.admin_auth import require_admin, write_audit

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Tables holding rows keyed by a single athlete_id column. Deleted when an
# athlete (or its parent) is removed. Order doesn't matter (no enforced FKs
# between them) — all are deleted before the athlete row itself.
ATHLETE_CHILD_TABLES = [
    "events", "meal_logs", "meal_plans", "meal_plan_selections", "daily_targets",
    "water_logs", "push_subscriptions", "expo_push_tokens", "athlete_article_picks",
    "athlete_logins", "athlete_food_prefs", "notification_log", "window_logs",
    "confirmations", "streak_state", "pantry_list_items", "account_athlete",
    "feature_requests",
]

# Parent-level tables keyed directly by the parent's id (child athletes are
# cascaded separately). account_athlete uses account_id = the parent account id.
PARENT_CHILD_TABLES = [
    ("otp_codes", "parent_id"),
    ("expo_push_tokens", "parent_id"),
    ("account_athlete", "account_id"),
]


# ── Request models (declared inline, matching auth.py / feedback.py) ─────────
class AdminLoginRequest(BaseModel):
    password: str


class ParentUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None


class AthleteUpdate(BaseModel):
    first_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    weight_lbs: Optional[float] = None
    height_ft: Optional[int] = None
    height_in: Optional[float] = None
    position: Optional[str] = None
    competition_level: Optional[str] = None
    date_of_birth: Optional[str] = None
    byga_ics_url: Optional[str] = None
    playmetrics_ics_url: Optional[str] = None


class DeleteConfirm(BaseModel):
    confirm: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────────
def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _count(conn, table: str, where: str, params) -> int:
    if not _table_exists(conn, table):
        return 0
    row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()
    return row[0] if row else 0


def _athlete_ids(conn, parent_id: int) -> list[int]:
    rows = conn.execute("SELECT id FROM athletes WHERE parent_id = ?", (parent_id,)).fetchall()
    return [r[0] for r in rows]


# ── Cascade preview + delete ─────────────────────────────────────────────────
def _preview_athlete(conn, athlete_id: int) -> dict:
    counts = {}
    for table in ATHLETE_CHILD_TABLES:
        n = _count(conn, table, "athlete_id = ?", (athlete_id,))
        if n:
            counts[table] = n
    # shopping_list_items via list_id → shopping_lists.athlete_id
    if _table_exists(conn, "shopping_lists"):
        list_ids = [r[0] for r in conn.execute(
            "SELECT id FROM shopping_lists WHERE athlete_id = ?", (athlete_id,)).fetchall()]
        if list_ids and _table_exists(conn, "shopping_list_items"):
            q = ",".join("?" * len(list_ids))
            n = conn.execute(
                f"SELECT COUNT(*) FROM shopping_list_items WHERE list_id IN ({q})", list_ids
            ).fetchone()[0]
            if n:
                counts["shopping_list_items"] = n
        if list_ids:
            counts["shopping_lists"] = len(list_ids)
    return counts


def _delete_athlete(conn, athlete_id: int) -> None:
    """Delete every child row for one athlete, then the athlete. Caller owns the
    transaction/commit."""
    if _table_exists(conn, "shopping_lists"):
        list_ids = [r[0] for r in conn.execute(
            "SELECT id FROM shopping_lists WHERE athlete_id = ?", (athlete_id,)).fetchall()]
        if list_ids and _table_exists(conn, "shopping_list_items"):
            q = ",".join("?" * len(list_ids))
            conn.execute(f"DELETE FROM shopping_list_items WHERE list_id IN ({q})", list_ids)
        conn.execute("DELETE FROM shopping_lists WHERE athlete_id = ?", (athlete_id,))
    for table in ATHLETE_CHILD_TABLES:
        if _table_exists(conn, table):
            conn.execute(f"DELETE FROM {table} WHERE athlete_id = ?", (athlete_id,))
    conn.execute("DELETE FROM athletes WHERE id = ?", (athlete_id,))


def _merge_counts(dst: dict, src: dict) -> None:
    for k, v in src.items():
        dst[k] = dst.get(k, 0) + v


# ── Auth ─────────────────────────────────────────────────────────────────────
@router.post("/login")
def admin_login(data: AdminLoginRequest, request: Request):
    ip = _client_ip(request)
    admin_auth.check_rate_limit(ip)
    if not admin_auth.password_configured():
        raise HTTPException(503, "Admin login is not configured.")
    if not admin_auth.verify_password(data.password):
        admin_auth.record_failed_login(ip)
        raise HTTPException(401, "Incorrect password.")
    admin_auth.clear_failed_logins(ip)
    return {"token": admin_auth.mint_token(), "expires_in": admin_auth.TOKEN_TTL_SECONDS}


# ── Users list ───────────────────────────────────────────────────────────────
@router.get("/users")
def list_families(
    _: bool = Depends(require_admin),
    page: int = 1,
    limit: int = 25,
    search: str = "",
    calendar: str = "any",       # any | byga | playmetrics | none
    has_athletes: str = "any",   # any | yes | no
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort: str = "newest",        # newest | name | last_active
):
    page = max(1, page)
    limit = max(1, min(100, limit))
    offset = (page - 1) * limit
    stale_cutoff = (datetime.utcnow() - timedelta(hours=48)).isoformat()

    where = []
    params: list = []
    if search:
        like = f"%{search.strip()}%"
        where.append(
            "(p.full_name LIKE ? OR p.email LIKE ? OR EXISTS("
            "SELECT 1 FROM athletes a2 WHERE a2.parent_id = p.id AND a2.first_name LIKE ?))"
        )
        params += [like, like, like]
    if calendar == "byga":
        where.append("EXISTS(SELECT 1 FROM athletes a3 WHERE a3.parent_id = p.id AND a3.byga_ics_url IS NOT NULL)")
    elif calendar == "playmetrics":
        where.append("EXISTS(SELECT 1 FROM athletes a3 WHERE a3.parent_id = p.id AND a3.playmetrics_ics_url IS NOT NULL)")
    elif calendar == "none":
        where.append("NOT EXISTS(SELECT 1 FROM athletes a3 WHERE a3.parent_id = p.id AND "
                     "(a3.byga_ics_url IS NOT NULL OR a3.playmetrics_ics_url IS NOT NULL))")
    if date_from:
        where.append("p.created_at >= ?")
        params.append(date_from)
    if date_to:
        where.append("p.created_at <= ?")
        params.append(date_to)

    having = ""
    if has_athletes == "yes":
        having = "HAVING athlete_count > 0"
    elif has_athletes == "no":
        having = "HAVING athlete_count = 0"

    order = {
        "name": "p.full_name COLLATE NOCASE ASC",
        "last_active": "last_active DESC",
        "newest": "p.created_at DESC",
    }.get(sort, "p.created_at DESC")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    base = f"""
        SELECT p.id, p.full_name, p.email, p.created_at,
               COUNT(a.id) AS athlete_count,
               SUM(CASE WHEN a.byga_ics_url IS NOT NULL OR a.playmetrics_ics_url IS NOT NULL
                        THEN 1 ELSE 0 END) AS connected_count,
               SUM(CASE WHEN a.byga_ics_url IS NOT NULL THEN 1 ELSE 0 END) AS byga_count,
               SUM(CASE WHEN a.playmetrics_ics_url IS NOT NULL THEN 1 ELSE 0 END) AS playmetrics_count,
               (SELECT COUNT(*) FROM events e JOIN athletes aa ON aa.id = e.athlete_id
                 WHERE aa.parent_id = p.id AND e.synced_at IS NOT NULL AND e.synced_at > ?) AS recent_synced_count,
               (SELECT MAX(ts) FROM (
                    SELECT MAX(ml.logged_at) AS ts FROM meal_logs ml JOIN athletes aa ON aa.id = ml.athlete_id WHERE aa.parent_id = p.id
                    UNION ALL
                    SELECT MAX(wl.created_at) FROM window_logs wl JOIN athletes aa ON aa.id = wl.athlete_id WHERE aa.parent_id = p.id
                    UNION ALL
                    SELECT MAX(w.updated_at) FROM water_logs w JOIN athletes aa ON aa.id = w.athlete_id WHERE aa.parent_id = p.id
               )) AS last_active
        FROM parents p
        LEFT JOIN athletes a ON a.parent_id = p.id
        {where_sql}
        GROUP BY p.id
        {having}
    """
    conn = get_conn()
    try:
        # recent_synced_count subquery param comes first in the SELECT param order
        select_params = [stale_cutoff] + params
        total = conn.execute(
            f"SELECT COUNT(*) FROM ({base})", select_params
        ).fetchone()[0]
        rows = conn.execute(
            f"{base} ORDER BY {order} LIMIT ? OFFSET ?",
            select_params + [limit, offset],
        ).fetchall()

        cutoff_3d = (datetime.utcnow() - timedelta(days=3)).isoformat()
        items = []
        for r in rows:
            d = dict(r)
            athlete_count = d["athlete_count"] or 0
            connected = d["connected_count"] or 0
            # Nested athlete summaries for the row (name, sport/position, age)
            aths = conn.execute(
                "SELECT id, first_name, age, position, competition_level, "
                "byga_ics_url, playmetrics_ics_url FROM athletes WHERE parent_id = ? ORDER BY id",
                (d["id"],),
            ).fetchall()
            chips = []
            if athlete_count == 0:
                chips.append("no_athletes")
            else:
                if connected == 0 and d["created_at"] and d["created_at"] < cutoff_3d:
                    chips.append("never_connected")
                if connected > 0 and (d["recent_synced_count"] or 0) == 0:
                    chips.append("sync_stale")
            items.append({
                "id": d["id"],
                "full_name": d["full_name"],
                "email": d["email"],
                "created_at": d["created_at"],
                "last_active": d["last_active"],
                "athlete_count": athlete_count,
                "byga_count": d["byga_count"] or 0,
                "playmetrics_count": d["playmetrics_count"] or 0,
                "athletes": [
                    {
                        "id": a["id"], "first_name": a["first_name"], "age": a["age"],
                        "position": a["position"], "competition_level": a["competition_level"],
                        "calendar": ("byga" if a["byga_ics_url"] else
                                     "playmetrics" if a["playmetrics_ics_url"] else "none"),
                    } for a in aths
                ],
                "chips": chips,
            })
        return {"items": items, "total": total, "page": page, "limit": limit}
    finally:
        conn.close()


# ── Family detail ────────────────────────────────────────────────────────────
@router.get("/users/{parent_id}")
def family_detail(parent_id: int, _: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        prow = conn.execute("SELECT * FROM parents WHERE id = ?", (parent_id,)).fetchone()
        if not prow:
            raise HTTPException(404, "Parent not found.")
        parent = dict(prow)

        athletes = []
        for a in conn.execute("SELECT * FROM athletes WHERE parent_id = ? ORDER BY id", (parent_id,)).fetchall():
            ad = dict(a)
            stats = conn.execute(
                "SELECT source, COUNT(*) AS n, "
                "SUM(CASE WHEN event_date >= date('now') THEN 1 ELSE 0 END) AS upcoming "
                "FROM events WHERE athlete_id = ? GROUP BY source",
                (ad["id"],),
            ).fetchall()
            by_source, total_events, upcoming_events = {}, 0, 0
            for s in stats:
                sd = dict(s)
                by_source[sd["source"] or "manual"] = sd["n"]
                total_events += sd["n"]
                upcoming_events += sd["upcoming"] or 0
            last_synced = conn.execute(
                "SELECT MAX(synced_at) FROM events WHERE athlete_id = ? AND synced_at IS NOT NULL",
                (ad["id"],),
            ).fetchone()[0]
            ad["event_stats"] = {
                "total": total_events, "upcoming": upcoming_events, "by_source": by_source,
            }
            ad["last_synced_at"] = last_synced
            athletes.append(ad)

        athlete_ids = [a["id"] for a in athletes]
        upcoming = []
        recent_ideas = []
        if athlete_ids:
            q = ",".join("?" * len(athlete_ids))
            upcoming = [dict(e) for e in conn.execute(
                f"SELECT * FROM events WHERE athlete_id IN ({q}) AND event_date >= date('now') "
                f"ORDER BY event_date, start_time LIMIT 5", athlete_ids
            ).fetchall()]
        # Feature ideas: match by any family athlete_id OR the parent's email.
        if _table_exists(conn, "feature_requests"):
            if athlete_ids:
                q = ",".join("?" * len(athlete_ids))
                recent_ideas = [dict(f) for f in conn.execute(
                    f"SELECT * FROM feature_requests WHERE athlete_id IN ({q}) OR lower(email) = lower(?) "
                    f"ORDER BY submitted_at DESC LIMIT 10", athlete_ids + [parent["email"]]
                ).fetchall()]
            else:
                recent_ideas = [dict(f) for f in conn.execute(
                    "SELECT * FROM feature_requests WHERE lower(email) = lower(?) "
                    "ORDER BY submitted_at DESC LIMIT 10", (parent["email"],)
                ).fetchall()]

        return {
            "parent": parent,
            "athletes": athletes,
            "activity": {
                "upcoming_events": upcoming,
                "feature_ideas": recent_ideas,
                # problem_reports has no parent/athlete column in the schema, so it
                # cannot be scoped to a family — shown only as a global count on the
                # analytics dashboard, not here.
            },
        }
    finally:
        conn.close()


# ── Edit parent ──────────────────────────────────────────────────────────────
@router.put("/parents/{parent_id}")
def update_parent(parent_id: int, data: ParentUpdate, _: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM parents WHERE id = ?", (parent_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Parent not found.")
        fields, values, changed = [], [], {}
        if data.full_name is not None:
            fields.append("full_name = ?"); values.append(data.full_name); changed["full_name"] = data.full_name
        if data.email is not None:
            email = data.email.strip().lower()
            if not _EMAIL_RE.match(email):
                raise HTTPException(400, "Invalid email format.")
            fields.append("email = ?"); values.append(email); changed["email"] = email
        if not fields:
            return dict(row)
        try:
            conn.execute(f"UPDATE parents SET {', '.join(fields)} WHERE id = ?", values + [parent_id])
            conn.commit()
        except Exception as e:
            if "UNIQUE" in str(e):
                raise HTTPException(409, "Another parent already uses that email.")
            raise HTTPException(500, str(e))
        write_audit("update_parent", "parent", parent_id, changed)
        return dict(conn.execute("SELECT * FROM parents WHERE id = ?", (parent_id,)).fetchone())
    finally:
        conn.close()


# ── Edit athlete ─────────────────────────────────────────────────────────────
@router.put("/athletes/{athlete_id}")
def update_athlete(athlete_id: int, data: AthleteUpdate, _: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        allowed = ["first_name", "age", "gender", "weight_lbs", "height_ft", "height_in",
                   "position", "competition_level", "date_of_birth",
                   "byga_ics_url", "playmetrics_ics_url"]
        fields, values, changed = [], [], {}
        payload = data.model_dump(exclude_unset=True)
        for key in allowed:
            if key in payload:
                fields.append(f"{key} = ?"); values.append(payload[key]); changed[key] = payload[key]
        if not fields:
            return dict(row)
        conn.execute(f"UPDATE athletes SET {', '.join(fields)} WHERE id = ?", values + [athlete_id])
        conn.commit()
        write_audit("update_athlete", "athlete", athlete_id, changed)
        return dict(conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone())
    finally:
        conn.close()


# ── Delete preview + delete: athlete ─────────────────────────────────────────
@router.get("/athletes/{athlete_id}/delete-preview")
def preview_delete_athlete(athlete_id: int, _: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        row = conn.execute("SELECT first_name FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        return {"athlete_id": athlete_id, "first_name": row[0], "counts": _preview_athlete(conn, athlete_id)}
    finally:
        conn.close()


@router.delete("/athletes/{athlete_id}")
def delete_athlete(athlete_id: int, _: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        row = conn.execute("SELECT first_name FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Athlete not found.")
        counts = _preview_athlete(conn, athlete_id)
        try:
            conn.execute("BEGIN")
            _delete_athlete(conn, athlete_id)
            write_audit("delete_athlete", "athlete", athlete_id,
                        {"first_name": row[0], "cascade": counts}, conn=conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(500, str(e))
        return {"deleted": True, "athlete_id": athlete_id, "cascade": counts}
    finally:
        conn.close()


# ── Delete preview + delete: parent (full family) ────────────────────────────
def _preview_parent(conn, parent_id: int) -> dict:
    athlete_ids = _athlete_ids(conn, parent_id)
    counts: dict = {"athletes": len(athlete_ids)}
    for aid in athlete_ids:
        _merge_counts(counts, _preview_athlete(conn, aid))
    for table, col in PARENT_CHILD_TABLES:
        n = _count(conn, table, f"{col} = ?", (parent_id,))
        if n:
            counts[f"{table}:{col}"] = counts.get(f"{table}:{col}", 0) + n
    return counts


@router.get("/parents/{parent_id}/delete-preview")
def preview_delete_parent(parent_id: int, _: bool = Depends(require_admin)):
    conn = get_conn()
    try:
        row = conn.execute("SELECT full_name FROM parents WHERE id = ?", (parent_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Parent not found.")
        return {"parent_id": parent_id, "full_name": row[0], "counts": _preview_parent(conn, parent_id)}
    finally:
        conn.close()


@router.delete("/parents/{parent_id}")
def delete_parent(parent_id: int, data: DeleteConfirm, _: bool = Depends(require_admin)):
    if (data.confirm or "").strip() != "DELETE":
        raise HTTPException(400, "Type DELETE to confirm parent deletion.")
    conn = get_conn()
    try:
        row = conn.execute("SELECT full_name FROM parents WHERE id = ?", (parent_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Parent not found.")
        counts = _preview_parent(conn, parent_id)
        try:
            conn.execute("BEGIN")
            for aid in _athlete_ids(conn, parent_id):
                _delete_athlete(conn, aid)
            for table, col in PARENT_CHILD_TABLES:
                if _table_exists(conn, table):
                    conn.execute(f"DELETE FROM {table} WHERE {col} = ?", (parent_id,))
            conn.execute("DELETE FROM parents WHERE id = ?", (parent_id,))
            write_audit("delete_parent", "parent", parent_id,
                        {"full_name": row[0], "cascade": counts}, conn=conn)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise HTTPException(500, str(e))
        return {"deleted": True, "parent_id": parent_id, "cascade": counts}
    finally:
        conn.close()
