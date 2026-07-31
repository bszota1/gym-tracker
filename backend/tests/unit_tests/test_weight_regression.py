from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.app.ml.weight_regression import (
    MIN_WEIGHT_REGRESSION_SAMPLES,
    clamp_to_relative_band,
    round_down_to_plate,
    suggest_next_weight,
)


def _rows(count: int) -> list[dict]:
    start = date(2026, 1, 1)
    rows: list[dict] = []
    for index in range(count):
        rows.append(
            {
                "date": start + timedelta(days=4 * index),
                "weight_kg": 80.0 + 0.5 * index,
                "days_since_prev_session": 4 if index else None,
                "prev_volume_kg": 400.0 + index,
                "sleep_hours": 7.0,
                "body_weight_kg": 80.0,
                "rpe": 8.0,
                "one_rm_delta": 0.5 if index else None,
            }
        )
    for row in rows:
        if row["days_since_prev_session"] is None:
            row["days_since_prev_session"] = 3
        if row["one_rm_delta"] is None:
            row["one_rm_delta"] = 0.0
        if row["prev_volume_kg"] is None:
            row["prev_volume_kg"] = 400.0
    return rows


def test_plate_rounding_and_clamp() -> None:
    assert round_down_to_plate(101.0) == 100.0
    assert clamp_to_relative_band(130.0, center=100.0) == pytest.approx(110.0)
    assert clamp_to_relative_band(85.0, center=100.0) == pytest.approx(90.0)


def test_suggest_requires_minimum_samples() -> None:
    result = suggest_next_weight(_rows(MIN_WEIGHT_REGRESSION_SAMPLES - 1))
    assert result.status == "INSUFFICIENT_DATA"
    assert result.suggested_weight_kg is None
    assert result.is_suggestion_only is True


def test_suggest_returns_clamped_suggestion() -> None:
    result = suggest_next_weight(_rows(MIN_WEIGHT_REGRESSION_SAMPLES + 2))
    assert result.status in {"SUGGESTED", "BASELINE_PREFERRED"}
    assert result.suggested_weight_kg is not None
    assert result.last_successful_weight_kg is not None
    low = result.last_successful_weight_kg * 0.9
    high = result.last_successful_weight_kg * 1.1
    assert low <= result.suggested_weight_kg <= high
    assert result.is_suggestion_only is True
