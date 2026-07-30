from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.daily_metrics import DailyMetric


class DailyMetricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_date(self, metric_date: date) -> DailyMetric | None:
        return await self._session.get(DailyMetric, metric_date)

    async def list_by_daterange(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[DailyMetric]:
        stmt = select(DailyMetric)

        if date_from is not None:
            stmt = stmt.where(DailyMetric.metric_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(DailyMetric.metric_date <= date_to)

        stmt = stmt.order_by(DailyMetric.metric_date)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, daily_metric: DailyMetric) -> DailyMetric:
        self._session.add(daily_metric)
        await self._session.flush()
        return daily_metric

    async def delete(self, daily_metric: DailyMetric) -> None:
        await self._session.delete(daily_metric)

    async def ensure_day(self, metric_date: date) -> DailyMetric:
        existing = await self.get_by_date(metric_date)
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        daily_metric = DailyMetric(
            metric_date=metric_date,
            body_weight_kg=None,
            calories_kcal=None,
            sleep_hours=None,
            notes=None,
            created_at=now,
            updated_at=now,
        )
        return await self.create(daily_metric)
