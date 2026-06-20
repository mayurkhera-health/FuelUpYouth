"""Tests for recipe generator (agent picks from recipe library)."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services import recipe_generator


@patch("api.services.recipe_generator.converse_text")
def test_generate_recipe_agent_picks_from_library(mock_converse):
    mock_converse.return_value = json.dumps({"recipe_ids": ["R011"]})

    result = recipe_generator.generate_recipe(
        category="halftime",
        question="I want something with a banana at halftime",
    )

    assert result["ingredient_source"] == "recipe_library"
    assert result["recipe"]["name"] == "Banana + Natural Sports Drink"
    assert result["recipe"]["category"] == "halftime"
    assert len(result["recipe"]["ingredients"]) >= 1
    mock_converse.assert_called_once()
    prompt = mock_converse.call_args.kwargs["user"]
    assert "AVAILABLE RECIPES" in prompt
    assert "R010" in prompt
    assert "R011" in prompt
    assert "banana" in prompt.lower()


@patch("api.services.recipe_generator.converse_text")
def test_generate_recipe_only_sends_allergen_safe_recipes(mock_converse):
    mock_converse.return_value = json.dumps({"recipe_id": "R010"})

    recipe_generator.generate_recipe(category="halftime", allergies=["peanuts"])

    prompt = mock_converse.call_args.kwargs["user"]
    assert "R006" not in prompt


@patch("api.services.recipe_generator.converse_text")
def test_generate_recipe_vegan_dietary_filter(mock_converse):
    mock_converse.return_value = json.dumps({"recipe_id": "R010"})

    result = recipe_generator.generate_recipe(
        category="halftime",
        dietary_restrictions=["vegan"],
    )

    assert "vegan" in result["recipe"]["tags"]
    prompt = mock_converse.call_args.kwargs["user"]
    assert "R007" not in prompt


@patch("api.services.recipe_generator.converse_text")
def test_generate_recipe_falls_back_on_invalid_agent_id(mock_converse):
    mock_converse.return_value = json.dumps({"recipe_id": "R999"})

    result = recipe_generator.generate_recipe(category="halftime")

    assert result["recipe"]["name"] in {
        "Orange Slices + Water",
        "Banana + Natural Sports Drink",
        "Medjool Dates + Water",
    }


def test_generate_recipe_unknown_category_raises():
    with pytest.raises(ValueError, match="Unknown category"):
        recipe_generator.generate_recipe(category="invalid")


def test_generate_recipe_no_match_raises():
    from api.services import recipe_db

    with patch.object(recipe_db, "get_valid_recipes", return_value=[]):
        with pytest.raises(ValueError, match="No recipe found"):
            recipe_generator.generate_recipe(category="halftime")


def test_get_valid_recipes_returns_halftime_options():
    from api.services.recipe_db import get_valid_recipes

    recipes = get_valid_recipes("halftime")
    assert len(recipes) == 3
    assert all(r["category"] == "halftime" for r in recipes)


def test_resolve_category_halftime():
    from api.services.recipe_categories import resolve_category

    profile = resolve_category("halftime")
    assert profile["key"] == "halftime"
    assert profile["target_calories"]["min"] > 0
