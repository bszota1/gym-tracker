from __future__ import annotations

from datetime import date

from backend.app.ml.temporal_features import add_temporal_features


def _row(
    day: date,
    one_rm: float,
    volume: float,
) -> dict:
    return {
        "date": day,
        "one_rm_kg": one_rm,
        "weight_kg": one_rm * 0.9,
        "reps": 5,
        "rpe": 8.0,
        "session_id": 1,
        "set_id": 1,
        "exercise_id": 5,
        "volume_kg": volume,
        "body_weight_kg": None,
        "sleep_hours": None,
        "calories_kcal": None,
        "body_weight_missing": True,
        "sleep_missing": True,
        "calories_missing": True,
    }


def test_temporal_features_first_rows_and_lags() -> None:
    rows = [
        _row(date(2026, 1, 10), 100.0, 400.0),
        _row(date(2026, 1, 12), 110.0, 440.0),
        _row(date(2026, 1, 19), 105.0, 420.0),
    ]
    result = add_temporal_features(rows)

    assert result[0]["days_since_prev_session"] is None
    assert result[0]["one_rm_delta"] is None
    assert result[0]["prev_volume_kg"] is None
    assert result[0]["one_rm_roll_7"] == 100.0
    assert result[0]["one_rm_roll_28"] == 100.0

    assert result[1]["days_since_prev_session"] == 2
    assert result[1]["one_rm_delta"] == 10.0
    assert result[1]["prev_volume_kg"] == 400.0
    assert result[1]["one_rm_roll_7"] == 105.0
    assert result[1]["one_rm_roll_28"] == 105.0

    assert result[2]["days_since_prev_session"] == 7
    assert result[2]["one_rm_delta"] == -5.0
    assert result[2]["prev_volume_kg"] == 440.0
    assert result[2]["one_rm_roll_7"] == 105.0
    assert result[2]["one_rm_roll_28"] == 105.0


def test_temporal_features_ignore_future_values() -> None:
    rows = [
        _row(date(2026, 2, 1), 100.0, 300.0),
        _row(date(2026, 2, 3), 102.0, 310.0),
        _row(date(2026, 2, 5), 200.0, 900.0),
    ]
    shuffled = [rows[2], rows[0], rows[1]]
    result = add_temporal_features(shuffled)

    assert [item["date"] for item in result] == [
        date(2026, 2, 1),
        date(2026, 2, 3),
        date(2026, 2, 5),
    ]
    assert result[0]["one_rm_roll_7"] == 100.0
    assert result[0]["prev_volume_kg"] is None
    assert result[1]["one_rm_roll_7"] == 101.0
    assert result[1]["prev_volume_kg"] == 300.0
    assert result[1]["one_rm_delta"] == 2.0
    assert result[2]["one_rm_roll_7"] == (100.0 + 102.0 + 200.0) / 3
    assert result[2]["prev_volume_kg"] == 310.0
