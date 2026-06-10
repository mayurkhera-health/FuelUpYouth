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


def test_iron_rda_female_14():
    """Female age 14 iron RDA is 15mg per NIH."""
    from api.services.knowledge.calculations import iron_rda
    result = iron_rda(14, "female")
    assert result["value"] == 15
    assert result["unit"] == "mg/day"
    assert "NIH" in result["source"]

def test_iron_rda_male_14():
    """Male age 14 iron RDA is 11mg per NIH."""
    from api.services.knowledge.calculations import iron_rda
    result = iron_rda(14, "male")
    assert result["value"] == 11

def test_iron_rda_child_9():
    """Age 9 iron RDA is 8mg regardless of gender per NIH."""
    from api.services.knowledge.calculations import iron_rda
    assert iron_rda(9, "female")["value"] == 8
    assert iron_rda(9, "male")["value"] == 8

def test_calcium_rda_youth():
    """Ages 9-18 calcium RDA is 1300mg per NIH."""
    from api.services.knowledge.calculations import calcium_rda
    result = calcium_rda(14)
    assert result["value"] == 1300
    assert result["unit"] == "mg/day"

def test_protein_range_game_day():
    """120 lb athlete on game day: 1.6-1.8 g/kg = 87-98g."""
    from api.services.knowledge.calculations import protein_range
    result = protein_range(120, "game")
    assert result["min_g"] == 87
    assert result["max_g"] == 98
    assert result["unit"] == "g/day"

def test_hydration_needs_game():
    """120 lb athlete on game day without heat: 80-88 oz."""
    from api.services.knowledge.calculations import hydration_needs
    result = hydration_needs(120, "game", weather_hot=False)
    assert result["min_oz"] == 80
    assert result["max_oz"] == 88

def test_hydration_needs_hot_weather():
    """Hot weather adds 8-16 oz to baseline."""
    from api.services.knowledge.calculations import hydration_needs
    normal = hydration_needs(120, "rest", weather_hot=False)
    hot = hydration_needs(120, "rest", weather_hot=True)
    assert hot["min_oz"] == normal["min_oz"] + 8
    assert hot["max_oz"] == normal["max_oz"] + 16

def test_pre_training_meal_window():
    """Event at 18:00 → full meal by 15:30, snack by 17:00."""
    from api.services.knowledge.calculations import pre_training_meal_window
    result = pre_training_meal_window("18:00")
    assert result["full_meal_by"] == "15:30"
    assert result["snack_by"] == "17:00"

def test_post_training_recovery_window():
    """Event ends at 20:00 → window open 20:00, closes 20:30."""
    from api.services.knowledge.calculations import post_training_recovery_window
    result = post_training_recovery_window("20:00")
    assert result["window_opens"] == "20:00"
    assert result["window_closes"] == "20:30"


from unittest.mock import patch

def test_no_answer_when_empty_retrieval():
    """When no chunks found, return safe fallback string."""
    from api.services.knowledge.answer import answer_with_knowledge

    with patch("api.services.knowledge.answer.retrieve", return_value=[]):
        result = answer_with_knowledge(
            "what is the stock price of Apple",
            {"id": 1, "first_name": "Alex", "age": 14, "gender": "female",
             "weight_lbs": 120, "event_type": "rest"}
        )
    assert "don't have enough approved information" in result["answer"]
    assert result["citations"] == []

def test_citations_included_in_answer():
    """Answers from knowledge base must include at least one citation."""
    from api.services.knowledge.answer import answer_with_knowledge
    from api.services.knowledge.retrieval import KnowledgeChunk

    mock_chunk = KnowledgeChunk(
        chunk_id=1, item_id=1, slug="iron_magnesium",
        title="Iron and Magnesium Requirements",
        category="micronutrients",
        source="NIH Office of Dietary Supplements",
        source_urls=["https://ods.od.nih.gov/factsheets/Iron-HealthProfessional/"],
        applicable_age_range="9-17", tags=["iron"],
        review_status="approved", heading="Daily Iron Requirements",
        content="Female athletes age 14-18 need 15mg iron per day.",
        score=0.7,
    )

    with patch("api.services.knowledge.answer.retrieve", return_value=[mock_chunk]):
        with patch("api.services.knowledge.answer._call_claude",
                   return_value="Female athletes need 15mg iron. Source: Iron and Magnesium Requirements"):
            result = answer_with_knowledge(
                "how much iron does a girl need",
                {"id": 1, "first_name": "Alex", "age": 14, "gender": "female",
                 "weight_lbs": 120, "event_type": "rest"}
            )
    assert len(result["citations"]) >= 1
    assert result["citations"][0]["title"] == "Iron and Magnesium Requirements"

def test_safety_guardrail_in_system_prompt():
    """Claude system prompt must contain safety guardrail instructions."""
    from api.services.knowledge.answer import _build_system_prompt
    prompt = _build_system_prompt(chunks=[], calc_result=None)
    assert "medical" in prompt.lower()
    assert "professional" in prompt.lower()
    assert "eating" in prompt.lower()

def test_calculation_included_when_relevant():
    """Iron question for a known athlete should produce a non-None result."""
    from api.services.knowledge.answer import answer_with_knowledge
    from api.services.knowledge.retrieval import KnowledgeChunk

    mock_chunk = KnowledgeChunk(
        chunk_id=1, item_id=1, slug="iron_magnesium",
        title="Iron and Magnesium Requirements",
        category="micronutrients",
        source="NIH", source_urls=[],
        applicable_age_range="9-17", tags=["iron"],
        review_status="approved", heading="Iron RDA",
        content="Female athletes age 14-18 need 15mg iron per day.",
        score=0.6,
    )

    with patch("api.services.knowledge.answer.retrieve", return_value=[mock_chunk]):
        with patch("api.services.knowledge.answer._call_claude", return_value="15mg"):
            result = answer_with_knowledge(
                "how much iron does she need",
                {"id": 1, "first_name": "Maya", "age": 15, "gender": "female",
                 "weight_lbs": 115, "event_type": "rest"}
            )
    assert result["answer"] is not None
