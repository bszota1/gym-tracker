from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AppError, NotFoundError
from backend.app.ml.dataset import FeatureDatasetBuilder
from backend.app.ml.model_types import ERROR_INSUFFICIENT_DATA
from backend.app.ml.pipeline_contract import PipelineInput
from backend.app.ml.weight_regression import suggest_next_weight
from backend.app.repositories.exercises import ExerciseRepository
from backend.app.schemas.models_ml import WeightSuggestionResponse


class WeightSuggestionService:
    def __init__(self, session: AsyncSession) -> None:
        self._exercises = ExerciseRepository(session)
        self._datasets = FeatureDatasetBuilder(session)

    async def suggest(self, *, exercise_id: int) -> WeightSuggestionResponse:
        exercise = await self._exercises.get_by_id(exercise_id)
        if exercise is None:
            raise NotFoundError("Exercise not found")

        pipeline = await self._datasets.build_base(PipelineInput(exercise_id=exercise_id))
        if not pipeline.rows:
            raise AppError(
                "Insufficient data for weight suggestion",
                code=ERROR_INSUFFICIENT_DATA,
                status_code=422,
            )

        result = suggest_next_weight(pipeline.rows)
        return WeightSuggestionResponse(
            exercise_id=exercise_id,
            status=result.status,  # type: ignore[arg-type]
            suggested_weight_kg=(
                Decimal(str(result.suggested_weight_kg))
                if result.suggested_weight_kg is not None
                else None
            ),
            last_successful_weight_kg=(
                Decimal(str(result.last_successful_weight_kg))
                if result.last_successful_weight_kg is not None
                else None
            ),
            raw_prediction_kg=(
                Decimal(str(round(result.raw_prediction_kg, 2)))
                if result.raw_prediction_kg is not None
                else None
            ),
            clamped=result.clamped,
            rounded_down=result.rounded_down,
            model_mae=result.model_mae,
            baseline_mae=result.baseline_mae,
            beats_baseline=result.beats_baseline,
            sample_count=result.sample_count,
            reason=result.reason,
            is_suggestion_only=True,
            disclaimer=(
                "Suggestion only - not a prescription. Use judgment and available plates."
            ),
        )
