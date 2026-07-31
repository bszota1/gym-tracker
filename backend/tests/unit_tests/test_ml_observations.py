from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app.ml.metrics_join import join_daily_metrics
from backend.app.ml.observations import select_daily_strength_observations


def test_select_daily_max_excludes_warmup_and_high_reps() -> None:
    rows = [
        (date(2026, 1, 1), 1, 10, 5, 1, Decimal("100"), 5, Decimal("8"), False, Decimal("116.67")),
        (date(2026, 1, 1), 2, 10, 5, 2, Decimal("60"), 5, None, True, Decimal("70")),
        (date(2026, 1, 1), 3, 10, 5, 3, Decimal("40"), 20, None, False, Decimal("66.67")),
        (date(2026, 1, 2), 4, 11, 5, 1, Decimal("105"), 3, Decimal("9"), False, Decimal("115.50")),
        (date(2026, 1, 2), 5, 11, 99, 1, Decimal("200"), 1, None, False, Decimal("200")),
    ]
    result = select_daily_strength_observations(rows, exercise_id=5)
    assert len(result) == 2
    assert result[0]["date"] == date(2026, 1, 1)
    assert result[0]["one_rm_kg"] == 116.67
    assert result[0]["set_id"] == 1
    assert result[0]["volume_kg"] == 100 * 5 + 40 * 20
    assert result[1]["one_rm_kg"] == 115.50
    assert all(item["exercise_id"] == 5 for item in result)


def test_join_metrics_keeps_nulls_without_forward_fill() -> None:
    observations = [
        {
            "date": date(2026, 1, 1),
            "one_rm_kg": 100.0,
            "weight_kg": 90.0,
            "reps": 5,
            "rpe": 8.0,
            "session_id": 1,
            "set_id": 1,
            "exercise_id": 5,
            "volume_kg": 450.0,
        },
        {
            "date": date(2026, 1, 3),
            "one_rm_kg": 102.0,
            "weight_kg": 92.0,
            "reps": 4,
            "rpe": None,
            "session_id": 2,
            "set_id": 2,
            "exercise_id": 5,
            "volume_kg": 368.0,
        },
    ]
    metrics = [
        (date(2026, 1, 1), Decimal("80.0"), 2500, Decimal("7.5")),
    ]
    joined = join_daily_metrics(observations, metrics)
    assert joined[0]["body_weight_kg"] == 80.0
    assert joined[0]["sleep_missing"] is False
    assert joined[1]["body_weight_kg"] is None
    assert joined[1]["sleep_hours"] is None
    assert joined[1]["body_weight_missing"] is True
    assert joined[1]["sleep_missing"] is True
    assert joined[1]["calories_missing"] is True
    assert joined[0]["one_rm_roll_7"] is None
