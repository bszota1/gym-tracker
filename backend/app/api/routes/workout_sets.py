from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.workout_sets import (
    WorkoutSetCreate,
    WorkoutSetResponse,
    WorkoutSetUpdate,
)
from backend.app.services.workout_sets import WorkoutSetService

router = APIRouter(tags=["workout-sets"])


def get_workout_set_service(db: AsyncSession = Depends(get_db)) -> WorkoutSetService:
    return WorkoutSetService(db)


@router.post(
    "/api/v1/sessions/{session_id}/sets",
    response_model=WorkoutSetResponse,
    status_code=201,
)
async def create_set(
    session_id: int,
    data: WorkoutSetCreate,
    service: WorkoutSetService = Depends(get_workout_set_service),
) -> WorkoutSetResponse:
    workout_set = await service.create(session_id, data)
    return WorkoutSetResponse.model_validate(workout_set)


@router.get(
    "/api/v1/sets/{set_id}",
    response_model=WorkoutSetResponse,
)
async def get_set(
    set_id: int,
    service: WorkoutSetService = Depends(get_workout_set_service),
) -> WorkoutSetResponse:
    workout_set = await service.get_by_id(set_id)
    return WorkoutSetResponse.model_validate(workout_set)


@router.patch(
    "/api/v1/sets/{set_id}",
    response_model=WorkoutSetResponse,
)
async def update_set(
    set_id: int,
    data: WorkoutSetUpdate,
    service: WorkoutSetService = Depends(get_workout_set_service),
) -> WorkoutSetResponse:
    workout_set = await service.update(set_id, data)
    return WorkoutSetResponse.model_validate(workout_set)


@router.delete(
    "/api/v1/sets/{set_id}",
    status_code=204,
)
async def delete_set(
    set_id: int,
    service: WorkoutSetService = Depends(get_workout_set_service),
) -> Response:
    await service.delete(set_id)
    return Response(status_code=204)
