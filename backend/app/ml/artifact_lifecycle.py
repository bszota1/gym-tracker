from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prophet import Prophet
from sklearn.pipeline import Pipeline
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AppError
from backend.app.db.models.model_runs import ModelRun
from backend.app.ml.artifacts import (
    load_joblib_artifact,
    model_dir,
    save_joblib_artifact,
)
from backend.app.ml.model_types import (
    ERROR_INFERENCE,
    MODEL_RUN_STATUS_FAILED,
    MODEL_RUN_STATUS_SUCCESS,
)
from backend.app.ml.pipeline_contract import FEATURE_PIPELINE_VERSION
from backend.app.repositories.model_runs import ModelRunRepository


def build_artifact_filename(
    *,
    model_type: str,
    exercise_id: int,
    trained_at: datetime,
    pipeline_version: str = FEATURE_PIPELINE_VERSION,
) -> str:
    stamp = trained_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    safe_type = model_type.replace("/", "_")
    return f"{safe_type}_ex{exercise_id}_{stamp}_pipe{pipeline_version}.joblib"


@dataclass(frozen=True, slots=True)
class PublishResult:
    model_run: ModelRun
    artifact_path: str
    replaced_previous: bool


class ArtifactLifecycleService:
    def __init__(self, session: AsyncSession, *, root: Path | None = None) -> None:
        self._session = session
        self._runs = ModelRunRepository(session)
        self._root = root

    async def publish_success(
        self,
        *,
        model_type: str,
        exercise_id: int,
        model_obj: Any,
        data_fingerprint: str,
        sample_count: int,
        metrics: dict[str, Any],
        trained_at: datetime | None = None,
        pipeline_version: str = FEATURE_PIPELINE_VERSION,
    ) -> PublishResult:
        when = trained_at or datetime.now(UTC)
        previous = await self._runs.get_latest_success(
            model_type=model_type,
            exercise_id=exercise_id,
        )
        filename = build_artifact_filename(
            model_type=model_type,
            exercise_id=exercise_id,
            trained_at=when,
            pipeline_version=pipeline_version,
        )
        save_joblib_artifact(model_obj, filename, root=self._root or model_dir())
        run = ModelRun(
            model_type=model_type,
            exercise_id=exercise_id,
            trained_at=when,
            data_fingerprint=data_fingerprint,
            sample_count=sample_count,
            metrics_json=json.dumps(metrics),
            artifact_path=filename,
            status=MODEL_RUN_STATUS_SUCCESS,
        )
        created = await self._runs.create(run)
        await self._session.commit()
        await self._session.refresh(created)
        return PublishResult(
            model_run=created,
            artifact_path=filename,
            replaced_previous=previous is not None,
        )

    async def record_failure(
        self,
        *,
        model_type: str,
        exercise_id: int,
        data_fingerprint: str,
        sample_count: int,
        metrics: dict[str, Any],
        trained_at: datetime | None = None,
    ) -> ModelRun:
        previous = await self._runs.get_latest_success(
            model_type=model_type,
            exercise_id=exercise_id,
        )
        when = trained_at or datetime.now(UTC)
        artifact_path = previous.artifact_path if previous is not None else ""
        run = ModelRun(
            model_type=model_type,
            exercise_id=exercise_id,
            trained_at=when,
            data_fingerprint=data_fingerprint,
            sample_count=sample_count,
            metrics_json=json.dumps(metrics),
            artifact_path=artifact_path,
            status=MODEL_RUN_STATUS_FAILED,
        )
        created = await self._runs.create(run)
        await self._session.commit()
        await self._session.refresh(created)
        return created

    def load_prophet(self, artifact_path: str) -> Prophet:
        obj = load_joblib_artifact(artifact_path, root=self._root or model_dir())
        if not isinstance(obj, Prophet):
            raise AppError(
                "Loaded artifact is not a Prophet model",
                code=ERROR_INFERENCE,
                status_code=500,
            )
        return obj

    def load_pipeline(self, artifact_path: str) -> Pipeline:
        obj = load_joblib_artifact(artifact_path, root=self._root or model_dir())
        if not isinstance(obj, Pipeline):
            raise AppError(
                "Loaded artifact is not a sklearn Pipeline",
                code=ERROR_INFERENCE,
                status_code=500,
            )
        return obj
