from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.model_runs import ModelRun
from backend.app.ml.model_types import MODEL_RUN_STATUS_SUCCESS


class ModelRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_success(
        self,
        *,
        model_type: str,
        exercise_id: int,
    ) -> ModelRun | None:
        stmt = (
            select(ModelRun)
            .where(ModelRun.model_type == model_type)
            .where(ModelRun.exercise_id == exercise_id)
            .where(ModelRun.status == MODEL_RUN_STATUS_SUCCESS)
            .order_by(ModelRun.trained_at.desc(), ModelRun.id.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, run: ModelRun) -> ModelRun:
        self._session.add(run)
        await self._session.flush()
        return run
