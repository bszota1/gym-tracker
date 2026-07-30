from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.workout_session import WorkoutSession


class WorkoutSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, session_id: int) -> WorkoutSession | None:
        return await self._session.get(WorkoutSession, session_id)

    async def list(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        split_type: str | None = None,
    ) -> list[WorkoutSession]:
        stmt = select(WorkoutSession)

        if date_from is not None:
            stmt = stmt.where(WorkoutSession.workout_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(WorkoutSession.workout_date <= date_to)
        if split_type is not None:
            stmt = stmt.where(WorkoutSession.split_type == split_type)

        stmt = stmt.order_by(WorkoutSession.workout_date, WorkoutSession.id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, workout_session: WorkoutSession) -> WorkoutSession:
        self._session.add(workout_session)
        await self._session.flush()
        return workout_session

    async def delete(self, workout_session: WorkoutSession) -> None:
        await self._session.delete(workout_session)
