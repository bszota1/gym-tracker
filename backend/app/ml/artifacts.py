from __future__ import annotations

from pathlib import Path

import joblib
from prophet import Prophet

from backend.app.core.config import get_settings
from backend.app.core.exceptions import AppError
from backend.app.ml.model_types import ERROR_INFERENCE


def model_dir() -> Path:
    return Path(get_settings().model_dir)


def resolve_trusted_artifact_path(artifact_path: str, *, root: Path | None = None) -> Path:
    base = (root or model_dir()).resolve()
    path = Path(artifact_path)
    if not path.is_absolute():
        path = base / path
    resolved = path.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise AppError(
            "Artifact path is outside trusted model directory",
            code=ERROR_INFERENCE,
            status_code=500,
        ) from exc
    return resolved


def save_prophet_artifact(model: Prophet, relative_name: str, *, root: Path | None = None) -> Path:
    base = root or model_dir()
    base.mkdir(parents=True, exist_ok=True)
    path = resolve_trusted_artifact_path(relative_name, root=base)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(model, tmp)
    tmp.replace(path)
    return path


def load_prophet_artifact(artifact_path: str, *, root: Path | None = None) -> Prophet:
    path = resolve_trusted_artifact_path(artifact_path, root=root)
    if not path.is_file():
        raise AppError(
            "Model artifact file not found",
            code=ERROR_INFERENCE,
            status_code=500,
        )
    try:
        model = joblib.load(path)
    except Exception as exc:
        raise AppError(
            "Failed to load model artifact",
            code=ERROR_INFERENCE,
            status_code=500,
            details=[str(exc)],
        ) from exc
    if not isinstance(model, Prophet):
        raise AppError(
            "Loaded artifact is not a Prophet model",
            code=ERROR_INFERENCE,
            status_code=500,
        )
    return model
