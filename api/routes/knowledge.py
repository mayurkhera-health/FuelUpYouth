from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import json
import os

from api.database import get_conn
from api.services.knowledge.ingest import ingest_file, ingest_all
from api.services.knowledge.answer import answer_with_knowledge

router = APIRouter()

_ADMIN_KEY = os.getenv("KNOWLEDGE_ADMIN_KEY", "fuelup-admin")


def _require_admin(x_admin_key: Optional[str] = Header(None)):
    if x_admin_key != _ADMIN_KEY:
        raise HTTPException(403, "Admin key required. Pass X-Admin-Key header.")


class AskRequest(BaseModel):
    question: str
    athlete_id: int


class StatusUpdate(BaseModel):
    review_status: str


@router.get("/")
def list_knowledge_items(x_admin_key: Optional[str] = Header(None)):
    _require_admin(x_admin_key)
    conn = get_conn()
    try:
        rows = conn.execute(
            """SELECT ki.slug, ki.title, ki.category, ki.review_status, ki.version,
                      ki.last_reviewed_date, ki.source, ki.ingested_at,
                      COUNT(kc.id) as chunk_count
               FROM knowledge_items ki
               LEFT JOIN knowledge_chunks kc ON kc.item_id = ki.id
               GROUP BY ki.id ORDER BY ki.review_status, ki.category, ki.slug"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.post("/ingest")
def trigger_ingest(file_path: Optional[str] = None,
                   x_admin_key: Optional[str] = Header(None)):
    _require_admin(x_admin_key)
    if file_path:
        return ingest_file(file_path)
    return ingest_all()


@router.get("/{slug}")
def get_knowledge_item(slug: str, x_admin_key: Optional[str] = Header(None)):
    _require_admin(x_admin_key)
    conn = get_conn()
    try:
        item = conn.execute(
            "SELECT * FROM knowledge_items WHERE slug = ?", (slug,)
        ).fetchone()
        if not item:
            raise HTTPException(404, f"Knowledge item '{slug}' not found.")
        chunks = conn.execute(
            "SELECT chunk_index, heading, content FROM knowledge_chunks WHERE item_id = ? ORDER BY chunk_index",
            (item["id"],),
        ).fetchall()
        return {
            **dict(item),
            "source_urls": json.loads(item["source_urls"] or "[]"),
            "tags": json.loads(item["tags"] or "[]"),
            "chunks": [dict(c) for c in chunks],
        }
    finally:
        conn.close()


@router.patch("/{slug}/status")
def update_status(slug: str, body: StatusUpdate,
                  x_admin_key: Optional[str] = Header(None)):
    _require_admin(x_admin_key)
    allowed = {"draft", "approved", "archived"}
    if body.review_status not in allowed:
        raise HTTPException(400, f"review_status must be one of: {allowed}")
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM knowledge_items WHERE slug = ?", (slug,)
        ).fetchone()
        if not row:
            raise HTTPException(404, f"Knowledge item '{slug}' not found.")
        conn.execute(
            "UPDATE knowledge_items SET review_status = ? WHERE slug = ?",
            (body.review_status, slug),
        )
        conn.commit()
        return {"slug": slug, "review_status": body.review_status}
    finally:
        conn.close()


@router.delete("/{slug}")
def archive_item(slug: str, x_admin_key: Optional[str] = Header(None)):
    _require_admin(x_admin_key)
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM knowledge_items WHERE slug = ?", (slug,)
        ).fetchone()
        if not row:
            raise HTTPException(404, f"Knowledge item '{slug}' not found.")
        conn.execute(
            "UPDATE knowledge_items SET review_status = 'archived' WHERE slug = ?",
            (slug,),
        )
        conn.commit()
        return {"slug": slug, "review_status": "archived", "message": "Item archived (not deleted)."}
    finally:
        conn.close()


@router.post("/ask")
def ask_knowledge(body: AskRequest):
    """Public endpoint — athletes/parents ask questions."""
    conn = get_conn()
    try:
        athlete = conn.execute(
            "SELECT * FROM athletes WHERE id = ?", (body.athlete_id,)
        ).fetchone()
        if not athlete:
            raise HTTPException(404, "Athlete not found.")
        athlete_dict = dict(athlete)
    finally:
        conn.close()
    return answer_with_knowledge(body.question, athlete_dict)
