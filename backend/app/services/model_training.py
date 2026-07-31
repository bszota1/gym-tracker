from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import partial
from typing import Any

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AppError, NotFoundError
from backend.app.ml.anomaly_alerts import (
    DROP_ALERT_THRESHOLD_VERSION,
    NEGATIVE_DROP_PCT_THRESHOLD,
    assess_points_for_drop_alerts,
)
from backend.app.ml.anomaly_features import build_anomaly_feature_rows
from backend.app.ml.anomaly_severity import enrich_drop_alert
from backend.app.ml.artifact_lifecycle import ArtifactLifecycleService
from backend.app.ml.dataset import FeatureDatasetBuilder
from backend.app.ml.forecast_readiness import assess_forecast_readiness
from backend.app.ml.forecast_validation import build_forecast_series
from backend.app.ml.freshness import assess_model_freshness
from backend.app.ml.isolation_forest import (
    MIN_SESSIONS_FOR_ISOLATION_FOREST,
    score_anomaly_points,
    train_isolation_forest,
)
from backend.app.ml.model_types import (
    ERROR_INSUFFICIENT_DATA,
    ERROR_NO_MODEL,
    MODEL_TYPE_ISOLATION_FOREST,
    MODEL_TYPE_PROPHET_ONE_RM,
)
from backend.app.ml.pipeline_contract import FEATURE_PIPELINE_VERSION, PipelineInput
from backend.app.ml.prophet_train import fit_prophet
from backend.app.ml.prophet_validate import (
    PROPHET_STATUS_ACCEPTED,
    evaluate_prophet,
)
from backend.app.repositories.exercises import ExerciseRepository
from backend.app.repositories.model_runs import ModelRunRepository


class ModelTrainingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._exercises = ExerciseRepository(session)
        self._runs = ModelRunRepository(session)
        self._datasets = FeatureDatasetBuilder(session)
        self._lifecycle = ArtifactLifecycleService(session)

    async def get_status(self, *, exercise_id: int, model_type: str) -> dict[str, Any]:
        exercise = await self._exercises.get_by_id(exercise_id)
        if exercise is None:
            raise NotFoundError("Exercise not found")

        pipeline = await self._datasets.build_base(PipelineInput(exercise_id=exercise_id))
        current_fingerprint = pipeline.meta.fingerprint or ""
        run = await self._runs.get_latest_success(
            model_type=model_type,
            exercise_id=exercise_id,
        )
        if run is None:
            return {
                "exercise_id": exercise_id,
                "model_type": model_type,
                "has_model": False,
                "freshness": None,
                "warnings": ["no_model"],
                "model_run_id": None,
                "trained_at": None,
                "sample_count": pipeline.meta.sample_count,
                "current_fingerprint": current_fingerprint,
                "data_fingerprint": None,
                "feature_pipeline_version": FEATURE_PIPELINE_VERSION,
                "deleted": False,
            }

        freshness = assess_model_freshness(
            trained_fingerprint=run.data_fingerprint,
            current_fingerprint=current_fingerprint,
            trained_at=run.trained_at,
        )
        return {
            "exercise_id": exercise_id,
            "model_type": model_type,
            "has_model": True,
            "freshness": freshness.status,
            "warnings": list(freshness.warnings),
            "model_run_id": run.id,
            "trained_at": run.trained_at,
            "sample_count": run.sample_count,
            "current_fingerprint": current_fingerprint,
            "data_fingerprint": run.data_fingerprint,
            "feature_pipeline_version": FEATURE_PIPELINE_VERSION,
            "age_days": freshness.age_days,
            "max_age_days": freshness.max_age_days,
            "deleted": False,
            "metrics": _parse_metrics(run.metrics_json),
        }

    async def train_forecast(self, *, exercise_id: int) -> dict[str, Any]:
        await self._require_exercise(exercise_id)
        pipeline = await self._datasets.build_base(PipelineInput(exercise_id=exercise_id))
        readiness = assess_forecast_readiness(pipeline.rows)
        if not readiness.can_forecast:
            raise AppError(
                "Insufficient data for forecasting",
                code=ERROR_INSUFFICIENT_DATA,
                status_code=422,
                details=[{"reasons": list(readiness.reasons)}],
            )

        series = build_forecast_series(pipeline.rows)
        fingerprint = pipeline.meta.fingerprint or ""

        def _train() -> tuple[Any, Any]:
            validation = evaluate_prophet(series)
            model = fit_prophet(series)
            return validation, model

        validation, model = await anyio.to_thread.run_sync(_train)
        metrics = {
            "status": validation.status,
            "mae": validation.mae,
            "mape": validation.mape,
            "baseline_mae": validation.baseline_mae,
            "beats_baseline": validation.beats_baseline,
            "feature_pipeline_version": FEATURE_PIPELINE_VERSION,
        }
        if validation.status != PROPHET_STATUS_ACCEPTED:
            failed = await self._lifecycle.record_failure(
                model_type=MODEL_TYPE_PROPHET_ONE_RM,
                exercise_id=exercise_id,
                data_fingerprint=fingerprint,
                sample_count=series.size,
                metrics=metrics,
            )
            return {
                "accepted": False,
                "model_run_id": failed.id,
                "status": failed.status,
                "metrics": metrics,
                "kept_previous_model": True,
            }

        published = await self._lifecycle.publish_success(
            model_type=MODEL_TYPE_PROPHET_ONE_RM,
            exercise_id=exercise_id,
            model_obj=model,
            data_fingerprint=fingerprint,
            sample_count=series.size,
            metrics=metrics,
            trained_at=datetime.now(UTC),
        )
        return {
            "accepted": True,
            "model_run_id": published.model_run.id,
            "status": published.model_run.status,
            "artifact_path": published.artifact_path,
            "metrics": metrics,
            "kept_previous_model": False,
        }

    async def train_anomalies(self, *, exercise_id: int) -> dict[str, Any]:
        await self._require_exercise(exercise_id)
        pipeline = await self._datasets.build_base(PipelineInput(exercise_id=exercise_id))
        feature_rows = build_anomaly_feature_rows(pipeline.rows)
        if len(feature_rows) < MIN_SESSIONS_FOR_ISOLATION_FOREST:
            raise AppError(
                "Insufficient data for anomaly model",
                code=ERROR_INSUFFICIENT_DATA,
                status_code=422,
                details=[{"min_sessions": MIN_SESSIONS_FOR_ISOLATION_FOREST}],
            )

        fingerprint = pipeline.meta.fingerprint or ""

        def _train() -> Any:
            return train_isolation_forest(feature_rows)

        try:
            trained = await anyio.to_thread.run_sync(_train)
        except Exception as exc:
            failed = await self._lifecycle.record_failure(
                model_type=MODEL_TYPE_ISOLATION_FOREST,
                exercise_id=exercise_id,
                data_fingerprint=fingerprint,
                sample_count=len(feature_rows),
                metrics={"error": str(exc)},
            )
            return {
                "accepted": False,
                "model_run_id": failed.id,
                "status": failed.status,
                "kept_previous_model": True,
                "metrics": {"error": str(exc)},
            }

        metrics = {
            "n_samples": trained.n_samples,
            "contamination": trained.contamination,
            "random_state": trained.random_state,
            "score_distribution": {
                "min": trained.score_distribution.min_score,
                "max": trained.score_distribution.max_score,
                "mean": trained.score_distribution.mean_score,
                "p25": trained.score_distribution.p25,
                "p50": trained.score_distribution.p50,
                "p75": trained.score_distribution.p75,
            },
            "threshold_version": DROP_ALERT_THRESHOLD_VERSION,
            "negative_drop_threshold_pct": NEGATIVE_DROP_PCT_THRESHOLD,
            "feature_pipeline_version": FEATURE_PIPELINE_VERSION,
        }
        published = await self._lifecycle.publish_success(
            model_type=MODEL_TYPE_ISOLATION_FOREST,
            exercise_id=exercise_id,
            model_obj=trained.pipeline,
            data_fingerprint=fingerprint,
            sample_count=trained.n_samples,
            metrics=metrics,
            trained_at=datetime.now(UTC),
        )
        return {
            "accepted": True,
            "model_run_id": published.model_run.id,
            "status": published.model_run.status,
            "artifact_path": published.artifact_path,
            "metrics": metrics,
            "kept_previous_model": False,
        }

    async def list_anomalies(self, *, exercise_id: int) -> dict[str, Any]:
        await self._require_exercise(exercise_id)
        pipeline = await self._datasets.build_base(PipelineInput(exercise_id=exercise_id))
        if not pipeline.rows:
            raise AppError(
                "Insufficient data for anomalies",
                code=ERROR_INSUFFICIENT_DATA,
                status_code=422,
            )

        run = await self._runs.get_latest_success(
            model_type=MODEL_TYPE_ISOLATION_FOREST,
            exercise_id=exercise_id,
        )
        if run is None:
            raise AppError(
                "No trained anomaly model available",
                code=ERROR_NO_MODEL,
                status_code=404,
            )

        feature_rows = build_anomaly_feature_rows(pipeline.rows)
        model = await anyio.to_thread.run_sync(
            partial(self._lifecycle.load_pipeline, run.artifact_path)
        )
        scored = await anyio.to_thread.run_sync(
            partial(score_anomaly_points, model, feature_rows)
        )
        alerts = assess_points_for_drop_alerts(scored)
        one_rm_by_date = {row["date"]: float(row["one_rm_kg"]) for row in pipeline.rows}
        points: list[dict[str, Any]] = []
        for (feature_row, is_outlier, score), alert in zip(scored, alerts, strict=True):
            enriched = enrich_drop_alert(alert, feature_row)
            points.append(
                {
                    "date": feature_row.date,
                    "one_rm_kg": one_rm_by_date.get(feature_row.date, feature_row.one_rm_kg),
                    "is_outlier": is_outlier,
                    "anomaly_score": score,
                    "alert": enriched.alert,
                    "severity": enriched.severity,
                    "reason": enriched.reason,
                    "message": enriched.message,
                    "pct_dev_roll_7": enriched.pct_dev_roll_7,
                    "facts": list(enriched.context.facts),
                    "assumptions": list(enriched.context.assumptions),
                    "sleep_hours": enriched.context.sleep_hours,
                    "rpe": enriched.context.rpe,
                    "prev_volume_kg": enriched.context.prev_volume_kg,
                }
            )

        freshness = assess_model_freshness(
            trained_fingerprint=run.data_fingerprint,
            current_fingerprint=pipeline.meta.fingerprint or "",
            trained_at=run.trained_at,
        )
        return {
            "exercise_id": exercise_id,
            "model_run_id": run.id,
            "trained_at": run.trained_at,
            "freshness": freshness.status,
            "warnings": list(freshness.warnings),
            "sample_count": len(points),
            "deleted": False,
            "threshold_version": DROP_ALERT_THRESHOLD_VERSION,
            "points": points,
        }

    async def _require_exercise(self, exercise_id: int) -> None:
        exercise = await self._exercises.get_by_id(exercise_id)
        if exercise is None:
            raise NotFoundError("Exercise not found")


def _parse_metrics(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
