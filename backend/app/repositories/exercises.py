from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.exercises import Exercise

class ExerciseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, exercise_id: int) -> Exercise | None:
        result: Exercise | None = await self._session.get(Exercise, exercise_id)
        return result

    async def get_by_name(self, name: str) -> Exercise | None:
        stmt = select(Exercise).where(func.lower(Exercise.name) == name.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, *, is_active: bool | None = None) -> list[Exercise]:
        stmt = select(Exercise)
        if is_active is not None:
            stmt = stmt.where(Exercise.is_active == is_active)
        stmt = stmt.order_by(Exercise.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, exercise: Exercise) -> Exercise:
        self._session.add(exercise)
        await self._session.flush()
        return exercise