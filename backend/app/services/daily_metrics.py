from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.db.models.daily_metrics import DailyMetric
from backend.app.db.models.workout_session import WorkoutSession
from backend.app.repositories.daily_metrics import DailyMetricRepository
from backend.app.schemas.daily_metrics import DailyMetricCreate, DailyMetricUpdate


class DailyMetricService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._daily_metrics = DailyMetricRepository(session)

    async def get_by_date(self, metric_date: date) -> DailyMetric:
        daily_metric = await self._daily_metrics.get_by_date(metric_date)
        if daily_metric is None:
            raise NotFoundError("Daily metric not found")
        return daily_metric

    async def list(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[DailyMetric]:
        return await self._daily_metrics.list_by_daterange(
            date_from=date_from,
            date_to=date_to,
        )

    async def create(self, data: DailyMetricCreate) -> DailyMetric:
        existing = await self._daily_metrics.get_by_date(data.metric_date)
        if existing is not None:
            raise ConflictError("Daily metric already exists")

        now = datetime.now(UTC)
        daily_metric = DailyMetric(
            metric_date=data.metric_date,
            body_weight_kg=data.body_weight_kg,
            calories_kcal=data.calories_kcal,
            sleep_hours=data.sleep_hours,
            notes=data.notes,
            created_at=now,
            updated_at=now,
        )
        created = await self._daily_metrics.create(daily_metric)
        await self._session.commit()
        return created

    async def update(self, metric_date: date, data: DailyMetricUpdate) -> DailyMetric:
        daily_metric = await self.get_by_date(metric_date)

        if data.body_weight_kg is not None:
            daily_metric.body_weight_kg = data.body_weight_kg
        if data.calories_kcal is not None:
            daily_metric.calories_kcal = data.calories_kcal
        if data.sleep_hours is not None:
            daily_metric.sleep_hours = data.sleep_hours
        if data.notes is not None:
            daily_metric.notes = data.notes

        daily_metric.updated_at = datetime.now(UTC)
        await self._session.commit()
        return daily_metric

    async def delete(self, metric_date: date) -> None:
        daily_metric = await self.get_by_date(metric_date)

        result = await self._session.execute(
            select(WorkoutSession.id).where(WorkoutSession.workout_date == metric_date).limit(1)
        )
        if result.scalar_one_or_none() is not None:
            raise ConflictError("Cannot delete day with workout sessions")

        await self._daily_metrics.delete(daily_metric)
        await self._session.commit()
