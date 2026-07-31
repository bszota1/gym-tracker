from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.app.ml.forecast_baseline import is_better_than_baseline
from backend.app.ml.forecast_validation import FORECAST_CV_SPLITS, iter_time_series_folds

MIN_WEIGHT_REGRESSION_SAMPLES = 12
WEIGHT_PLATE_INCREMENT_KG = 2.5
WEIGHT_RECOMMENDATION_MAX_RELATIVE_DELTA = 0.10
WEIGHT_RIDGE_ALPHA = 1.0
WEIGHT_FEATURE_COLUMNS: tuple[str, ...] = (
    "days_since_prev_session",
    "prev_volume_kg",
    "sleep_hours",
    "body_weight_kg",
    "rpe",
    "one_rm_delta",
)


@dataclass(frozen=True, slots=True)
class WeightSuggestion:
    status: str
    suggested_weight_kg: float | None
    last_successful_weight_kg: float | None
    raw_prediction_kg: float | None
    clamped: bool
    rounded_down: bool
    model_mae: float | None
    baseline_mae: float | None
    beats_baseline: bool | None
    sample_count: int
    reason: str | None
    is_suggestion_only: bool = True


def _matrix_from_rows(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    features: list[list[float]] = []
    targets: list[float] = []
    for row in rows:
        weight = row.get("weight_kg")
        if weight is None:
            continue
        values: list[float] = []
        skip = False
        for name in WEIGHT_FEATURE_COLUMNS:
            raw = row.get(name)
            if raw is None:
                skip = True
                break
            values.append(float(raw))
        if skip:
            continue
        features.append(values)
        targets.append(float(weight))
    if not features:
        return np.empty((0, len(WEIGHT_FEATURE_COLUMNS))), np.empty((0,))
    return np.asarray(features, dtype=float), np.asarray(targets, dtype=float)


def round_down_to_plate(
    weight_kg: float,
    *,
    increment_kg: float = WEIGHT_PLATE_INCREMENT_KG,
) -> float:
    if increment_kg <= 0:
        raise ValueError("increment_kg must be positive")
    steps = int(weight_kg // increment_kg)
    return float(steps * increment_kg)


def clamp_to_relative_band(
    value: float,
    *,
    center: float,
    max_relative_delta: float = WEIGHT_RECOMMENDATION_MAX_RELATIVE_DELTA,
) -> float:
    low = center * (1.0 - max_relative_delta)
    high = center * (1.0 + max_relative_delta)
    return float(min(max(value, low), high))


def _last_value_baseline_mae(y: np.ndarray, n_splits: int = FORECAST_CV_SPLITS) -> float:
    truths: list[float] = []
    preds: list[float] = []
    for fold in iter_time_series_folds(len(y), n_splits=n_splits):
        last = float(y[fold.train_indices[-1]])
        for index in fold.test_indices:
            truths.append(float(y[index]))
            preds.append(last)
    return float(mean_absolute_error(truths, preds))


def _ridge_cv_mae(x: np.ndarray, y: np.ndarray, n_splits: int = FORECAST_CV_SPLITS) -> float:
    truths: list[float] = []
    preds: list[float] = []
    for fold in iter_time_series_folds(len(y), n_splits=n_splits):
        model = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("ridge", Ridge(alpha=WEIGHT_RIDGE_ALPHA)),
            ]
        )
        model.fit(x[list(fold.train_indices)], y[list(fold.train_indices)])
        pred = model.predict(x[list(fold.test_indices)])
        truths.extend(float(v) for v in y[list(fold.test_indices)])
        preds.extend(float(v) for v in pred)
    return float(mean_absolute_error(truths, preds))


def suggest_next_weight(rows: list[dict[str, Any]]) -> WeightSuggestion:
    ordered = sorted(rows, key=lambda row: row["date"])
    x, y = _matrix_from_rows(ordered)
    sample_count = int(y.size)
    if sample_count < MIN_WEIGHT_REGRESSION_SAMPLES:
        return WeightSuggestion(
            status="INSUFFICIENT_DATA",
            suggested_weight_kg=None,
            last_successful_weight_kg=float(y[-1]) if sample_count else None,
            raw_prediction_kg=None,
            clamped=False,
            rounded_down=False,
            model_mae=None,
            baseline_mae=None,
            beats_baseline=None,
            sample_count=sample_count,
            reason="too_few_complete_feature_rows",
        )

    last_weight = float(y[-1])
    baseline_mae = _last_value_baseline_mae(y)
    model_mae = _ridge_cv_mae(x, y)
    beats = is_better_than_baseline(model_mae, baseline_mae)

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=WEIGHT_RIDGE_ALPHA)),
        ]
    )
    model.fit(x, y)
    raw = float(model.predict(x[-1].reshape(1, -1))[0])
    clamped_value = clamp_to_relative_band(raw, center=last_weight)
    rounded = round_down_to_plate(clamped_value)
    return WeightSuggestion(
        status="SUGGESTED" if beats else "BASELINE_PREFERRED",
        suggested_weight_kg=rounded,
        last_successful_weight_kg=last_weight,
        raw_prediction_kg=raw,
        clamped=clamped_value != raw,
        rounded_down=rounded != clamped_value,
        model_mae=model_mae,
        baseline_mae=baseline_mae,
        beats_baseline=beats,
        sample_count=sample_count,
        reason=None if beats else "model_not_better_than_baseline",
        is_suggestion_only=True,
    )
