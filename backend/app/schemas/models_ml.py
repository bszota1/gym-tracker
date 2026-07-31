from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.app.schemas.common import APIModel

FreshnessStatus = Literal["FRESH", "STALE_DATA", "STALE_AGE"]
WeightSuggestionStatus = Literal[
    "SUGGESTED",
    "BASELINE_PREFERRED",
    "INSUFFICIENT_DATA",
]


class ModelStatusResponse(BaseModel):
    exercise_id: int
    model_type: str
    has_model: bool
    freshness: FreshnessStatus | None = None
    warnings: list[str] = Field(default_factory=list)
    model_run_id: int | None = None
    trained_at: datetime | None = None
    sample_count: int = 0
    current_fingerprint: str
    data_fingerprint: str | None = None
    feature_pipeline_version: str
    age_days: int | None = None
    max_age_days: int | None = None
    deleted: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)


class ModelTrainResponse(BaseModel):
    accepted: bool
    model_run_id: int
    status: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_path: str | None = None
    kept_previous_model: bool = False


class AnomalyPointResponse(BaseModel):
    date: date
    one_rm_kg: float
    is_outlier: bool
    anomaly_score: float
    alert: bool
    severity: str | None = None
    reason: str | None = None
    message: str | None = None
    pct_dev_roll_7: float | None = None
    facts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    sleep_hours: float | None = None
    rpe: float | None = None
    prev_volume_kg: float | None = None


class AnomalyListResponse(BaseModel):
    exercise_id: int
    model_run_id: int
    trained_at: datetime
    freshness: FreshnessStatus
    warnings: list[str] = Field(default_factory=list)
    sample_count: int
    deleted: bool = False
    threshold_version: str
    points: list[AnomalyPointResponse]


class WeightSuggestionResponse(APIModel):
    exercise_id: int
    status: WeightSuggestionStatus
    suggested_weight_kg: Decimal | None = None
    last_successful_weight_kg: Decimal | None = None
    raw_prediction_kg: Decimal | None = None
    clamped: bool = False
    rounded_down: bool = False
    model_mae: float | None = None
    baseline_mae: float | None = None
    beats_baseline: bool | None = None
    sample_count: int
    reason: str | None = None
    is_suggestion_only: bool = True
    disclaimer: str
