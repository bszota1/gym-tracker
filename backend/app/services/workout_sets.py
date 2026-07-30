from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import UTC, datetime

from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.db.models.exercises import Exercise
from backend.app.db.models.workout_session import WorkoutSession
from backend.app.db.models.workout_sets import WorkoutSet
from backend.app.repositories.workout_sets import WorkoutSetRepository
from backend.app.schemas.workout_sets import WorkoutSetCreate
from backend.app.domain.one_rm import calculate_1rm


class WorkoutSetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sets = WorkoutSetRepository(session)

    async def create(self, session_id: int, data: WorkoutSetCreate) -> WorkoutSet:
        workout_session: WorkoutSession | None = await self._session.get(WorkoutSession, session_id)
        if workout_session is None:
            raise NotFoundError("Workout session not found")

        exercise: Exercise | None = await self._session.get(Exercise, data.exercise_id)
        if exercise is None:
            raise NotFoundError("Exercise not found")
        if not exercise.is_active:
            raise ConflictError("Exercise is archived")

        existing = await self._session.execute(
            select(WorkoutSet).where(
                WorkoutSet.session_id == session_id,
                WorkoutSet.exercise_id == data.exercise_id,
                WorkoutSet.set_number == data.set_number,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("Set number already exists")

        calculated_1rm = calculate_1rm(data.weight_kg, data.reps)
        now = datetime.now(UTC)

        workout_set = WorkoutSet(
            session_id=session_id,
            exercise_id=data.exercise_id,
            set_number=data.set_number,
            weight_kg=data.weight_kg,
            reps=data.reps,
            rpe=data.rpe,
            is_warmup=data.is_warmup,
            calculated_1rm=calculated_1rm,
            created_at=now,
            updated_at=now,
        )

        created = await self._sets.create(workout_set)
        await self._session.commit()
        return created
