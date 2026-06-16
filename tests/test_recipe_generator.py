"""Tests for recipe generator agent (FDC → LLM composition)."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services import recipe_generator


@patch("api.services.recipe_generator.gather_ingredients")
@patch("api.services.recipe_generator.converse_text")
def test_generate_recipe_full_pipeline(mock_converse, mock_gather):
    mock_gather.return_value = [
        {
            "fdcId": 173944,
            "name": "Bananas, raw",
            "calories": 89,
            "protein_g": 1.1,
            "carbs_g": 22.8,
            "fat_g": 0.3,
            "score": 10,
        },
        {
            "fdcId": 173904,
            "name": "Oats, rolled, dry",
            "calories": 379,
            "protein_g": 13.2,
            "carbs_g": 67.7,
            "fat_g": 6.5,
            "score": 8,
        },
    ]
    mock_converse.return_value = json.dumps({
        "name": "Quick Halftime Banana Bites",
        "category": "halftime",
        "calories": 220,
        "protein_g": 4,
        "carbs_g": 45,
        "fat_g": 2,
        "ingredients": ["1 medium banana", "2 tbsp honey"],
        "preparation_notes": "Slice and serve.",
        "tags": ["halftime", "quick"],
    })

    result = recipe_generator.generate_recipe(category="halftime")

    assert result["recipe"]["name"] == "Quick Halftime Banana Bites"
    assert result["recipe"]["calories"] == 220
    assert len(result["recipe"]["ingredients"]) == 2
    assert len(result["source_ingredients"]) == 2
    assert "Bananas, raw" in result["source_ingredients"]
    mock_gather.assert_called_once()
    mock_converse.assert_called_once()


@patch("api.services.recipe_generator.gather_ingredients")
def test_generate_recipe_unknown_category_raises(mock_gather):
    mock_gather.side_effect = ValueError('Unknown category "invalid"')
    with pytest.raises(ValueError, match="Unknown category"):
        recipe_generator.generate_recipe(category="invalid")


def test_resolve_category_halftime():
    from api.services.recipe_categories import resolve_category

    profile = resolve_category("halftime")
    assert profile["key"] == "halftime"
    assert profile["fdc_search_queries"]
    assert profile["target_calories"]["min"] > 0
