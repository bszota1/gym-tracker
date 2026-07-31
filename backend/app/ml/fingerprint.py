from __future__ import annotations

import hashlib
from datetime import date, datetime
from decimal import Decimal
from math import isnan
from typing import Any

from backend.app.ml.pipeline_contract import (
    FEATURE_PIPELINE_VERSION,
    REQUIRED_DAILY_COLUMNS,
)


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(float(value), ".12g")
    if isinstance(value, float):
        if isnan(value):
            return ""
        return format(value, ".12g")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    return str(value)


def _canonical_row(row: dict[str, Any], columns: tuple[str, ...]) -> str:
    return ",".join(_normalize_value(row.get(column)) for column in columns)


def compute_dataset_fingerprint(
    rows: list[dict[str, Any]],
    *,
    exercise_id: int,
    feature_pipeline_version: str = FEATURE_PIPELINE_VERSION,
    columns: tuple[str, ...] = REQUIRED_DAILY_COLUMNS,
) -> str:
    ordered = sorted(
        rows,
        key=lambda row: (
            _normalize_value(row.get("date")),
            _normalize_value(row.get("set_id")),
            _normalize_value(row.get("session_id")),
        ),
    )
    parts = [
        f"feature_pipeline_version={feature_pipeline_version}",
        f"exercise_id={exercise_id}",
        "columns=" + ",".join(columns),
        f"sample_count={len(ordered)}",
    ]
    parts.extend(_canonical_row(row, columns) for row in ordered)
    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
