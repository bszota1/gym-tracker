from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.workout_sessions import (
    SplitType,
    WorkoutSessionCreate,
    WorkoutSessionResponse,
    WorkoutSessionUpdate,
)
from backend.app.services.workout_sessions import WorkoutSessionService

router = APIRouter(tags=["workout-sessions"])


def get_workout_session_service(
    db: AsyncSession = Depends(get_db),
) -> WorkoutSessionService:
    return WorkoutSessionService(db)


@router.post(
    "/api/v1/sessions",
    response_model=WorkoutSessionResponse,
    status_code=201,
)
async def create_session(
    data: WorkoutSessionCreate,
    service: WorkoutSessionService = Depends(get_workout_session_service),
) -> WorkoutSessionResponse:
    workout_session = await service.create(data)
    return WorkoutSessionResponse.model_validate(workout_session)


@router.get(
    "/api/v1/sessions",
    response_model=list[WorkoutSessionResponse],
)
async def list_sessions(
    date_from: date | None = None,
    date_to: date | None = None,
    split_type: SplitType | None = None,
    service: WorkoutSessionService = Depends(get_workout_session_service),
) -> list[WorkoutSessionResponse]:
    sessions = await service.list(
        date_from=date_from,
        date_to=date_to,
        split_type=split_type.value if split_type is not None else None,
    )
    return [WorkoutSessionResponse.model_validate(session) for session in sessions]


@router.get(
    "/api/v1/sessions/{session_id}",
    response_model=WorkoutSessionResponse,
)
async def get_session(
    session_id: int,
    service: WorkoutSessionService = Depends(get_workout_session_service),
) -> WorkoutSessionResponse:
    workout_session = await service.get_by_id(session_id)
    return WorkoutSessionResponse.model_validate(workout_session)


@router.patch(
    "/api/v1/sessions/{session_id}",
    response_model=WorkoutSessionResponse,
)
async def update_session(
    session_id: int,
    data: WorkoutSessionUpdate,
    service: WorkoutSessionService = Depends(get_workout_session_service),
) -> WorkoutSessionResponse:
    workout_session = await service.update(session_id, data)
    return WorkoutSessionResponse.model_validate(workout_session)


@router.delete(
    "/api/v1/sessions/{session_id}",
    status_code=204,
)
async def delete_session(
    session_id: int,
    service: WorkoutSessionService = Depends(get_workout_session_service),
) -> Response:
    await service.delete(session_id)
    return Response(status_code=204)
