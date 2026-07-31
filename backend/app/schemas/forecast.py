from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from backend.app.schemas.common import APIModel

ForecastResultStatus = Literal["ACHIEVED", "PREDICTED", "UNAVAILABLE"]
FreshnessStatus = Literal["FRESH", "STALE_DATA", "STALE_AGE"]
TrendStatus = Literal["POSITIVE", "FLAT", "NEGATIVE"]


class ForecastResponse(APIModel):
    status: ForecastResultStatus
    exercise_id: int
    goal_id: int
    target_1rm_kg: Decimal
    current_best_1rm_kg: Decimal
    crossing_date: date | None = None
    crossing_date_lower: date | None = None
    crossing_date_upper: date | None = None
    trend: TrendStatus
    reason: str | None = None
    sample_count: int
    data_date_from: date | None = None
    data_date_to: date | None = None
    feature_pipeline_version: str
    model_run_id: int | None = None
    trained_at: datetime | None = None
    data_fingerprint: str | None = None
    current_fingerprint: str
    freshness: FreshnessStatus | None = None
    warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    horizon_days: int = 0
