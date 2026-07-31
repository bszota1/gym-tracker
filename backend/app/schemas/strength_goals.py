from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.common import APIModel

GoalStatus = Literal["ACTIVE", "ACHIEVED", "ARCHIVED"]
UserSettableGoalStatus = Literal["ACTIVE", "ARCHIVED"]


class StrengthGoalCreate(BaseModel):
    exercise_id: int
    target_1rm_kg: Decimal = Field(gt=Decimal("0"), le=Decimal("1000"))
    target_date: date | None = None


class StrengthGoalUpdate(BaseModel):
    target_1rm_kg: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        le=Decimal("1000"),
    )
    target_date: date | None = None
    status: UserSettableGoalStatus | None = None


class StrengthGoalResponse(APIModel):
    id: int
    exercise_id: int
    target_1rm_kg: Decimal
    target_date: date | None
    status: GoalStatus
