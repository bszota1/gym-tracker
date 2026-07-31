from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from backend.app.ml.forecast_readiness import MIN_UNIQUE_TRAINING_DAYS
from backend.app.ml.forecast_validation import build_forecast_series
from backend.app.ml.prophet_config import (
    MAX_FORECAST_HORIZON_DAYS,
    PROPHET_DAILY_SEASONALITY,
    PROPHET_WEEKLY_SEASONALITY,
    PROPHET_YEARLY_SEASONALITY,
    create_prophet_model,
)
from backend.app.ml.prophet_train import (
    fit_prophet,
    make_horizon_forecast,
    series_to_prophet_frame,
)
from backend.app.ml.prophet_validate import (
    PROPHET_STATUS_ACCEPTED,
    PROPHET_STATUS_REJECTED_WORSE_THAN_BASELINE,
    ProphetValidationResult,
    evaluate_prophet,
    safe_mape,
)


def _rising_rows(count: int = 12) -> list[dict]:
    start = date(2026, 1, 1)
    return [
        {
            "date": start + timedelta(days=7 * index),
            "one_rm_kg": 100.0 + 1.5 * index,
        }
        for index in range(count)
    ]


def test_prophet_frame_and_config() -> None:
    series = build_forecast_series(_rising_rows(MIN_UNIQUE_TRAINING_DAYS))
    frame = series_to_prophet_frame(series)
    assert list(frame.columns) == ["ds", "y"]
    assert len(frame) == MIN_UNIQUE_TRAINING_DAYS
    assert PROPHET_YEARLY_SEASONALITY is False
    assert PROPHET_WEEKLY_SEASONALITY is False
    assert PROPHET_DAILY_SEASONALITY is False
    model = create_prophet_model(n_observations=series.size)
    assert model.yearly_seasonality is False
    assert model.weekly_seasonality is False
    assert model.daily_seasonality is False


def test_fit_prophet_and_horizon_cap() -> None:
    series = build_forecast_series(_rising_rows(10))
    model = fit_prophet(series)
    forecast = make_horizon_forecast(model, periods=MAX_FORECAST_HORIZON_DAYS + 50)
    last_history = pd.Timestamp(series.dates[-1])
    future_only = forecast.loc[forecast["ds"] > last_history]
    assert len(future_only) == MAX_FORECAST_HORIZON_DAYS


def test_safe_mape_skips_near_zero() -> None:
    assert safe_mape([0.0, 0.1], [0.0, 0.2], min_abs_y=1.0) is None
    mape = safe_mape([100.0, 110.0], [100.0, 121.0], min_abs_y=1.0)
    assert mape is not None
    assert mape == pytest.approx(5.0)


def test_evaluate_prophet_on_rising_series() -> None:
    series = build_forecast_series(_rising_rows(12))
    result = evaluate_prophet(series)
    assert isinstance(result, ProphetValidationResult)
    assert result.n_predictions > 0
    assert result.mae >= 0.0
    assert result.mape is not None
    assert result.baseline_mae >= 0.0
    assert result.status in {
        PROPHET_STATUS_ACCEPTED,
        PROPHET_STATUS_REJECTED_WORSE_THAN_BASELINE,
    }
    assert result.accepted is result.beats_baseline


def test_reject_when_worse_than_baseline_decision() -> None:
    result = ProphetValidationResult(
        status=PROPHET_STATUS_REJECTED_WORSE_THAN_BASELINE,
        mae=5.0,
        mape=4.0,
        baseline_mae=2.0,
        fold_maes=(5.0,),
        n_splits=1,
        n_predictions=1,
        beats_baseline=False,
    )
    assert result.accepted is False
