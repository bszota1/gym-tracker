from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from backend.app.domain.analytics_defs import (
    INCLUDE_WARMUPS_IN_VOLUME,
    MAX_REPS_FOR_STRENGTH_TREND,
    ROLLING_WINDOW_DAYS,
    is_eligible_for_strength_trend,
    set_volume_kg,
)

FEATURE_PIPELINE_VERSION = "1"

REQUIRED_DAILY_COLUMNS: tuple[str, ...] = (
    "date",
    "one_rm_kg",
    "weight_kg",
    "reps",
    "rpe",
    "session_id",
    "set_id",
    "body_weight_kg",
    "sleep_hours",
    "calories_kcal",
    "body_weight_missing",
    "sleep_missing",
    "calories_missing",
    "volume_kg",
    "days_since_prev_session",
    "one_rm_delta",
    "one_rm_roll_7",
    "one_rm_roll_28",
)


@dataclass(frozen=True, slots=True)
class PipelineInput:
    exercise_id: int
    date_from: date | None = None
    date_to: date | None = None


@dataclass(slots=True)
class PipelineMeta:
    exercise_id: int
    feature_pipeline_version: str
    date_from: date | None
    date_to: date | None
    sample_count: int
    fingerprint: str | None = None
    rolling_window_days: int = ROLLING_WINDOW_DAYS
    max_reps_for_trend: int = MAX_REPS_FOR_STRENGTH_TREND
    include_warmups_in_volume: bool = INCLUDE_WARMUPS_IN_VOLUME
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PipelineResult:
    rows: list[dict[str, Any]]
    meta: PipelineMeta

    def column_names(self) -> list[str]:
        if not self.rows:
            return list(REQUIRED_DAILY_COLUMNS)
        return list(self.rows[0].keys())


def uses_strength_eligibility(is_warmup: bool, reps: int) -> bool:
    return is_eligible_for_strength_trend(is_warmup=is_warmup, reps=reps)


def volume_for_set(weight_kg: Any, reps: int) -> Any:
    return set_volume_kg(weight_kg, reps)
