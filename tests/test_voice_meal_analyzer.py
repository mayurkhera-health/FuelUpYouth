"""Tests for voice meal analyzer agent (STT transcript → LLM → FDC)."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services import voice_meal_analyzer


def test_unique_foods_deduplicates():
    foods = [
        {"name": "Chicken", "estimated_portion_g": 100},
        {"name": "chicken", "estimated_portion_g": 120},
        {"name": "Rice", "estimated_portion_g": 150},
    ]
    result = voice_meal_analyzer._unique_foods(foods)
    assert len(result) == 2
    assert result[0]["name"] == "Chicken"
    assert result[1]["name"] == "Rice"


def test_analyze_voice_rejects_empty_transcription():
    with pytest.raises(ValueError, match="No speech transcription"):
        voice_meal_analyzer.analyze_voice("  ")


@patch("api.services.voice_meal_analyzer.detect_foods_from_text")
@patch("api.services.voice_meal_analyzer.lookup_food_nutrition")
def test_analyze_voice_full_pipeline(mock_lookup, mock_detect):
    mock_detect.return_value = [
        {"name": "grilled chicken breast", "estimated_portion_g": 120},
        {"name": "brown rice", "estimated_portion_g": 150},
    ]
    mock_lookup.side_effect = [
        {
            "name": "grilled chicken breast",
            "estimated_portion_g": 120,
            "calories": 198,
            "protein_g": 37.2,
            "carbs_g": 0,
            "fat_g": 4.3,
            "fdc_id": 171077,
            "fdc_description": "Chicken, breast, grilled",
        },
        {
            "name": "brown rice",
            "estimated_portion_g": 150,
            "calories": 185,
            "protein_g": 4.1,
            "carbs_g": 38.4,
            "fat_g": 1.5,
            "fdc_id": 168878,
            "fdc_description": "Rice, brown, cooked",
        },
    ]

    result = voice_meal_analyzer.analyze_voice("chicken and rice for lunch")

    assert result["transcription"] == "chicken and rice for lunch"
    assert len(result["foods"]) == 2
    assert result["totals"]["calories"] == 383
    assert "grilled chicken breast" in result["description"]
    mock_detect.assert_called_once_with("chicken and rice for lunch")


@patch("api.services.voice_meal_analyzer.detect_foods_from_text")
def test_analyze_voice_no_foods_detected(mock_detect):
    mock_detect.return_value = []
    with pytest.raises(ValueError, match="No foods detected"):
        voice_meal_analyzer.analyze_voice("hello world")


@patch("api.services.voice_meal_analyzer.converse_text")
def test_detect_foods_from_text_parses_llm_json(mock_converse):
    mock_converse.return_value = json.dumps({
        "foods": [
            {"name": "scrambled eggs", "estimated_portion_g": 100},
            {"name": "toast", "estimated_portion_g": 30},
        ]
    })

    foods = voice_meal_analyzer.detect_foods_from_text("two eggs and toast")
    assert len(foods) == 2
    assert foods[0]["name"] == "scrambled eggs"
    assert foods[0]["estimated_portion_g"] == 100


def test_detect_foods_from_text_empty_returns_empty():
    assert voice_meal_analyzer.detect_foods_from_text("") == []
    assert voice_meal_analyzer.detect_foods_from_text("   ") == []
