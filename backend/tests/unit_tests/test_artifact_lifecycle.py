from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from sklearn.pipeline import Pipeline

from backend.app.core.config import get_settings
from backend.app.core.exceptions import AppError
from backend.app.ml.artifact_lifecycle import (
    ArtifactLifecycleService,
    build_artifact_filename,
)
from backend.app.ml.artifacts import resolve_trusted_artifact_path
from backend.app.ml.isolation_forest import build_isolation_forest_pipeline
from backend.app.ml.model_types import (
    MODEL_RUN_STATUS_FAILED,
    MODEL_RUN_STATUS_SUCCESS,
    MODEL_TYPE_ISOLATION_FOREST,
)


def test_artifact_filename_contains_type_exercise_time_version() -> None:
    name = build_artifact_filename(
        model_type=MODEL_TYPE_ISOLATION_FOREST,
        exercise_id=7,
        trained_at=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
        pipeline_version="1",
    )
    assert MODEL_TYPE_ISOLATION_FOREST in name
    assert "ex7" in name
    assert "20260731T120000Z" in name
    assert "pipe1" in name
    assert name.endswith(".joblib")


def test_rejects_absolute_and_escaping_paths(tmp_path: Path) -> None:
    try:
        resolve_trusted_artifact_path(str(tmp_path / "x.joblib"), root=tmp_path)
        raise AssertionError("expected AppError")
    except AppError as exc:
        assert exc.code == "INFERENCE_ERROR"

    try:
        resolve_trusted_artifact_path("../escape.joblib", root=tmp_path)
        raise AssertionError("expected AppError")
    except AppError as exc:
        assert exc.code == "INFERENCE_ERROR"


def test_publish_success_and_keep_last_good_on_failure(client) -> None:
    root = Path(get_settings().model_dir)
    exercise_id = client.post(
        "/api/v1/exercises",
        json={"name": "Lifecycle Lift"},
    ).json()["id"]

    async def run() -> None:
        async with client.session_factory() as session:
            lifecycle = ArtifactLifecycleService(session, root=root)
            pipe = build_isolation_forest_pipeline()
            first = await lifecycle.publish_success(
                model_type=MODEL_TYPE_ISOLATION_FOREST,
                exercise_id=exercise_id,
                model_obj=pipe,
                data_fingerprint="fp-1",
                sample_count=8,
                metrics={"ok": True},
                trained_at=datetime(2026, 7, 1, tzinfo=UTC),
            )
            assert first.model_run.status == MODEL_RUN_STATUS_SUCCESS
            assert (root / first.artifact_path).is_file()

            failed = await lifecycle.record_failure(
                model_type=MODEL_TYPE_ISOLATION_FOREST,
                exercise_id=exercise_id,
                data_fingerprint="fp-2",
                sample_count=8,
                metrics={"error": "eval_failed"},
                trained_at=datetime(2026, 7, 2, tzinfo=UTC),
            )
            assert failed.status == MODEL_RUN_STATUS_FAILED
            assert failed.artifact_path == first.artifact_path

            latest = await lifecycle._runs.get_latest_success(
                model_type=MODEL_TYPE_ISOLATION_FOREST,
                exercise_id=exercise_id,
            )
            assert latest is not None
            assert latest.id == first.model_run.id
            assert (root / latest.artifact_path).is_file()

            loaded = lifecycle.load_pipeline(latest.artifact_path)
            assert isinstance(loaded, Pipeline)

    asyncio.run(run())
