from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError
from backend.app.db.models.workout_session import WorkoutSession
from backend.app.repositories.daily_metrics import DailyMetricRepository
from backend.app.repositories.workout_sessions import WorkoutSessionRepository
from backend.app.schemas.workout_sessions import WorkoutSessionCreate, WorkoutSessionUpdate


class WorkoutSessionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = WorkoutSessionRepository(session)
        self._daily_metrics = DailyMetricRepository(session)

    async def get_by_id(self, session_id: int) -> WorkoutSession:
        workout_session = await self._sessions.get_by_id(session_id)
        if workout_session is None:
            raise NotFoundError("Workout session not found")
        return workout_session

    async def list(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        split_type: str | None = None,
    ) -> list[WorkoutSession]:
        return await self._sessions.list(
            date_from=date_from,
            date_to=date_to,
            split_type=split_type,
        )

    async def create(self, data: WorkoutSessionCreate) -> WorkoutSession:
        await self._daily_metrics.ensure_day(data.workout_date)

        now = datetime.now(UTC)
        workout_session = WorkoutSession(
            workout_date=data.workout_date,
            split_type=data.split_type.value,
            notes=data.notes,
            created_at=now,
            updated_at=now,
        )
        created = await self._sessions.create(workout_session)
        await self._session.commit()
        return created

    async def update(self, session_id: int, data: WorkoutSessionUpdate) -> WorkoutSession:
        workout_session = await self.get_by_id(session_id)

        if data.workout_date is not None:
            await self._daily_metrics.ensure_day(data.workout_date)
            workout_session.workout_date = data.workout_date

        if data.split_type is not None:
            workout_session.split_type = data.split_type.value

        if data.notes is not None:
            workout_session.notes = data.notes

        workout_session.updated_at = datetime.now(UTC)
        await self._session.commit()
        return workout_session

    async def delete(self, session_id: int) -> None:
        workout_session = await self.get_by_id(session_id)
        await self._sessions.delete(workout_session)
        await self._session.commit()
