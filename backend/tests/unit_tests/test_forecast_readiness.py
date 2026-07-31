from __future__ import annotations

from datetime import date, timedelta

from backend.app.ml.forecast_readiness import (
    FORECAST_STATUS_INSUFFICIENT_DATA,
    FORECAST_STATUS_OK,
    MIN_ONE_RM_RANGE_KG,
    MIN_SPAN_DAYS,
    MIN_UNIQUE_TRAINING_DAYS,
    REASON_CONSTANT_SERIES,
    REASON_SPAN_TOO_SHORT,
    REASON_TOO_FEW_DAYS,
    ForecastInsufficientDataError,
    assess_forecast_readiness,
    require_forecast_ready,
)


def _rows(
    *,
    start: date,
    count: int,
    step_days: int,
    start_one_rm: float,
    delta: float,
) -> list[dict]:
    rows: list[dict] = []
    for index in range(count):
        day = start + timedelta(days=step_days * index)
        rows.append(
            {
                "date": day,
                "one_rm_kg": start_one_rm + delta * index,
            }
        )
    return rows


def test_insufficient_when_too_few_unique_days() -> None:
    rows = _rows(
        start=date(2026, 1, 1),
        count=MIN_UNIQUE_TRAINING_DAYS - 1,
        step_days=7,
        start_one_rm=100.0,
        delta=1.0,
    )
    readiness = assess_forecast_readiness(rows)
    assert readiness.status == FORECAST_STATUS_INSUFFICIENT_DATA
    assert readiness.can_forecast is False
    assert REASON_TOO_FEW_DAYS in readiness.reasons
    assert readiness.unique_days == MIN_UNIQUE_TRAINING_DAYS - 1


def test_insufficient_when_span_too_short() -> None:
    rows = _rows(
        start=date(2026, 1, 1),
        count=MIN_UNIQUE_TRAINING_DAYS,
        step_days=1,
        start_one_rm=100.0,
        delta=1.0,
    )
    readiness = assess_forecast_readiness(rows)
    assert readiness.status == FORECAST_STATUS_INSUFFICIENT_DATA
    assert REASON_SPAN_TOO_SHORT in readiness.reasons
    assert readiness.span_days is not None
    assert readiness.span_days < MIN_SPAN_DAYS


def test_insufficient_when_constant_series() -> None:
    rows = _rows(
        start=date(2026, 1, 1),
        count=MIN_UNIQUE_TRAINING_DAYS,
        step_days=7,
        start_one_rm=100.0,
        delta=0.0,
    )
    readiness = assess_forecast_readiness(rows)
    assert readiness.status == FORECAST_STATUS_INSUFFICIENT_DATA
    assert REASON_CONSTANT_SERIES in readiness.reasons
    assert readiness.one_rm_range_kg is not None
    assert readiness.one_rm_range_kg < MIN_ONE_RM_RANGE_KG


def test_ready_when_minimums_met() -> None:
    rows = _rows(
        start=date(2026, 1, 1),
        count=MIN_UNIQUE_TRAINING_DAYS,
        step_days=5,
        start_one_rm=100.0,
        delta=1.0,
    )
    readiness = assess_forecast_readiness(rows)
    assert readiness.span_days is not None
    assert readiness.span_days >= MIN_SPAN_DAYS
    assert readiness.status == FORECAST_STATUS_OK
    assert readiness.can_forecast is True
    assert readiness.reasons == ()


def test_require_forecast_ready_raises_controlled_status() -> None:
    rows = _rows(
        start=date(2026, 1, 1),
        count=3,
        step_days=1,
        start_one_rm=100.0,
        delta=1.0,
    )
    try:
        require_forecast_ready(rows)
        raise AssertionError("expected ForecastInsufficientDataError")
    except ForecastInsufficientDataError as exc:
        assert exc.readiness.status == FORECAST_STATUS_INSUFFICIENT_DATA
        assert REASON_TOO_FEW_DAYS in exc.readiness.reasons
