import sqlite3
import pytest
import json
from pathlib import Path
import sys, os
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = Path(__file__).parent.parent / "fuelup.db"

def test_knowledge_tables_exist():
    """DB must have knowledge_items and knowledge_chunks tables."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "knowledge_items" in tables
    assert "knowledge_chunks" in tables

def test_knowledge_items_schema():
    """knowledge_items must have required columns."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cols = {r["name"] for r in conn.execute(
        "PRAGMA table_info(knowledge_items)"
    ).fetchall()}
    conn.close()
    required = {"id", "slug", "title", "category", "source", "source_urls",
                "last_reviewed_date", "applicable_age_range", "tags",
                "review_status", "version", "file_path", "ingested_at"}
    assert required.issubset(cols)

def test_knowledge_chunks_schema():
    """knowledge_chunks must have required columns."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cols = {r["name"] for r in conn.execute(
        "PRAGMA table_info(knowledge_chunks)"
    ).fetchall()}
    conn.close()
    required = {"id", "item_id", "chunk_index", "heading", "content", "created_at"}
    assert required.issubset(cols)


def _get_conn():
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def test_ingest_creates_knowledge_item():
    """Ingesting an approved file creates a knowledge_items row."""
    from api.services.knowledge.ingest import ingest_file
    iron_path = Path(__file__).parent.parent / "knowledge" / "iron_magnesium.md"
    ingest_file(str(iron_path))
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM knowledge_items WHERE slug = 'iron_magnesium'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["title"] == "Iron and Magnesium Requirements for Youth Athletes"
    assert row["review_status"] == "approved"

def test_ingest_creates_chunks():
    """Ingesting a file creates at least 3 chunks in knowledge_chunks."""
    conn = _get_conn()
    item = conn.execute(
        "SELECT id FROM knowledge_items WHERE slug = 'iron_magnesium'"
    ).fetchone()
    if not item:
        from api.services.knowledge.ingest import ingest_file
        iron_path = Path(__file__).parent.parent / "knowledge" / "iron_magnesium.md"
        ingest_file(str(iron_path))
        conn = _get_conn()
        item = conn.execute(
            "SELECT id FROM knowledge_items WHERE slug = 'iron_magnesium'"
        ).fetchone()
    chunks = conn.execute(
        "SELECT * FROM knowledge_chunks WHERE item_id = ?", (item["id"],)
    ).fetchall()
    conn.close()
    assert len(chunks) >= 3

def test_draft_file_not_ingested(tmp_path):
    """A file with review_status: draft must not be ingested."""
    draft = tmp_path / "draft_test.md"
    draft.write_text("""---
title: "Draft Test"
category: "test"
source: "test"
source_urls: []
last_reviewed_date: "2026-06-10"
applicable_age_range: "9-17"
tags: ["test"]
review_status: "draft"
version: 1
---

## Test Content

This should never be ingested.
""")
    from api.services.knowledge.ingest import ingest_file
    result = ingest_file(str(draft))
    assert result["status"] == "skipped"
    assert "draft" in result["reason"]


def test_retrieval_finds_iron_content():
    """Query about iron needs should return chunks from iron_magnesium.md."""
    from api.services.knowledge.ingest import ingest_file
    iron_path = Path(__file__).parent.parent / "knowledge" / "iron_magnesium.md"
    ingest_file(str(iron_path))

    from api.services.knowledge.retrieval import retrieve
    results = retrieve("how much iron does a teenage girl need per day")
    assert len(results) > 0
    titles = [r.title for r in results]
    assert any("Iron" in t or "Magnesium" in t for t in titles)

def test_retrieval_returns_empty_for_unknown_domain():
    """Out-of-domain query should return results all below threshold."""
    from api.services.knowledge.retrieval import retrieve
    results = retrieve("what is the latest iPhone model price")
    for r in results:
        assert r.score < 0.05, f"Unexpected high score {r.score} for out-of-domain query"

def test_retrieval_respects_approved_only():
    """Only approved chunks are returned."""
    from api.services.knowledge.retrieval import retrieve
    results = retrieve("test draft content should never appear")
    for r in results:
        assert r.review_status == "approved"
