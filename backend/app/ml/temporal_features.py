from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from backend.app.ml.pipeline_contract import (
    LONG_ROLLING_OBSERVATIONS,
    SHORT_ROLLING_OBSERVATIONS,
)


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


def _nullable_int(value: Any) -> int | None:
    number = _nullable_float(value)
    if number is None:
        return None
    return int(number)


def add_temporal_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    frame = pd.DataFrame.from_records(rows)
    frame["date"] = pd.to_datetime(frame["date"].map(_as_date))
    frame = frame.sort_values("date", kind="mergesort").reset_index(drop=True)

    one_rm = frame["one_rm_kg"].astype(float)
    volume = frame["volume_kg"].astype(float)

    frame["days_since_prev_session"] = frame["date"].diff().dt.days
    frame["one_rm_delta"] = one_rm.diff()
    frame["prev_volume_kg"] = volume.shift(1)
    frame["one_rm_roll_7"] = one_rm.rolling(
        window=SHORT_ROLLING_OBSERVATIONS,
        min_periods=1,
    ).mean()
    frame["one_rm_roll_28"] = one_rm.rolling(
        window=LONG_ROLLING_OBSERVATIONS,
        min_periods=1,
    ).mean()

    enriched: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        enriched.append(
            {
                **row,
                "date": _as_date(row["date"]),
                "days_since_prev_session": _nullable_int(row["days_since_prev_session"]),
                "one_rm_delta": _nullable_float(row["one_rm_delta"]),
                "prev_volume_kg": _nullable_float(row["prev_volume_kg"]),
                "one_rm_roll_7": _nullable_float(row["one_rm_roll_7"]),
                "one_rm_roll_28": _nullable_float(row["one_rm_roll_28"]),
            }
        )
    return enriched
