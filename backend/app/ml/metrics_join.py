from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

_METRIC_COLUMNS = [
    "metric_date",
    "body_weight_kg",
    "calories_kcal",
    "sleep_hours",
]


def _rows_to_frame(rows: list[Any], columns: list[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=columns)
    records: list[dict[str, Any]] = []
    for row in rows:
        if hasattr(row, "_mapping"):
            mapping = row._mapping
        else:
            mapping = dict(zip(columns, row, strict=False))
        records.append({key: mapping[key] for key in columns})
    return pd.DataFrame.from_records(records, columns=columns)


def _as_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, pd.Timestamp):
        return value
    return pd.Timestamp(value).date()


def _as_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def _as_int(value: Any) -> int | None:
    number = _as_float(value)
    if number is None:
        return None
    return int(number)


def join_daily_metrics(
    observations: list[dict[str, Any]],
    metric_rows: list[Any],
) -> list[dict[str, Any]]:
    metrics = _rows_to_frame(metric_rows, _METRIC_COLUMNS)
    metrics_by_date: dict[date, dict[str, Any]] = {}
    if not metrics.empty:
        for row in metrics.itertuples(index=False):
            day = _as_date(row.metric_date)
            metrics_by_date[day] = {
                "body_weight_kg": _as_float(row.body_weight_kg),
                "calories_kcal": _as_int(row.calories_kcal),
                "sleep_hours": _as_float(row.sleep_hours),
            }

    joined: list[dict[str, Any]] = []
    for item in sorted(observations, key=lambda row: row["date"]):
        day = item["date"]
        if not isinstance(day, date):
            day = _as_date(day)
        metric = metrics_by_date.get(day, {})
        body_weight = metric.get("body_weight_kg")
        sleep_hours = metric.get("sleep_hours")
        calories = metric.get("calories_kcal")
        joined.append(
            {
                **item,
                "date": day,
                "body_weight_kg": body_weight,
                "sleep_hours": sleep_hours,
                "calories_kcal": calories,
                "body_weight_missing": body_weight is None,
                "sleep_missing": sleep_hours is None,
                "calories_missing": calories is None,
            }
        )
    return joined
