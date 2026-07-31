from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

ANOMALY_FEATURE_COLUMNS: tuple[str, ...] = (
    "pct_dev_roll_7",
    "pct_dev_roll_28",
    "one_rm_delta",
    "rpe",
    "prev_volume_kg",
    "sleep_hours",
    "body_weight_kg",
    "days_since_prev_session",
)

MISSING_FEATURE_POLICY: dict[str, str] = {
    "pct_dev_roll_7": (
        "None when roll_7 is missing or ~0; SimpleImputer(median) at fit/predict"
    ),
    "pct_dev_roll_28": (
        "None when roll_28 is missing or ~0; SimpleImputer(median) at fit/predict"
    ),
    "one_rm_delta": "None on first session; SimpleImputer(median)",
    "rpe": "None when best-set RPE absent; SimpleImputer(median)",
    "prev_volume_kg": "None on first session; SimpleImputer(median)",
    "sleep_hours": (
        "None when daily sleep missing (no forward-fill); SimpleImputer(median)"
    ),
    "body_weight_kg": (
        "None when daily body weight missing (no forward-fill); "
        "SimpleImputer(median)"
    ),
    "days_since_prev_session": "None on first session; SimpleImputer(median)",
}

_ROLL_EPS = 1e-9


@dataclass(frozen=True, slots=True)
class AnomalyFeatureRow:
    date: date
    features: dict[str, float | None]
    one_rm_kg: float


def _as_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, pd.Timestamp):
        return value
    return pd.Timestamp(value).date()


def _nullable_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if pd.isna(value):
        return None
    return float(value)


def _pct_deviation(value: float, trend: float | None) -> float | None:
    if trend is None or abs(trend) < _ROLL_EPS:
        return None
    return (value - trend) / trend * 100.0


def build_anomaly_feature_rows(rows: list[dict[str, Any]]) -> list[AnomalyFeatureRow]:
    result: list[AnomalyFeatureRow] = []
    for row in sorted(rows, key=lambda item: _as_date(item["date"])):
        one_rm = float(row["one_rm_kg"])
        roll_7 = _nullable_float(row.get("one_rm_roll_7"))
        roll_28 = _nullable_float(row.get("one_rm_roll_28"))
        features = {
            "pct_dev_roll_7": _pct_deviation(one_rm, roll_7),
            "pct_dev_roll_28": _pct_deviation(one_rm, roll_28),
            "one_rm_delta": _nullable_float(row.get("one_rm_delta")),
            "rpe": _nullable_float(row.get("rpe")),
            "prev_volume_kg": _nullable_float(row.get("prev_volume_kg")),
            "sleep_hours": _nullable_float(row.get("sleep_hours")),
            "body_weight_kg": _nullable_float(row.get("body_weight_kg")),
            "days_since_prev_session": _nullable_float(row.get("days_since_prev_session")),
        }
        result.append(
            AnomalyFeatureRow(
                date=_as_date(row["date"]),
                features=features,
                one_rm_kg=one_rm,
            )
        )
    return result


def anomaly_feature_matrix(
    feature_rows: list[AnomalyFeatureRow],
) -> tuple[np.ndarray, tuple[str, ...]]:
    matrix = np.empty((len(feature_rows), len(ANOMALY_FEATURE_COLUMNS)), dtype=float)
    for row_index, item in enumerate(feature_rows):
        for col_index, name in enumerate(ANOMALY_FEATURE_COLUMNS):
            value = item.features.get(name)
            matrix[row_index, col_index] = np.nan if value is None else float(value)
    return matrix, ANOMALY_FEATURE_COLUMNS
