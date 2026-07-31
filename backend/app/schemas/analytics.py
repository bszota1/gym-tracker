from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    date_from: date | None = None
    date_to: date | None = None
    semantics_version: str
    rolling_window_days: int | None = None
    units: dict[str, str] | None = None


class BodyWeightPoint(BaseModel):
    date: date
    body_weight_kg: float | None = None


class RollingPoint(BaseModel):
    date: date
    rolling_avg_kg: float | None = None


class BodyWeightTrendResponse(BaseModel):
    points: list[BodyWeightPoint]
    trend: list[RollingPoint]
    rate_kg_per_week: float | None = None
    meta: AnalyticsMeta


class OneRmSourceSet(BaseModel):
    set_id: int
    session_id: int
    exercise_id: int
    set_number: int
    weight_kg: float | None = None
    reps: int
    rpe: float | None = None


class OneRmPoint(BaseModel):
    date: date
    one_rm_kg: float
    is_lifetime_pr: bool
    source_set: OneRmSourceSet


class OneRmTrendResponse(BaseModel):
    points: list[OneRmPoint]
    trend: list[RollingPoint]
    rate_kg_per_week: float | None = None
    meta: AnalyticsMeta


class StrengthVsWeightPoint(BaseModel):
    date: date
    one_rm_kg: float | None = None
    body_weight_kg: float | None = None


class StrengthVsWeightResponse(BaseModel):
    points: list[StrengthVsWeightPoint]
    meta: AnalyticsMeta


class RecoveryPoint(BaseModel):
    date: date
    sleep_hours: float | None = None
    calories_kcal: int | None = None
    body_weight_kg: float | None = None
    volume_kg: float | None = None
    rpe_avg: float | None = None
    rpe_n: int = 0
    one_rm_kg: float | None = None
    one_rm_delta: float | None = None


class RecoveryResponse(BaseModel):
    points: list[RecoveryPoint]
    meta: AnalyticsMeta


class OverviewMetric(BaseModel):
    model_config = ConfigDict(extra="allow")

    value: float | int | None = None
    as_of: date | None = None


class OverviewResponse(BaseModel):
    body_weight: OverviewMetric
    delta_to_target_kg: OverviewMetric
    avg_calories_kcal: OverviewMetric
    avg_sleep_hours: OverviewMetric
    sessions_this_week: OverviewMetric
    meta: dict[str, Any] = Field(default_factory=dict)
