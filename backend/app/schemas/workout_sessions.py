from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel

from backend.app.schemas.common import APIModel


class SplitType(StrEnum):
    PUSH = "PUSH"
    PULL = "PULL"
    LEGS = "LEGS"
    OTHER = "OTHER"


class WorkoutSessionCreate(BaseModel):
    workout_date: date
    split_type: SplitType
    notes: str | None = None


class WorkoutSessionUpdate(BaseModel):
    workout_date: date | None = None
    split_type: SplitType | None = None
    notes: str | None = None


class WorkoutSessionResponse(APIModel):
    id: int
    workout_date: date
    split_type: SplitType
    notes: str | None
    created_at: datetime
    updated_at: datetime
