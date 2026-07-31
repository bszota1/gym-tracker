from __future__ import annotations

import json
from decimal import Decimal
from functools import partial

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AppError, NotFoundError
from backend.app.ml.artifacts import load_prophet_artifact, model_dir
from backend.app.ml.dataset import FeatureDatasetBuilder
from backend.app.ml.forecast_readiness import assess_forecast_readiness
from backend.app.ml.forecast_validation import build_forecast_series
from backend.app.ml.freshness import assess_model_freshness
from backend.app.ml.model_types import (
    ERROR_INFERENCE,
    ERROR_INSUFFICIENT_DATA,
    ERROR_NO_MODEL,
    MODEL_TYPE_PROPHET_ONE_RM,
)
from backend.app.ml.pipeline_contract import FEATURE_PIPELINE_VERSION, PipelineInput
from backend.app.ml.prophet_config import MAX_FORECAST_HORIZON_DAYS
from backend.app.ml.target_date import (
    TARGET_DATE_STATUS_ACHIEVED,
    estimate_target_date_with_model,
)
from backend.app.repositories.exercises import ExerciseRepository
from backend.app.repositories.model_runs import ModelRunRepository
from backend.app.repositories.strength_goals import StrengthGoalRepository
from backend.app.schemas.forecast import ForecastResponse


class ForecastService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._exercises = ExerciseRepository(session)
        self._goals = StrengthGoalRepository(session)
        self._runs = ModelRunRepository(session)
        self._datasets = FeatureDatasetBuilder(session)

    async def get_strength_forecast(
        self,
        *,
        exercise_id: int,
        goal_id: int,
    ) -> ForecastResponse:
        exercise = await self._exercises.get_by_id(exercise_id)
        if exercise is None:
            raise NotFoundError("Exercise not found")

        goal = await self._goals.get_by_id(goal_id)
        if goal is None:
            raise NotFoundError("Strength goal not found")
        if goal.exercise_id != exercise_id:
            raise AppError(
                "Goal does not belong to exercise",
                code="CONFLICT",
                status_code=409,
            )

        pipeline = await self._datasets.build_base(PipelineInput(exercise_id=exercise_id))
        if pipeline.meta.sample_count == 0 or not pipeline.rows:
            raise AppError(
                "Insufficient data for forecasting",
                code=ERROR_INSUFFICIENT_DATA,
                status_code=422,
                details=[{"status": ERROR_INSUFFICIENT_DATA}],
            )

        series = build_forecast_series(pipeline.rows)
        target = float(goal.target_1rm_kg)
        current_best = float(max(series.values))
        current_fingerprint = pipeline.meta.fingerprint or ""

        if current_best >= target:
            return ForecastResponse(
                status="ACHIEVED",
                exercise_id=exercise_id,
                goal_id=goal_id,
                target_1rm_kg=goal.target_1rm_kg,
                current_best_1rm_kg=Decimal(str(current_best)),
                crossing_date=None,
                crossing_date_lower=None,
                crossing_date_upper=None,
                trend="POSITIVE",
                reason="already_achieved",
                sample_count=pipeline.meta.sample_count,
                data_date_from=pipeline.meta.date_from,
                data_date_to=pipeline.meta.date_to,
                feature_pipeline_version=FEATURE_PIPELINE_VERSION,
                model_run_id=None,
                trained_at=None,
                data_fingerprint=None,
                current_fingerprint=current_fingerprint,
                freshness=None,
                warnings=[],
                metrics={},
                horizon_days=0,
            )

        readiness = assess_forecast_readiness(pipeline.rows)
        if not readiness.can_forecast:
            raise AppError(
                "Insufficient data for forecasting",
                code=ERROR_INSUFFICIENT_DATA,
                status_code=422,
                details=[
                    {
                        "status": ERROR_INSUFFICIENT_DATA,
                        "reasons": list(readiness.reasons),
                    }
                ],
            )

        run = await self._runs.get_latest_success(
            model_type=MODEL_TYPE_PROPHET_ONE_RM,
            exercise_id=exercise_id,
        )
        if run is None:
            raise AppError(
                "No trained forecast model available",
                code=ERROR_NO_MODEL,
                status_code=404,
            )

        try:
            model = await anyio.to_thread.run_sync(
                partial(load_prophet_artifact, run.artifact_path, root=model_dir())
            )
            estimate = await anyio.to_thread.run_sync(
                partial(
                    estimate_target_date_with_model,
                    series,
                    target,
                    model,
                    horizon_days=MAX_FORECAST_HORIZON_DAYS,
                )
            )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                "Forecast inference failed",
                code=ERROR_INFERENCE,
                status_code=500,
                details=[str(exc)],
            ) from exc

        freshness = assess_model_freshness(
            trained_fingerprint=run.data_fingerprint,
            current_fingerprint=current_fingerprint,
            trained_at=run.trained_at,
        )
        metrics = _parse_metrics(run.metrics_json)
        warnings = list(freshness.warnings)
        if estimate.status == TARGET_DATE_STATUS_ACHIEVED:
            status = "ACHIEVED"
        elif estimate.status == "PREDICTED":
            status = "PREDICTED"
        else:
            status = "UNAVAILABLE"

        return ForecastResponse(
            status=status,
            exercise_id=exercise_id,
            goal_id=goal_id,
            target_1rm_kg=goal.target_1rm_kg,
            current_best_1rm_kg=Decimal(str(estimate.current_best_1rm_kg)),
            crossing_date=estimate.crossing_date,
            crossing_date_lower=estimate.crossing_date_lower,
            crossing_date_upper=estimate.crossing_date_upper,
            trend=estimate.trend,  # type: ignore[arg-type]
            reason=estimate.reason,
            sample_count=pipeline.meta.sample_count,
            data_date_from=pipeline.meta.date_from,
            data_date_to=pipeline.meta.date_to,
            feature_pipeline_version=FEATURE_PIPELINE_VERSION,
            model_run_id=run.id,
            trained_at=run.trained_at,
            data_fingerprint=run.data_fingerprint,
            current_fingerprint=current_fingerprint,
            freshness=freshness.status,  # type: ignore[arg-type]
            warnings=warnings,
            metrics=metrics,
            horizon_days=estimate.horizon_days,
        )


def _parse_metrics(raw: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}
