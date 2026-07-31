from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.strength_goals import (
    GoalStatus,
    StrengthGoalCreate,
    StrengthGoalResponse,
    StrengthGoalUpdate,
)
from backend.app.services.strength_goals import StrengthGoalService

router = APIRouter(tags=["strength-goals"])


def get_strength_goal_service(db: AsyncSession = Depends(get_db)) -> StrengthGoalService:
    return StrengthGoalService(db)


@router.post(
    "/api/v1/strength-goals",
    response_model=StrengthGoalResponse,
    status_code=201,
)
async def create_strength_goal(
    data: StrengthGoalCreate,
    service: StrengthGoalService = Depends(get_strength_goal_service),
) -> StrengthGoalResponse:
    goal = await service.create(data)
    return StrengthGoalResponse.model_validate(goal)


@router.get(
    "/api/v1/strength-goals",
    response_model=list[StrengthGoalResponse],
)
async def list_strength_goals(
    exercise_id: int | None = None,
    status: GoalStatus | None = Query(default=None),
    service: StrengthGoalService = Depends(get_strength_goal_service),
) -> list[StrengthGoalResponse]:
    goals = await service.list(exercise_id=exercise_id, status=status)
    return [StrengthGoalResponse.model_validate(goal) for goal in goals]


@router.get(
    "/api/v1/strength-goals/{goal_id}",
    response_model=StrengthGoalResponse,
)
async def get_strength_goal(
    goal_id: int,
    service: StrengthGoalService = Depends(get_strength_goal_service),
) -> StrengthGoalResponse:
    goal = await service.get_by_id(goal_id)
    return StrengthGoalResponse.model_validate(goal)


@router.patch(
    "/api/v1/strength-goals/{goal_id}",
    response_model=StrengthGoalResponse,
)
async def update_strength_goal(
    goal_id: int,
    data: StrengthGoalUpdate,
    service: StrengthGoalService = Depends(get_strength_goal_service),
) -> StrengthGoalResponse:
    goal = await service.update(goal_id, data)
    return StrengthGoalResponse.model_validate(goal)
