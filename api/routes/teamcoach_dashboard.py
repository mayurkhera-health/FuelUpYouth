"""TeamCoach read-only dashboard API.

All handlers: coach bearer token required, team access scoped to coach.
Never exposes nutrition/macro/clinical data.
"""
from fastapi import APIRouter, Header
from api.routes.teamcoach_auth import require_coach
from api.services.teamcoach_service import (
    get_coach_teams, assert_coach_owns_team, get_roster, get_engagement
)

router = APIRouter()


@router.get("/")
def list_teams(authorization: str = Header(None)):
    payload = require_coach(authorization)
    return get_coach_teams(payload["coach_id"])


@router.get("/{team_id}/roster")
def team_roster(team_id: int, authorization: str = Header(None)):
    payload = require_coach(authorization)
    assert_coach_owns_team(payload["coach_id"], team_id)
    return get_roster(team_id)


@router.get("/{team_id}/engagement")
def team_engagement(team_id: int, authorization: str = Header(None)):
    payload = require_coach(authorization)
    assert_coach_owns_team(payload["coach_id"], team_id)
    return get_engagement(team_id)
