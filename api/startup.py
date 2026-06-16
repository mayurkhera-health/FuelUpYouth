"""
App startup: lightweight DB migrations + knowledge ingest.
Runs on every deploy so production stays in sync without manual fly ssh steps.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from api.database import DB_PATH, get_conn

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


def _ensure_knowledge_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS knowledge_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            source TEXT,
            source_urls TEXT,
            last_reviewed_date TEXT,
            organization TEXT,
            applicable_age_range TEXT,
            tags TEXT,
            review_status TEXT DEFAULT 'draft',
            version INTEGER DEFAULT 1,
            file_path TEXT NOT NULL,
            ingested_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER REFERENCES knowledge_items(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            heading TEXT,
            content TEXT NOT NULL,
            embedding TEXT,
            embedding_model TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_item
            ON knowledge_chunks(item_id);

        CREATE INDEX IF NOT EXISTS idx_knowledge_items_status
            ON knowledge_items(review_status);
        """
    )


def ensure_schema() -> None:
    """Apply idempotent schema fixes for existing production databases."""
    conn = get_conn()
    try:
        _ensure_knowledge_tables(conn)

        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(knowledge_items)").fetchall()
        }
        if cols and "organization" not in cols:
            conn.execute("ALTER TABLE knowledge_items ADD COLUMN organization TEXT")
            logger.info("Added knowledge_items.organization column")

        chunk_cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(knowledge_chunks)").fetchall()
        }
        if chunk_cols and "embedding" not in chunk_cols:
            conn.execute("ALTER TABLE knowledge_chunks ADD COLUMN embedding TEXT")
            logger.info("Added knowledge_chunks.embedding column")
        if chunk_cols and "embedding_model" not in chunk_cols:
            conn.execute("ALTER TABLE knowledge_chunks ADD COLUMN embedding_model TEXT")
            logger.info("Added knowledge_chunks.embedding_model column")

        conn.commit()
    finally:
        conn.close()


def ensure_knowledge_ingested(force: bool = False) -> None:
    """
    Ingest bundled knowledge/*.md into SQLite.
    Skips when approved chunks already exist unless force=True.
    """
    from api.services.knowledge.ingest import ingest_all

    if not KNOWLEDGE_DIR.is_dir():
        logger.warning("Knowledge directory missing: %s", KNOWLEDGE_DIR)
        return

    conn = get_conn()
    try:
        chunk_count = conn.execute(
            """SELECT COUNT(*) FROM knowledge_chunks kc
               JOIN knowledge_items ki ON kc.item_id = ki.id
               WHERE ki.review_status = 'approved'"""
        ).fetchone()[0]
    finally:
        conn.close()

    if chunk_count > 0 and not force:
        logger.info("Knowledge already ingested (%s approved chunks)", chunk_count)
        return

    results = ingest_all(str(KNOWLEDGE_DIR))
    ok = [r for r in results if r.get("status") == "ok"]
    skipped = [r for r in results if r.get("status") == "skipped"]
    errors = [r for r in results if r.get("status") == "error"]
    total_chunks = sum(r.get("chunks", 0) for r in ok)
    logger.info(
        "Knowledge ingest: %s files, %s chunks (%s skipped, %s errors)",
        len(ok),
        total_chunks,
        len(skipped),
        len(errors),
    )
    for err in errors:
        logger.error("Knowledge ingest error: %s", err)


def ensure_knowledge_embeddings() -> None:
    """Backfill Bedrock embeddings for ingested chunks missing vectors."""
    from api.services.knowledge.retrieval import backfill_missing_embeddings

    try:
        updated = backfill_missing_embeddings()
        if updated:
            logger.info("Backfilled embeddings for %s knowledge chunks", updated)
    except Exception:
        logger.exception("Knowledge embedding backfill failed")


def run_startup() -> None:
    """Called once when the API process starts."""
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    ensure_schema()
    ensure_knowledge_ingested()
    ensure_knowledge_embeddings()
