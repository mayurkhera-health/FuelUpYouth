"""Validation tests for intensity on event models."""

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
