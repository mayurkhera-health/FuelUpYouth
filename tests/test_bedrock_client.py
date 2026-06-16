"""Tests for LLM JSON parsing helpers."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.bedrock_client import parse_json_from_llm, _sanitize_json_string_literals


def test_sanitize_json_string_literals_escapes_newlines():
    broken = '{\n  "preparation_notes": "Step one\nStep two"\n}'
    fixed = _sanitize_json_string_literals(broken)
    parsed = json.loads(fixed)
    assert parsed["preparation_notes"] == "Step one\nStep two"


def test_parse_json_from_llm_valid():
    assert parse_json_from_llm('{"name": "ok"}')["name"] == "ok"


def test_parse_json_from_llm_repairs_broken():
    broken = '{"name":"Banana Bites","preparation_notes":"Slice\nServe","tags":["quick"]}'
    result = parse_json_from_llm(broken)
    assert result["preparation_notes"] == "Slice\nServe"
