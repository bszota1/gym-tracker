from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any

from sklearn.model_selection import TimeSeriesSplit

FORECAST_CV_SPLITS = 3


@dataclass(frozen=True, slots=True)
class ForecastSeries:
    dates: tuple[date, ...]
    values: tuple[float, ...]

    @property
    def size(self) -> int:
        return len(self.dates)


@dataclass(frozen=True, slots=True)
class ForecastFold:
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def build_forecast_series(rows: list[dict[str, Any]]) -> ForecastSeries:
    by_day: dict[date, float] = {}
    for row in rows:
        day = _as_date(row["date"])
        one_rm = float(row["one_rm_kg"])
        previous = by_day.get(day)
        if previous is None or one_rm > previous:
            by_day[day] = one_rm
    days = sorted(by_day)
    return ForecastSeries(
        dates=tuple(days),
        values=tuple(by_day[day] for day in days),
    )


def iter_time_series_folds(
    n_samples: int,
    *,
    n_splits: int = FORECAST_CV_SPLITS,
) -> Iterator[ForecastFold]:
    if n_samples <= n_splits:
        raise ValueError(
            f"Need more than {n_splits} samples for time-series CV, got {n_samples}"
        )
    splitter = TimeSeriesSplit(n_splits=n_splits)
    indices = list(range(n_samples))
    for train_idx, test_idx in splitter.split(indices):
        yield ForecastFold(
            train_indices=tuple(int(i) for i in train_idx),
            test_indices=tuple(int(i) for i in test_idx),
        )
