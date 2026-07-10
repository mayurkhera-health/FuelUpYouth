"""Validation tests for intensity and source on event models."""

import pytest
from pydantic import ValidationError

from api.models import EventCreate, EventUpdate


def test_intensity_optional_defaults_none():
    e = EventCreate(athlete_id=1, event_name="Game", event_type="game", event_date="2026-06-21")
    assert e.intensity is None


def test_intensity_accepted_and_lowercased():
    e = EventCreate(athlete_id=1, event_name="Game", event_type="game",
                    event_date="2026-06-21", intensity="High")
    assert e.intensity == "high"


def test_invalid_intensity_rejected():
    with pytest.raises(ValidationError):
        EventCreate(athlete_id=1, event_name="Game", event_type="game",
                    event_date="2026-06-21", intensity="extreme")


def test_update_intensity_optional():
    u = EventUpdate(intensity="medium")
    assert u.intensity == "medium"
    u2 = EventUpdate()
    assert u2.intensity is None


# ── source field ──────────────────────────────────────────────────────────────

def test_source_defaults_to_manual():
    """A new event POSTed without a source field must report source='manual'."""
    e = EventCreate(athlete_id=1, event_name="Practice", event_type="practice",
                    event_date="2026-07-10")
    assert e.source == "manual"


def test_source_explicit_manual_accepted():
    """Passing source='manual' explicitly is fine."""
    e = EventCreate(athlete_id=1, event_name="Practice", event_type="practice",
                    event_date="2026-07-10", source="manual")
    assert e.source == "manual"


def test_source_spoofed_value_rejected():
    """Passing source='byga' (or any non-manual value) must be rejected with 422."""
    with pytest.raises(ValidationError):
        EventCreate(athlete_id=1, event_name="Practice", event_type="practice",
                    event_date="2026-07-10", source="byga")
