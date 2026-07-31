from __future__ import annotations

from prophet import Prophet

MAX_FORECAST_HORIZON_DAYS = 365
PROPHET_YEARLY_SEASONALITY = False
PROPHET_WEEKLY_SEASONALITY = False
PROPHET_DAILY_SEASONALITY = False
PROPHET_SEASONALITY_MODE = "additive"
PROPHET_CHANGEPOINT_PRIOR_SCALE = 0.05
PROPHET_UNCERTAINTY_SAMPLES = 100
PROPHET_N_CHANGEPOINTS = 5


def create_prophet_model(*, n_observations: int | None = None) -> Prophet:
    n_changepoints = PROPHET_N_CHANGEPOINTS
    if n_observations is not None:
        n_changepoints = max(0, min(PROPHET_N_CHANGEPOINTS, n_observations - 2))
    return Prophet(
        yearly_seasonality=PROPHET_YEARLY_SEASONALITY,
        weekly_seasonality=PROPHET_WEEKLY_SEASONALITY,
        daily_seasonality=PROPHET_DAILY_SEASONALITY,
        seasonality_mode=PROPHET_SEASONALITY_MODE,
        changepoint_prior_scale=PROPHET_CHANGEPOINT_PRIOR_SCALE,
        uncertainty_samples=PROPHET_UNCERTAINTY_SAMPLES,
        n_changepoints=n_changepoints,
    )
