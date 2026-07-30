from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.exercises import (
    ExerciseCreate,
    ExerciseResponse,
    ExerciseUpdate,
)
from backend.app.services.exercises import ExerciseService

router = APIRouter(tags=["exercises"])


def get_exercise_service(db: AsyncSession = Depends(get_db)) -> ExerciseService:
    return ExerciseService(db)


@router.post(
    "/api/v1/exercises",
    response_model=ExerciseResponse,
    status_code=201,
)
async def create_exercise(
    data: ExerciseCreate,
    service: ExerciseService = Depends(get_exercise_service),
) -> ExerciseResponse:
    exercise = await service.create(data)
    return ExerciseResponse.model_validate(exercise)


@router.get(
    "/api/v1/exercises",
    response_model=list[ExerciseResponse],
)
async def get_exercises(
    is_active: bool | None = None,
    service: ExerciseService = Depends(get_exercise_service),
) -> list[ExerciseResponse]:
    exercises = await service.list(is_active=is_active)
    return [ExerciseResponse.model_validate(exercise) for exercise in exercises]


@router.get(
    "/api/v1/exercises/{exercise_id}",
    response_model=ExerciseResponse,
)
async def get_exercise_by_id(
    exercise_id: int,
    service: ExerciseService = Depends(get_exercise_service),
) -> ExerciseResponse:
    exercise = await service.get_by_id(exercise_id)
    return ExerciseResponse.model_validate(exercise)


@router.patch(
    "/api/v1/exercises/{exercise_id}",
    response_model=ExerciseResponse,
)
async def update_exercise(
    exercise_id: int,
    data: ExerciseUpdate,
    service: ExerciseService = Depends(get_exercise_service),
) -> ExerciseResponse:
    exercise = await service.update(exercise_id, data)
    return ExerciseResponse.model_validate(exercise)
