from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from backend.app.domain.analytics_defs import (
    INCLUDE_WARMUPS_IN_VOLUME,
    ROLLING_WINDOW_DAYS,
    is_eligible_for_strength_trend,
    set_volume_kg,
)


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


def _as_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def _as_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, pd.Timestamp):
        return value
    return pd.Timestamp(value).date()


def _rolling_mean(values: pd.Series) -> pd.Series:
    return values.rolling(window=ROLLING_WINDOW_DAYS, min_periods=1).mean()


def _rate_per_week(dates: list[date], values: list[float]) -> float | None:
    if len(dates) < 2 or len(values) < 2:
        return None
    span_days = (dates[-1] - dates[0]).days
    if span_days <= 0:
        return None
    return (values[-1] - values[0]) / span_days * 7.0


def body_weight_series(rows: list[Any]) -> dict[str, Any]:
    df = _rows_to_frame(rows, ["metric_date", "body_weight_kg"])
    if df.empty:
        return {
            "points": [],
            "trend": [],
            "rate_kg_per_week": None,
            "rolling_window_days": ROLLING_WINDOW_DAYS,
        }

    df = df.sort_values("metric_date").reset_index(drop=True)
    df["body_weight_kg"] = df["body_weight_kg"].astype(float)
    df["rolling_avg_kg"] = _rolling_mean(df["body_weight_kg"])

    points = [
        {
            "date": _as_date(row.metric_date),
            "body_weight_kg": _as_float(row.body_weight_kg),
        }
        for row in df.itertuples(index=False)
    ]
    trend = [
        {
            "date": _as_date(row.metric_date),
            "rolling_avg_kg": _as_float(row.rolling_avg_kg),
        }
        for row in df.itertuples(index=False)
    ]
    dates = [point["date"] for point in points]
    values = [
        float(point["body_weight_kg"])
        for point in points
        if point["body_weight_kg"] is not None
    ]

    return {
        "points": points,
        "trend": trend,
        "rate_kg_per_week": _rate_per_week(dates, values),
        "rolling_window_days": ROLLING_WINDOW_DAYS,
    }


def daily_one_rm_series(rows: list[Any]) -> dict[str, Any]:
    columns = [
        "workout_date",
        "id",
        "session_id",
        "exercise_id",
        "set_number",
        "weight_kg",
        "reps",
        "rpe",
        "is_warmup",
        "calculated_1rm",
    ]
    df = _rows_to_frame(rows, columns)
    if df.empty:
        return {
            "points": [],
            "trend": [],
            "rate_kg_per_week": None,
            "rolling_window_days": ROLLING_WINDOW_DAYS,
        }

    eligible_mask = [
        is_eligible_for_strength_trend(is_warmup=bool(is_warmup), reps=int(reps))
        for is_warmup, reps in zip(df["is_warmup"], df["reps"], strict=True)
    ]
    eligible = df.loc[eligible_mask].copy()
    if eligible.empty:
        return {
            "points": [],
            "trend": [],
            "rate_kg_per_week": None,
            "rolling_window_days": ROLLING_WINDOW_DAYS,
        }

    eligible["calculated_1rm"] = eligible["calculated_1rm"].astype(float)
    best_idx = eligible.groupby("workout_date", sort=True)["calculated_1rm"].idxmax()
    daily = eligible.loc[best_idx].sort_values("workout_date").reset_index(drop=True)
    daily["rolling_avg_kg"] = _rolling_mean(daily["calculated_1rm"])
    lifetime_max = float(daily["calculated_1rm"].max())

    points: list[dict[str, Any]] = []
    for row in daily.itertuples(index=False):
        one_rm = float(row.calculated_1rm)
        points.append(
            {
                "date": _as_date(row.workout_date),
                "one_rm_kg": one_rm,
                "is_lifetime_pr": one_rm == lifetime_max,
                "source_set": {
                    "set_id": int(row.id),
                    "session_id": int(row.session_id),
                    "exercise_id": int(row.exercise_id),
                    "set_number": int(row.set_number),
                    "weight_kg": _as_float(row.weight_kg),
                    "reps": int(row.reps),
                    "rpe": _as_float(row.rpe),
                },
            }
        )

    trend = [
        {
            "date": _as_date(row.workout_date),
            "rolling_avg_kg": _as_float(row.rolling_avg_kg),
        }
        for row in daily.itertuples(index=False)
    ]
    dates = [point["date"] for point in points]
    values = [float(point["one_rm_kg"]) for point in points]

    return {
        "points": points,
        "trend": trend,
        "rate_kg_per_week": _rate_per_week(dates, values),
        "rolling_window_days": ROLLING_WINDOW_DAYS,
    }


def strength_vs_weight(
    one_rm_points: list[dict[str, Any]],
    weight_points: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    one_rm_by_date = {
        point["date"]: point.get("one_rm_kg") for point in one_rm_points
    }
    weight_by_date = {
        point["date"]: point.get("body_weight_kg") for point in weight_points
    }
    all_dates = sorted(set(one_rm_by_date) | set(weight_by_date))
    return [
        {
            "date": day,
            "one_rm_kg": one_rm_by_date.get(day),
            "body_weight_kg": weight_by_date.get(day),
        }
        for day in all_dates
    ]


def recovery_series(
    metric_rows: list[Any],
    set_rows: list[Any],
    *,
    one_rm_points: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    metrics = _rows_to_frame(
        metric_rows,
        ["metric_date", "body_weight_kg", "calories_kcal", "sleep_hours"],
    )
    sets = _rows_to_frame(
        set_rows,
        [
            "workout_date",
            "id",
            "session_id",
            "exercise_id",
            "set_number",
            "weight_kg",
            "reps",
            "rpe",
            "is_warmup",
            "calculated_1rm",
        ],
    )

    metrics_by_date: dict[date, dict[str, Any]] = {}
    if not metrics.empty:
        for row in metrics.itertuples(index=False):
            day = _as_date(row.metric_date)
            metrics_by_date[day] = {
                "body_weight_kg": _as_float(row.body_weight_kg),
                "calories_kcal": (
                    None if row.calories_kcal is None or pd.isna(row.calories_kcal)
                    else int(row.calories_kcal)
                ),
                "sleep_hours": _as_float(row.sleep_hours),
            }

    volume_by_date: dict[date, Decimal] = {}
    rpe_sum_by_date: dict[date, float] = {}
    rpe_n_by_date: dict[date, int] = {}
    if not sets.empty:
        for row in sets.itertuples(index=False):
            day = _as_date(row.workout_date)
            is_warmup = bool(row.is_warmup)
            if is_warmup and not INCLUDE_WARMUPS_IN_VOLUME:
                continue

            if isinstance(row.weight_kg, Decimal):
                weight = row.weight_kg
            else:
                weight = Decimal(str(row.weight_kg))
            volume_by_date[day] = volume_by_date.get(day, Decimal("0")) + set_volume_kg(
                weight, int(row.reps)
            )

            rpe = _as_float(row.rpe)
            if rpe is not None:
                rpe_sum_by_date[day] = rpe_sum_by_date.get(day, 0.0) + rpe
                rpe_n_by_date[day] = rpe_n_by_date.get(day, 0) + 1

    one_rm_by_date: dict[date, float] = {}
    if one_rm_points:
        for point in one_rm_points:
            value = point.get("one_rm_kg")
            if value is not None:
                one_rm_by_date[point["date"]] = float(value)

    sorted_one_rm_dates = sorted(one_rm_by_date)
    previous_one_rm: dict[date, float | None] = {}
    prev: float | None = None
    for day in sorted_one_rm_dates:
        previous_one_rm[day] = prev
        prev = one_rm_by_date[day]

    all_dates = sorted(
        set(metrics_by_date)
        | set(volume_by_date)
        | set(rpe_n_by_date)
        | set(one_rm_by_date)
    )

    result: list[dict[str, Any]] = []
    for day in all_dates:
        metric = metrics_by_date.get(day, {})
        rpe_n = rpe_n_by_date.get(day, 0)
        rpe_avg = (rpe_sum_by_date[day] / rpe_n) if rpe_n else None
        volume = volume_by_date.get(day)
        current_one_rm = one_rm_by_date.get(day)
        prior = previous_one_rm.get(day)
        one_rm_delta = None
        if current_one_rm is not None and prior is not None:
            one_rm_delta = current_one_rm - prior

        result.append(
            {
                "date": day,
                "sleep_hours": metric.get("sleep_hours"),
                "calories_kcal": metric.get("calories_kcal"),
                "body_weight_kg": metric.get("body_weight_kg"),
                "volume_kg": _as_float(volume) if volume is not None else None,
                "rpe_avg": rpe_avg,
                "rpe_n": rpe_n,
                "one_rm_kg": current_one_rm,
                "one_rm_delta": one_rm_delta,
            }
        )

    return result
