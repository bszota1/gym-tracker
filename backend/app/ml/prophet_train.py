from __future__ import annotations

import logging
from datetime import date
from functools import partial

import anyio
import pandas as pd
from prophet import Prophet

from backend.app.ml.forecast_validation import ForecastSeries
from backend.app.ml.prophet_config import (
    MAX_FORECAST_HORIZON_DAYS,
    create_prophet_model,
)


def _silence_prophet_logs() -> None:
    logging.getLogger("prophet").setLevel(logging.WARNING)
    logging.getLogger("cmdstanpy").setLevel(logging.WARNING)


def series_to_prophet_frame(series: ForecastSeries) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ds": [pd.Timestamp(day) for day in series.dates],
            "y": list(series.values),
        }
    )


def fit_prophet(series: ForecastSeries) -> Prophet:
    if series.size < 2:
        raise ValueError("Prophet requires at least 2 observations")
    _silence_prophet_logs()
    frame = series_to_prophet_frame(series)
    model = create_prophet_model(n_observations=series.size)
    model.fit(frame)
    return model


def predict_prophet_on_dates(
    model: Prophet,
    dates: list[date] | tuple[date, ...],
) -> list[float]:
    if not dates:
        return []
    future = pd.DataFrame({"ds": [pd.Timestamp(day) for day in dates]})
    forecast = model.predict(future)
    return [float(value) for value in forecast["yhat"].tolist()]


def make_horizon_forecast(
    model: Prophet,
    *,
    periods: int | None = None,
    include_history: bool = True,
) -> pd.DataFrame:
    horizon = MAX_FORECAST_HORIZON_DAYS if periods is None else periods
    if horizon < 0:
        raise ValueError("periods must be >= 0")
    if horizon > MAX_FORECAST_HORIZON_DAYS:
        horizon = MAX_FORECAST_HORIZON_DAYS
    future = model.make_future_dataframe(
        periods=horizon,
        freq="D",
        include_history=include_history,
    )
    return model.predict(future)


async def fit_prophet_async(series: ForecastSeries) -> Prophet:
    return await anyio.to_thread.run_sync(fit_prophet, series)


async def make_horizon_forecast_async(
    model: Prophet,
    *,
    periods: int | None = None,
    include_history: bool = True,
) -> pd.DataFrame:
    return await anyio.to_thread.run_sync(
        partial(
            make_horizon_forecast,
            model,
            periods=periods,
            include_history=include_history,
        )
    )
