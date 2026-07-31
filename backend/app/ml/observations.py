from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from backend.app.domain.analytics_defs import INCLUDE_WARMUPS_IN_VOLUME, set_volume_kg
from backend.app.ml.pipeline_contract import uses_strength_eligibility

_SET_COLUMNS = [
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


def select_daily_strength_observations(
    set_rows: list[Any],
    *,
    exercise_id: int,
) -> list[dict[str, Any]]:
    df = _rows_to_frame(set_rows, _SET_COLUMNS)
    if df.empty:
        return []

    df = df.loc[df["exercise_id"].astype(int) == int(exercise_id)].copy()
    if df.empty:
        return []

    eligible_mask = [
        uses_strength_eligibility(bool(is_warmup), int(reps))
        for is_warmup, reps in zip(df["is_warmup"], df["reps"], strict=True)
    ]
    eligible = df.loc[eligible_mask].copy()
    if eligible.empty:
        return []

    eligible["calculated_1rm"] = eligible["calculated_1rm"].astype(float)
    eligible = eligible.drop_duplicates(
        subset=["workout_date", "id", "session_id", "set_number"],
        keep="first",
    )

    best_idx = eligible.groupby("workout_date", sort=True)["calculated_1rm"].idxmax()
    daily = eligible.loc[best_idx].sort_values("workout_date").reset_index(drop=True)

    volume_by_date: dict[date, float] = {}
    for row in df.itertuples(index=False):
        day = _as_date(row.workout_date)
        is_warmup = bool(row.is_warmup)
        if is_warmup and not INCLUDE_WARMUPS_IN_VOLUME:
            continue
        weight = row.weight_kg
        if not isinstance(weight, Decimal):
            weight = Decimal(str(weight))
        volume_by_date[day] = volume_by_date.get(day, 0.0) + float(
            set_volume_kg(weight, int(row.reps))
        )

    observations: list[dict[str, Any]] = []
    for row in daily.itertuples(index=False):
        day = _as_date(row.workout_date)
        observations.append(
            {
                "date": day,
                "one_rm_kg": float(row.calculated_1rm),
                "weight_kg": _as_float(row.weight_kg),
                "reps": int(row.reps),
                "rpe": _as_float(row.rpe),
                "session_id": int(row.session_id),
                "set_id": int(row.id),
                "exercise_id": int(row.exercise_id),
                "volume_kg": volume_by_date.get(day),
            }
        )
    return observations
