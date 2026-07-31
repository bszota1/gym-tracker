from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.alert_feedback import AlertFeedback


class AlertFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_key(
        self,
        *,
        exercise_id: int,
        alert_date: date,
        model_run_id: int | None,
    ) -> AlertFeedback | None:
        stmt = (
            select(AlertFeedback)
            .where(AlertFeedback.exercise_id == exercise_id)
            .where(AlertFeedback.alert_date == alert_date)
        )
        if model_run_id is None:
            stmt = stmt.where(AlertFeedback.model_run_id.is_(None))
        else:
            stmt = stmt.where(AlertFeedback.model_run_id == model_run_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_exercise(
        self,
        *,
        exercise_id: int,
        threshold_version: str | None = None,
    ) -> list[AlertFeedback]:
        stmt = select(AlertFeedback).where(AlertFeedback.exercise_id == exercise_id)
        if threshold_version is not None:
            stmt = stmt.where(AlertFeedback.threshold_version == threshold_version)
        stmt = stmt.order_by(AlertFeedback.created_at.desc(), AlertFeedback.id.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, row: AlertFeedback) -> AlertFeedback:
        self._session.add(row)
        await self._session.flush()
        return row
