from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.strength_goals import StrengthGoal
from backend.app.domain.strength_goals import GOAL_STATUS_ACTIVE


class StrengthGoalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, goal_id: int) -> StrengthGoal | None:
        return await self._session.get(StrengthGoal, goal_id)

    async def list(
        self,
        *,
        exercise_id: int | None = None,
        status: str | None = None,
    ) -> list[StrengthGoal]:
        stmt = select(StrengthGoal)
        if exercise_id is not None:
            stmt = stmt.where(StrengthGoal.exercise_id == exercise_id)
        if status is not None:
            stmt = stmt.where(StrengthGoal.status == status)
        stmt = stmt.order_by(StrengthGoal.id.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_for_exercise(self, exercise_id: int) -> StrengthGoal | None:
        stmt = (
            select(StrengthGoal)
            .where(StrengthGoal.exercise_id == exercise_id)
            .where(StrengthGoal.status == GOAL_STATUS_ACTIVE)
            .order_by(StrengthGoal.id.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_for_exercise(self, exercise_id: int) -> list[StrengthGoal]:
        stmt = (
            select(StrengthGoal)
            .where(StrengthGoal.exercise_id == exercise_id)
            .where(StrengthGoal.status == GOAL_STATUS_ACTIVE)
            .order_by(StrengthGoal.id.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, goal: StrengthGoal) -> StrengthGoal:
        self._session.add(goal)
        await self._session.flush()
        return goal
