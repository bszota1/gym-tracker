from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

MIN_UNIQUE_TRAINING_DAYS = 8
MIN_SPAN_DAYS = 28
MIN_ONE_RM_RANGE_KG = 0.5

FORECAST_STATUS_OK = "OK"
FORECAST_STATUS_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

REASON_TOO_FEW_DAYS = "too_few_unique_days"
REASON_SPAN_TOO_SHORT = "span_too_short"
REASON_CONSTANT_SERIES = "constant_series"


@dataclass(frozen=True, slots=True)
class ForecastReadiness:
    status: str
    reasons: tuple[str, ...] = ()
    unique_days: int = 0
    span_days: int | None = None
    one_rm_range_kg: float | None = None
    sample_count: int = 0
    date_from: date | None = None
    date_to: date | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def can_forecast(self) -> bool:
        return self.status == FORECAST_STATUS_OK


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def assess_forecast_readiness(rows: list[dict[str, Any]]) -> ForecastReadiness:
    if not rows:
        return ForecastReadiness(
            status=FORECAST_STATUS_INSUFFICIENT_DATA,
            reasons=(REASON_TOO_FEW_DAYS,),
            unique_days=0,
            span_days=None,
            one_rm_range_kg=None,
            sample_count=0,
            extras={
                "min_unique_days": MIN_UNIQUE_TRAINING_DAYS,
                "min_span_days": MIN_SPAN_DAYS,
                "min_one_rm_range_kg": MIN_ONE_RM_RANGE_KG,
            },
        )

    by_day: dict[date, float] = {}
    for row in rows:
        day = _as_date(row["date"])
        one_rm = float(row["one_rm_kg"])
        previous = by_day.get(day)
        if previous is None or one_rm > previous:
            by_day[day] = one_rm

    days = sorted(by_day)
    values = [by_day[day] for day in days]
    unique_days = len(days)
    date_from = days[0]
    date_to = days[-1]
    span_days = (date_to - date_from).days
    one_rm_range = max(values) - min(values)

    reasons: list[str] = []
    if unique_days < MIN_UNIQUE_TRAINING_DAYS:
        reasons.append(REASON_TOO_FEW_DAYS)
    if span_days < MIN_SPAN_DAYS:
        reasons.append(REASON_SPAN_TOO_SHORT)
    if one_rm_range < MIN_ONE_RM_RANGE_KG:
        reasons.append(REASON_CONSTANT_SERIES)

    status = (
        FORECAST_STATUS_OK
        if not reasons
        else FORECAST_STATUS_INSUFFICIENT_DATA
    )
    return ForecastReadiness(
        status=status,
        reasons=tuple(reasons),
        unique_days=unique_days,
        span_days=span_days,
        one_rm_range_kg=one_rm_range,
        sample_count=len(rows),
        date_from=date_from,
        date_to=date_to,
        extras={
            "min_unique_days": MIN_UNIQUE_TRAINING_DAYS,
            "min_span_days": MIN_SPAN_DAYS,
            "min_one_rm_range_kg": MIN_ONE_RM_RANGE_KG,
        },
    )


def require_forecast_ready(rows: list[dict[str, Any]]) -> ForecastReadiness:
    readiness = assess_forecast_readiness(rows)
    if not readiness.can_forecast:
        raise ForecastInsufficientDataError(readiness)
    return readiness


class ForecastInsufficientDataError(Exception):
    def __init__(self, readiness: ForecastReadiness) -> None:
        self.readiness = readiness
        super().__init__(
            f"{FORECAST_STATUS_INSUFFICIENT_DATA}: {', '.join(readiness.reasons)}"
        )
