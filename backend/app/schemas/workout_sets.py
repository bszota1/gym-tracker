from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import datetime

from backend.app.schemas.common import APIModel


class WorkoutSetCreate(BaseModel):
    exercise_id: int
    set_number: int = Field(ge=1)
    weight_kg: Decimal = Field(ge=Decimal("0"), le=Decimal("1000"))
    reps: int = Field(ge=1, le=100)
    rpe: Decimal | None = Field(default=None, ge=Decimal("1"), le=Decimal("10"))
    is_warmup: bool = False

    @field_validator("rpe")
    @classmethod
    def validate_rep_step(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if (value * 2) % 1 != 0:
            raise ValueError("RPE must use 0.5 step")
        return value


class WorkoutSetUpdate(BaseModel):
    exercise_id: int | None = None
    set_number: int | None = Field(default=None, ge=1)
    weight_kg: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("1000"))
    reps: int | None = Field(default=None, ge=1, le=100)
    rpe: Decimal | None = Field(default=None, ge=Decimal("1"), le=Decimal("10"))
    is_warmup: bool | None = None

    @field_validator("rpe")
    @classmethod
    def validate_rpe_step(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if (value * 2) % 1 != 0:
            raise ValueError("RPE must use 0.5 step")
        return value


class WorkoutSetResponse(APIModel):
    id: int
    session_id: int
    exercise_id: int
    set_number: int
    weight_kg: Decimal
    reps: int
    rpe: Decimal | None
    is_warmup: bool
    calculated_1rm: Decimal
    created_at: datetime
    updated_at: datetime
