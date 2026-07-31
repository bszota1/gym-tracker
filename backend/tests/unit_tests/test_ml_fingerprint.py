from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.app.ml.fingerprint import compute_dataset_fingerprint
from backend.app.ml.temporal_features import add_temporal_features


def _base_row(
    day: date,
    one_rm: float,
    *,
    set_id: int = 1,
    session_id: int = 1,
    volume: float = 400.0,
) -> dict:
    return {
        "date": day,
        "one_rm_kg": one_rm,
        "weight_kg": 90.0,
        "reps": 5,
        "rpe": 8.0,
        "session_id": session_id,
        "set_id": set_id,
        "exercise_id": 5,
        "volume_kg": volume,
        "body_weight_kg": None,
        "sleep_hours": None,
        "calories_kcal": None,
        "body_weight_missing": True,
        "sleep_missing": True,
        "calories_missing": True,
    }


def test_fingerprint_is_stable_for_same_data() -> None:
    rows = add_temporal_features(
        [
            _base_row(date(2026, 3, 1), 100.0, set_id=1),
            _base_row(date(2026, 3, 3), 102.0, set_id=2, volume=410.0),
        ]
    )
    shuffled = [dict(rows[1]), dict(rows[0])]
    shuffled[0]["one_rm_kg"] = Decimal("102.0")
    first = compute_dataset_fingerprint(rows, exercise_id=5)
    second = compute_dataset_fingerprint(shuffled, exercise_id=5)
    assert first == second
    assert len(first) == 64


def test_fingerprint_changes_when_record_or_version_changes() -> None:
    rows = add_temporal_features(
        [
            _base_row(date(2026, 3, 1), 100.0),
            _base_row(date(2026, 3, 3), 102.0, set_id=2),
        ]
    )
    base = compute_dataset_fingerprint(rows, exercise_id=5)

    changed = [dict(row) for row in rows]
    changed[1]["one_rm_kg"] = 103.0
    assert compute_dataset_fingerprint(changed, exercise_id=5) != base

    assert (
        compute_dataset_fingerprint(
            rows,
            exercise_id=5,
            feature_pipeline_version="2",
        )
        != base
    )
    assert compute_dataset_fingerprint(rows, exercise_id=9) != base
