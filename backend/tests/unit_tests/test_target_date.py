from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from backend.app.ml.forecast_validation import ForecastSeries
from backend.app.ml.target_date import (
    REASON_ALREADY_ACHIEVED,
    REASON_FLAT_TREND,
    REASON_NEGATIVE_TREND,
    REASON_NO_CROSSING,
    TARGET_DATE_STATUS_ACHIEVED,
    TARGET_DATE_STATUS_PREDICTED,
    TARGET_DATE_STATUS_UNAVAILABLE,
    TREND_FLAT,
    TREND_NEGATIVE,
    TREND_POSITIVE,
    classify_forecast_trend,
    estimate_target_date,
)


def _series(values: list[float], start: date | None = None) -> ForecastSeries:
    day0 = start or date(2026, 1, 1)
    dates = tuple(day0 + timedelta(days=7 * index) for index in range(len(values)))
    return ForecastSeries(dates=dates, values=tuple(values))


def _forecast(
    as_of: date,
    *,
    days: int,
    start_yhat: float,
    daily_delta: float,
    band: float = 2.0,
) -> pd.DataFrame:
    rows: list[dict] = []
    for offset in range(1, days + 1):
        day = as_of + timedelta(days=offset)
        yhat = start_yhat + daily_delta * offset
        rows.append(
            {
                "ds": pd.Timestamp(day),
                "yhat": yhat,
                "yhat_lower": yhat - band,
                "yhat_upper": yhat + band,
            }
        )
    return pd.DataFrame(rows)


def test_classify_forecast_trend() -> None:
    assert classify_forecast_trend([100.0, 100.2]) == TREND_FLAT
    assert classify_forecast_trend([100.0, 99.0]) == TREND_NEGATIVE
    assert classify_forecast_trend([100.0, 110.0]) == TREND_POSITIVE


def test_already_achieved_skips_future_date() -> None:
    series = _series([100.0, 120.0])
    forecast = _forecast(series.dates[-1], days=30, start_yhat=120.0, daily_delta=0.1)
    result = estimate_target_date(series, 115.0, forecast)
    assert result.status == TARGET_DATE_STATUS_ACHIEVED
    assert result.reason == REASON_ALREADY_ACHIEVED
    assert result.crossing_date is None
    assert result.has_prediction is False


def test_predicted_crossing_and_interval_bounds() -> None:
    series = _series([100.0, 102.0, 104.0])
    as_of = series.dates[-1]
    forecast = _forecast(as_of, days=40, start_yhat=104.0, daily_delta=0.5, band=3.0)
    result = estimate_target_date(series, 110.0, forecast)
    assert result.status == TARGET_DATE_STATUS_PREDICTED
    assert result.trend == TREND_POSITIVE
    assert result.reason is None
    assert result.crossing_date is not None
    assert result.crossing_date_upper is not None
    assert result.crossing_date_lower is not None
    assert result.crossing_date_upper <= result.crossing_date <= result.crossing_date_lower


def test_flat_trend_has_no_date() -> None:
    series = _series([100.0, 100.1])
    forecast = _forecast(series.dates[-1], days=20, start_yhat=100.1, daily_delta=0.0)
    result = estimate_target_date(series, 120.0, forecast)
    assert result.status == TARGET_DATE_STATUS_UNAVAILABLE
    assert result.reason == REASON_FLAT_TREND
    assert result.crossing_date is None


def test_negative_trend_has_no_date() -> None:
    series = _series([110.0, 108.0])
    forecast = _forecast(series.dates[-1], days=20, start_yhat=108.0, daily_delta=-0.2)
    result = estimate_target_date(series, 120.0, forecast)
    assert result.status == TARGET_DATE_STATUS_UNAVAILABLE
    assert result.reason == REASON_NEGATIVE_TREND
    assert result.crossing_date is None


def test_no_crossing_within_horizon() -> None:
    series = _series([100.0, 101.0, 102.0])
    forecast = _forecast(series.dates[-1], days=10, start_yhat=102.0, daily_delta=0.1)
    result = estimate_target_date(series, 200.0, forecast)
    assert result.status == TARGET_DATE_STATUS_UNAVAILABLE
    assert result.reason == REASON_NO_CROSSING
    assert result.crossing_date is None
