from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.domain.one_rm import calculate_1rm
from backend.app.schemas.workout_sets import WorkoutSetCreate
from backend.app.services.exercises import ExerciseService


def test_calculate_1rm_for_single_rep_returns_weight() -> None:
    assert calculate_1rm(Decimal("100"), 1) == Decimal("100.00")


def test_calculate_1rm_uses_epley_for_multiple_reps() -> None:
    assert calculate_1rm(Decimal("100"), 5) == Decimal("116.67")


def test_calculate_1rm_rounds_half_up() -> None:
    assert calculate_1rm(Decimal("95"), 3) == Decimal("104.50")


def test_calculate_1rm_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="reps must be positive"):
        calculate_1rm(Decimal("100"), 0)
    with pytest.raises(ValueError, match="weight_kg must be non-negative"):
        calculate_1rm(Decimal("-1"), 5)


def test_rpe_half_step_is_valid() -> None:
    payload = WorkoutSetCreate(
        exercise_id=1,
        set_number=1,
        weight_kg=Decimal("100"),
        reps=5,
        rpe=Decimal("7.5"),
    )
    assert payload.rpe == Decimal("7.5")


def test_rpe_invalid_step_is_rejected() -> None:
    with pytest.raises(ValidationError):
        WorkoutSetCreate(
            exercise_id=1,
            set_number=1,
            weight_kg=Decimal("100"),
            reps=5,
            rpe=Decimal("7.3"),
        )


def test_normalize_exercise_name_collapses_whitespace() -> None:
    service = ExerciseService(session=None)  # type: ignore[arg-type]
    assert service.normalize_exercise_name("  Bench   Press  ") == "Bench Press"
