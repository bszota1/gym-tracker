from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.daily_metrics import DailyMetric
from backend.app.db.models.workout_session import WorkoutSession
from backend.app.db.models.workout_sets import WorkoutSet


class AnalyticsQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fetch_body_weight_rows(self, date_from: date, date_to: date) -> list[Any]:
        stmt = (
            select(DailyMetric.metric_date, DailyMetric.body_weight_kg)
            .where(DailyMetric.metric_date >= date_from)
            .where(DailyMetric.metric_date <= date_to)
            .where(DailyMetric.body_weight_kg.is_not(None))
            .order_by(DailyMetric.metric_date)
        )
        result = await self._session.execute(stmt)
        return list(result.all())

    async def fetch_set_rows_for_strength(
        self,
        *,
        date_from: date,
        date_to: date,
        exercise_id: int | None = None,
    ) -> list[Any]:
        stmt = (
            select(
                WorkoutSession.workout_date,
                WorkoutSet.id,
                WorkoutSet.session_id,
                WorkoutSet.exercise_id,
                WorkoutSet.set_number,
                WorkoutSet.weight_kg,
                WorkoutSet.reps,
                WorkoutSet.rpe,
                WorkoutSet.is_warmup,
                WorkoutSet.calculated_1rm,
            )
            .select_from(WorkoutSet)
            .join(WorkoutSession, WorkoutSet.session_id == WorkoutSession.id)
            .where(WorkoutSession.workout_date >= date_from)
            .where(WorkoutSession.workout_date <= date_to)
            .order_by(
                WorkoutSession.workout_date,
                WorkoutSet.exercise_id,
                WorkoutSet.set_number,
            )
        )
        if exercise_id is not None:
            stmt = stmt.where(WorkoutSet.exercise_id == exercise_id)

        result = await self._session.execute(stmt)
        return list(result.all())

    async def fetch_daily_metric_rows(self, date_from: date, date_to: date) -> list[Any]:
        stmt = (
            select(
                DailyMetric.metric_date,
                DailyMetric.body_weight_kg,
                DailyMetric.calories_kcal,
                DailyMetric.sleep_hours,
            )
            .where(DailyMetric.metric_date >= date_from)
            .where(DailyMetric.metric_date <= date_to)
            .order_by(DailyMetric.metric_date)
        )
        result = await self._session.execute(stmt)
        return list(result.all())

    async def fetch_session_dates(self, date_from: date, date_to: date) -> list[Any]:
        stmt = (
            select(WorkoutSession.id, WorkoutSession.workout_date)
            .where(WorkoutSession.workout_date >= date_from)
            .where(WorkoutSession.workout_date <= date_to)
            .order_by(WorkoutSession.workout_date, WorkoutSession.id)
        )
        result = await self._session.execute(stmt)
        return list(result.all())
