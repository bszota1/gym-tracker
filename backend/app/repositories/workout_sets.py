from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.workout_sets import WorkoutSet


class WorkoutSetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, set_id: int) -> WorkoutSet | None:
        result: WorkoutSet | None = await self._session.get(WorkoutSet, set_id)
        return result

    async def list_by_session(self, session_id: int) -> list[WorkoutSet]:
        stmt = (
            select(WorkoutSet)
            .where(WorkoutSet.session_id == session_id)
            .order_by(WorkoutSet.exercise_id, WorkoutSet.set_number)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, workout_set: WorkoutSet) -> WorkoutSet:
        self._session.add(workout_set)
        await self._session.flush()
        return workout_set

    async def delete(self, workout_set: WorkoutSet) -> None:
        await self._session.delete(workout_set)
