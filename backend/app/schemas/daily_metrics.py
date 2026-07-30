from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date, datetime

from backend.app.schemas.common import APIModel

class DailyMetricCreate(BaseModel):
    metric_date: date
    body_weight_kg: Decimal | None = Field(default=None, ge=Decimal("30"), le=Decimal("300"))
    calories_kcal: int | None = Field(default=None, ge=500, le=10000)
    sleep_hours: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("24"))
    notes: str | None = Field(default=None, max_length=2000)

class DailyMetricUpdate(BaseModel):
    body_weight_kg: Decimal | None = Field(default=None, ge=Decimal("30"), le=Decimal("300"))
    calories_kcal: int | None = Field(default=None, ge=500, le=10000)
    sleep_hours: Decimal | None = Field(default=None, ge=Decimal("0"), le=Decimal("24"))
    notes: str | None = Field(default=None, max_length=2000)

class DailyMetricResponse(APIModel):
    metric_date: date
    body_weight_kg: Decimal | None
    calories_kcal: int | None
    sleep_hours: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime