from __future__ import annotations

from dataclasses import dataclass

from sklearn.metrics import mean_absolute_error

from backend.app.ml.forecast_validation import (
    FORECAST_CV_SPLITS,
    ForecastSeries,
    iter_time_series_folds,
)

BASELINE_KIND_LAST_VALUE = "last_value"


@dataclass(frozen=True, slots=True)
class BaselineForecastResult:
    kind: str
    mae: float
    fold_maes: tuple[float, ...]
    n_splits: int
    n_predictions: int
    last_value: float

    @property
    def is_reference_only(self) -> bool:
        return True


def last_value_predict(train_values: list[float] | tuple[float, ...]) -> float:
    if not train_values:
        raise ValueError("Cannot build last-value baseline without training points")
    return float(train_values[-1])


def evaluate_last_value_baseline(
    series: ForecastSeries,
    *,
    n_splits: int = FORECAST_CV_SPLITS,
) -> BaselineForecastResult:
    fold_maes: list[float] = []
    all_true: list[float] = []
    all_pred: list[float] = []

    for fold in iter_time_series_folds(series.size, n_splits=n_splits):
        train = [series.values[i] for i in fold.train_indices]
        y_true = [series.values[i] for i in fold.test_indices]
        prediction = last_value_predict(train)
        y_pred = [prediction] * len(y_true)
        fold_maes.append(float(mean_absolute_error(y_true, y_pred)))
        all_true.extend(y_true)
        all_pred.extend(y_pred)

    return BaselineForecastResult(
        kind=BASELINE_KIND_LAST_VALUE,
        mae=float(mean_absolute_error(all_true, all_pred)),
        fold_maes=tuple(fold_maes),
        n_splits=n_splits,
        n_predictions=len(all_true),
        last_value=float(series.values[-1]),
    )


def is_better_than_baseline(model_mae: float, baseline_mae: float) -> bool:
    return model_mae < baseline_mae
