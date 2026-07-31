from __future__ import annotations

from datetime import date, timedelta

from backend.app.ml.forecast_baseline import (
    BASELINE_KIND_LAST_VALUE,
    evaluate_last_value_baseline,
    is_better_than_baseline,
    last_value_predict,
)
from backend.app.ml.forecast_readiness import MIN_UNIQUE_TRAINING_DAYS
from backend.app.ml.forecast_validation import (
    FORECAST_CV_SPLITS,
    build_forecast_series,
    iter_time_series_folds,
)


def _rising_rows(count: int = MIN_UNIQUE_TRAINING_DAYS) -> list[dict]:
    start = date(2026, 1, 1)
    return [
        {
            "date": start + timedelta(days=5 * index),
            "one_rm_kg": 100.0 + float(index),
        }
        for index in range(count)
    ]


def test_last_value_predict_uses_most_recent() -> None:
    assert last_value_predict([100.0, 105.0, 110.0]) == 110.0


def test_baseline_mae_on_constant_series_is_zero() -> None:
    start = date(2026, 1, 1)
    rows = [
        {"date": start + timedelta(days=5 * index), "one_rm_kg": 100.0}
        for index in range(MIN_UNIQUE_TRAINING_DAYS)
    ]
    series = build_forecast_series(rows)
    result = evaluate_last_value_baseline(series)
    assert result.kind == BASELINE_KIND_LAST_VALUE
    assert result.mae == 0.0
    assert result.n_splits == FORECAST_CV_SPLITS
    assert result.is_reference_only is True
    assert result.last_value == 100.0


def test_baseline_mae_positive_on_rising_series() -> None:
    series = build_forecast_series(_rising_rows())
    result = evaluate_last_value_baseline(series)
    assert result.mae > 0.0
    assert len(result.fold_maes) == FORECAST_CV_SPLITS
    assert result.n_predictions > 0


def test_time_series_folds_train_only_on_past() -> None:
    folds = list(iter_time_series_folds(MIN_UNIQUE_TRAINING_DAYS))
    assert len(folds) == FORECAST_CV_SPLITS
    for fold in folds:
        assert max(fold.train_indices) < min(fold.test_indices)


def test_model_must_beat_baseline_to_promote() -> None:
    assert is_better_than_baseline(1.0, 2.0) is True
    assert is_better_than_baseline(2.0, 2.0) is False
    assert is_better_than_baseline(2.5, 2.0) is False
