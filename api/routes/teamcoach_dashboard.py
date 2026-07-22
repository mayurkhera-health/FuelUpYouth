"""TeamCoach read-only dashboard API.

All handlers: coach bearer token required, team access scoped to coach.
Never exposes nutrition/macro/clinical data.
"""
from fastapi import APIRouter, Header
from api.routes.teamcoach_auth import require_coach
from api.services.teamcoach_service import (
    get_coach_teams, assert_coach_owns_team, get_roster, get_engagement,
    get_athlete_detail,
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


@router.get("/{team_id}/athletes/{athlete_id}")
def athlete_detail(team_id: int, athlete_id: int, authorization: str = Header(None)):
    from fastapi import HTTPException
    payload = require_coach(authorization)
    assert_coach_owns_team(payload["coach_id"], team_id)
    detail = get_athlete_detail(team_id, athlete_id)
    if detail is None:
        raise HTTPException(404, "Athlete not found on this team")
    return detail
