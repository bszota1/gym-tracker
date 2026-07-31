from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.db.models.exercises import Exercise
from backend.app.db.models.workout_session import WorkoutSession
from backend.app.db.models.workout_sets import WorkoutSet
from backend.app.domain.one_rm import calculate_1rm
from backend.app.repositories.workout_sets import WorkoutSetRepository
from backend.app.schemas.workout_sets import WorkoutSetCreate, WorkoutSetUpdate


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

    async def update(self, set_id: int, data: WorkoutSetUpdate) -> WorkoutSet:
        workout_set: WorkoutSet | None = await self._sets.get_by_id(set_id)
        if workout_set is None:
            raise NotFoundError("Workout set not found")

        exercise_id = data.exercise_id if data.exercise_id is not None else workout_set.exercise_id
        set_number = data.set_number if data.set_number is not None else workout_set.set_number
        weight_kg = data.weight_kg if data.weight_kg is not None else workout_set.weight_kg
        reps = data.reps if data.reps is not None else workout_set.reps
        rpe = data.rpe if data.rpe is not None else workout_set.rpe
        is_warmup = data.is_warmup if data.is_warmup is not None else workout_set.is_warmup

        if exercise_id != workout_set.exercise_id:
            exercise: Exercise | None = await self._session.get(Exercise, exercise_id)
            if exercise is None:
                raise NotFoundError("Exercise not found")
            if not exercise.is_active:
                raise ConflictError("Exercise is archived")

        if exercise_id != workout_set.exercise_id or set_number != workout_set.set_number:
            existing = await self._session.execute(
                select(WorkoutSet).where(
                    WorkoutSet.session_id == workout_set.session_id,
                    WorkoutSet.exercise_id == exercise_id,
                    WorkoutSet.set_number == set_number,
                    WorkoutSet.id != set_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise ConflictError("Set number already exists")

        workout_set.exercise_id = exercise_id
        workout_set.set_number = set_number
        workout_set.weight_kg = weight_kg
        workout_set.reps = reps
        workout_set.rpe = rpe
        workout_set.is_warmup = is_warmup
        workout_set.calculated_1rm = calculate_1rm(weight_kg, reps)
        workout_set.updated_at = datetime.now(UTC)

        await self._session.commit()
        return workout_set

    async def delete(self, set_id: int) -> None:
        workout_set: WorkoutSet | None = await self._sets.get_by_id(set_id)
        if workout_set is None:
            raise NotFoundError("Workout set not found")

        await self._sets.delete(workout_set)
        await self._session.commit()

    async def get_by_id(self, set_id: int) -> WorkoutSet:
        workout_set = await self._sets.get_by_id(set_id)
        if workout_set is None:
            raise NotFoundError("Workout set not found")
        return workout_set

    async def list_by_session(self, session_id: int) -> list[WorkoutSet]:
        workout_session: WorkoutSession | None = await self._session.get(
            WorkoutSession, session_id
        )
        if workout_session is None:
            raise NotFoundError("Workout session not found")
        return await self._sets.list_by_session(session_id)
