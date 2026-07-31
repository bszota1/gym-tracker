from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
from prophet import Prophet

from backend.app.ml.forecast_validation import ForecastSeries
from backend.app.ml.prophet_config import MAX_FORECAST_HORIZON_DAYS
from backend.app.ml.prophet_train import fit_prophet, make_horizon_forecast

TARGET_DATE_STATUS_ACHIEVED = "ACHIEVED"
TARGET_DATE_STATUS_PREDICTED = "PREDICTED"
TARGET_DATE_STATUS_UNAVAILABLE = "UNAVAILABLE"

TREND_POSITIVE = "POSITIVE"
TREND_FLAT = "FLAT"
TREND_NEGATIVE = "NEGATIVE"

REASON_ALREADY_ACHIEVED = "already_achieved"
REASON_NO_CROSSING = "no_crossing_within_horizon"
REASON_FLAT_TREND = "flat_trend"
REASON_NEGATIVE_TREND = "negative_trend"

FLAT_TREND_EPSILON_KG = 0.5


@dataclass(frozen=True, slots=True)
class TargetDateEstimate:
    status: str
    target_1rm_kg: float
    current_best_1rm_kg: float
    trend: str
    reason: str | None
    crossing_date: date | None
    crossing_date_lower: date | None
    crossing_date_upper: date | None
    horizon_days: int
    as_of_date: date | None

    @property
    def has_prediction(self) -> bool:
        return self.status == TARGET_DATE_STATUS_PREDICTED and self.crossing_date is not None


def _as_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, pd.Timestamp):
        return value
    return pd.Timestamp(value).date()


def _first_crossing(
    dates: list[date],
    values: list[float],
    target: float,
) -> date | None:
    for day, value in zip(dates, values, strict=True):
        if value >= target:
            return day
    return None


def classify_forecast_trend(
    future_values: list[float],
    *,
    flat_epsilon_kg: float = FLAT_TREND_EPSILON_KG,
) -> str:
    if len(future_values) < 2:
        return TREND_FLAT
    delta = float(future_values[-1] - future_values[0])
    if abs(delta) < flat_epsilon_kg:
        return TREND_FLAT
    if delta < 0:
        return TREND_NEGATIVE
    return TREND_POSITIVE


def estimate_target_date(
    series: ForecastSeries,
    target_1rm_kg: float,
    forecast: pd.DataFrame,
) -> TargetDateEstimate:
    if series.size == 0:
        raise ValueError("Cannot estimate target date without observations")
    if target_1rm_kg <= 0:
        raise ValueError("target_1rm_kg must be positive")

    target = float(target_1rm_kg)
    current_best = float(max(series.values))
    as_of = series.dates[-1]

    if current_best >= target:
        return TargetDateEstimate(
            status=TARGET_DATE_STATUS_ACHIEVED,
            target_1rm_kg=target,
            current_best_1rm_kg=current_best,
            trend=TREND_POSITIVE,
            reason=REASON_ALREADY_ACHIEVED,
            crossing_date=None,
            crossing_date_lower=None,
            crossing_date_upper=None,
            horizon_days=0,
            as_of_date=as_of,
        )

    required = {"ds", "yhat", "yhat_lower", "yhat_upper"}
    missing = required - set(forecast.columns)
    if missing:
        raise ValueError(f"Forecast frame missing columns: {sorted(missing)}")

    future = forecast.loc[forecast["ds"] > pd.Timestamp(as_of)].copy()
    future = future.sort_values("ds")
    if future.empty:
        return TargetDateEstimate(
            status=TARGET_DATE_STATUS_UNAVAILABLE,
            target_1rm_kg=target,
            current_best_1rm_kg=current_best,
            trend=TREND_FLAT,
            reason=REASON_NO_CROSSING,
            crossing_date=None,
            crossing_date_lower=None,
            crossing_date_upper=None,
            horizon_days=0,
            as_of_date=as_of,
        )

    dates = [_as_date(value) for value in future["ds"].tolist()]
    yhat = [float(value) for value in future["yhat"].tolist()]
    yhat_lower = [float(value) for value in future["yhat_lower"].tolist()]
    yhat_upper = [float(value) for value in future["yhat_upper"].tolist()]
    horizon_days = len(dates)
    trend = classify_forecast_trend(yhat)

    if trend == TREND_FLAT:
        return TargetDateEstimate(
            status=TARGET_DATE_STATUS_UNAVAILABLE,
            target_1rm_kg=target,
            current_best_1rm_kg=current_best,
            trend=trend,
            reason=REASON_FLAT_TREND,
            crossing_date=None,
            crossing_date_lower=None,
            crossing_date_upper=None,
            horizon_days=horizon_days,
            as_of_date=as_of,
        )
    if trend == TREND_NEGATIVE:
        return TargetDateEstimate(
            status=TARGET_DATE_STATUS_UNAVAILABLE,
            target_1rm_kg=target,
            current_best_1rm_kg=current_best,
            trend=trend,
            reason=REASON_NEGATIVE_TREND,
            crossing_date=None,
            crossing_date_lower=None,
            crossing_date_upper=None,
            horizon_days=horizon_days,
            as_of_date=as_of,
        )

    crossing = _first_crossing(dates, yhat, target)
    crossing_lower = _first_crossing(dates, yhat_lower, target)
    crossing_upper = _first_crossing(dates, yhat_upper, target)

    if crossing is None:
        return TargetDateEstimate(
            status=TARGET_DATE_STATUS_UNAVAILABLE,
            target_1rm_kg=target,
            current_best_1rm_kg=current_best,
            trend=trend,
            reason=REASON_NO_CROSSING,
            crossing_date=None,
            crossing_date_lower=crossing_lower,
            crossing_date_upper=crossing_upper,
            horizon_days=horizon_days,
            as_of_date=as_of,
        )

    return TargetDateEstimate(
        status=TARGET_DATE_STATUS_PREDICTED,
        target_1rm_kg=target,
        current_best_1rm_kg=current_best,
        trend=trend,
        reason=None,
        crossing_date=crossing,
        crossing_date_lower=crossing_lower,
        crossing_date_upper=crossing_upper,
        horizon_days=horizon_days,
        as_of_date=as_of,
    )


def estimate_target_date_with_model(
    series: ForecastSeries,
    target_1rm_kg: float,
    model: Prophet,
    *,
    horizon_days: int = MAX_FORECAST_HORIZON_DAYS,
) -> TargetDateEstimate:
    forecast = make_horizon_forecast(model, periods=horizon_days, include_history=True)
    return estimate_target_date(series, target_1rm_kg, forecast)


def estimate_target_date_from_series(
    series: ForecastSeries,
    target_1rm_kg: float,
    *,
    horizon_days: int = MAX_FORECAST_HORIZON_DAYS,
) -> TargetDateEstimate:
    current_best = float(max(series.values)) if series.size else 0.0
    if series.size > 0 and current_best >= float(target_1rm_kg):
        return estimate_target_date(
            series,
            target_1rm_kg,
            pd.DataFrame(columns=["ds", "yhat", "yhat_lower", "yhat_upper"]),
        )
    model = fit_prophet(series)
    return estimate_target_date_with_model(
        series,
        target_1rm_kg,
        model,
        horizon_days=horizon_days,
    )
