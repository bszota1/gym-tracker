from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.analytics.queries import AnalyticsQueries
from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.db.models.strength_goals import StrengthGoal
from backend.app.domain.strength_goals import (
    GOAL_STATUS_ACHIEVED,
    GOAL_STATUS_ACTIVE,
    GOAL_STATUS_ARCHIVED,
    USER_SETTABLE_GOAL_STATUSES,
)
from backend.app.ml.observations import select_daily_strength_observations
from backend.app.repositories.exercises import ExerciseRepository
from backend.app.repositories.strength_goals import StrengthGoalRepository
from backend.app.schemas.strength_goals import StrengthGoalCreate, StrengthGoalUpdate


class StrengthGoalService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._goals = StrengthGoalRepository(session)
        self._exercises = ExerciseRepository(session)
        self._analytics = AnalyticsQueries(session)

    async def create(self, data: StrengthGoalCreate) -> StrengthGoal:
        exercise = await self._exercises.get_by_id(data.exercise_id)
        if exercise is None:
            raise NotFoundError("Exercise not found")
        if not exercise.is_active:
            raise ConflictError("Cannot create goal for inactive exercise")

        await self._archive_active_for_exercise(data.exercise_id)

        goal = StrengthGoal(
            exercise_id=data.exercise_id,
            target_1rm_kg=data.target_1rm_kg,
            target_date=data.target_date,
            status=GOAL_STATUS_ACTIVE,
        )
        created = await self._goals.create(goal)
        await self._apply_achievement(created)
        await self._session.commit()
        await self._session.refresh(created)
        return created

    async def get_by_id(self, goal_id: int) -> StrengthGoal:
        goal = await self._goals.get_by_id(goal_id)
        if goal is None:
            raise NotFoundError("Strength goal not found")
        changed = await self._apply_achievement(goal)
        if changed:
            await self._session.commit()
            await self._session.refresh(goal)
        return goal

    async def list(
        self,
        *,
        exercise_id: int | None = None,
        status: str | None = None,
    ) -> list[StrengthGoal]:
        goals = await self._goals.list(exercise_id=exercise_id, status=status)
        changed = False
        for goal in goals:
            if await self._apply_achievement(goal):
                changed = True
        if changed:
            await self._session.commit()
            for goal in goals:
                await self._session.refresh(goal)
        return goals

    async def update(self, goal_id: int, data: StrengthGoalUpdate) -> StrengthGoal:
        goal = await self._goals.get_by_id(goal_id)
        if goal is None:
            raise NotFoundError("Strength goal not found")

        payload = data.model_dump(exclude_unset=True)
        if "target_1rm_kg" in payload and payload["target_1rm_kg"] is not None:
            goal.target_1rm_kg = payload["target_1rm_kg"]
        if "target_date" in payload:
            goal.target_date = payload["target_date"]
        if "status" in payload and payload["status"] is not None:
            new_status = payload["status"]
            if new_status not in USER_SETTABLE_GOAL_STATUSES:
                raise ConflictError("Status can only be set to ACTIVE or ARCHIVED")
            if new_status == GOAL_STATUS_ACTIVE and goal.status != GOAL_STATUS_ACTIVE:
                await self._archive_active_for_exercise(goal.exercise_id, exclude_id=goal.id)
            goal.status = new_status

        await self._apply_achievement(goal)
        await self._session.commit()
        await self._session.refresh(goal)
        return goal

    async def _archive_active_for_exercise(
        self,
        exercise_id: int,
        *,
        exclude_id: int | None = None,
    ) -> None:
        actives = await self._goals.list_active_for_exercise(exercise_id)
        for active in actives:
            if exclude_id is not None and active.id == exclude_id:
                continue
            active.status = GOAL_STATUS_ARCHIVED

    async def _best_eligible_one_rm(self, exercise_id: int) -> Decimal | None:
        set_rows = await self._analytics.fetch_set_rows_for_strength(
            date_from=date(1970, 1, 1),
            date_to=date(2100, 1, 1),
            exercise_id=exercise_id,
        )
        observations = select_daily_strength_observations(
            set_rows,
            exercise_id=exercise_id,
        )
        if not observations:
            return None
        best = max(float(item["one_rm_kg"]) for item in observations)
        return Decimal(str(best))

    async def _apply_achievement(self, goal: StrengthGoal) -> bool:
        if goal.status != GOAL_STATUS_ACTIVE:
            return False
        best = await self._best_eligible_one_rm(goal.exercise_id)
        if best is None:
            return False
        if best >= goal.target_1rm_kg:
            goal.status = GOAL_STATUS_ACHIEVED
            return True
        return False
