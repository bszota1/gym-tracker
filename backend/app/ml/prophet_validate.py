from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import mean_absolute_error

from backend.app.ml.forecast_baseline import (
    evaluate_last_value_baseline,
    is_better_than_baseline,
)
from backend.app.ml.forecast_validation import (
    FORECAST_CV_SPLITS,
    ForecastSeries,
    iter_time_series_folds,
)
from backend.app.ml.prophet_train import fit_prophet, predict_prophet_on_dates

PROPHET_STATUS_ACCEPTED = "ACCEPTED"
PROPHET_STATUS_REJECTED_WORSE_THAN_BASELINE = "REJECTED_WORSE_THAN_BASELINE"
SAFE_MAPE_MIN_ABS_Y = 1.0


@dataclass(frozen=True, slots=True)
class ProphetValidationResult:
    status: str
    mae: float
    mape: float | None
    baseline_mae: float
    fold_maes: tuple[float, ...]
    n_splits: int
    n_predictions: int
    beats_baseline: bool

    @property
    def accepted(self) -> bool:
        return self.status == PROPHET_STATUS_ACCEPTED


def safe_mape(
    y_true: list[float],
    y_pred: list[float],
    *,
    min_abs_y: float = SAFE_MAPE_MIN_ABS_Y,
) -> float | None:
    if len(y_true) != len(y_pred) or not y_true:
        return None
    truths = np.asarray(y_true, dtype=float)
    preds = np.asarray(y_pred, dtype=float)
    mask = np.abs(truths) >= min_abs_y
    if not np.any(mask):
        return None
    ratios = np.abs((truths[mask] - preds[mask]) / truths[mask])
    return float(np.mean(ratios) * 100.0)


def evaluate_prophet(
    series: ForecastSeries,
    *,
    n_splits: int = FORECAST_CV_SPLITS,
) -> ProphetValidationResult:
    baseline = evaluate_last_value_baseline(series, n_splits=n_splits)
    fold_maes: list[float] = []
    all_true: list[float] = []
    all_pred: list[float] = []

    for fold in iter_time_series_folds(series.size, n_splits=n_splits):
        train_series = ForecastSeries(
            dates=tuple(series.dates[i] for i in fold.train_indices),
            values=tuple(series.values[i] for i in fold.train_indices),
        )
        test_dates = tuple(series.dates[i] for i in fold.test_indices)
        y_true = [series.values[i] for i in fold.test_indices]
        model = fit_prophet(train_series)
        y_pred = predict_prophet_on_dates(model, test_dates)
        fold_maes.append(float(mean_absolute_error(y_true, y_pred)))
        all_true.extend(y_true)
        all_pred.extend(y_pred)

    mae = float(mean_absolute_error(all_true, all_pred))
    mape = safe_mape(all_true, all_pred)
    beats = is_better_than_baseline(mae, baseline.mae)
    status = (
        PROPHET_STATUS_ACCEPTED
        if beats
        else PROPHET_STATUS_REJECTED_WORSE_THAN_BASELINE
    )
    return ProphetValidationResult(
        status=status,
        mae=mae,
        mape=mape,
        baseline_mae=baseline.mae,
        fold_maes=tuple(fold_maes),
        n_splits=n_splits,
        n_predictions=len(all_true),
        beats_baseline=beats,
    )
