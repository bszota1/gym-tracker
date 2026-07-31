from __future__ import annotations

import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AppError
from backend.app.data_protection.backup import BackupService
from backend.app.data_protection.export import ExportService
from backend.app.data_protection.import_ import ImportService
from backend.app.data_protection.paths import export_dir
from backend.app.db.session import get_db
from backend.app.schemas.data_protection import (
    BackupCreateResponse,
    BackupInfo,
    ExportCreateResponse,
    ExportInfo,
    ImportApplyResponse,
    ImportDryRunResponse,
)

router = APIRouter(tags=["data-protection"])

_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


def _safe_join(directory: Path, filename: str) -> Path:
    if not _SAFE_NAME.match(filename):
        raise AppError(
            "Invalid filename",
            code="VALIDATION_ERROR",
            status_code=422,
        )
    path = (directory / filename).resolve()
    if path.parent != directory.resolve():
        raise AppError(
            "Invalid filename",
            code="VALIDATION_ERROR",
            status_code=422,
        )
    return path


@router.post(
    "/api/v1/backups",
    response_model=BackupCreateResponse,
    status_code=201,
)
async def create_backup() -> BackupCreateResponse:
    result = BackupService().create_backup()
    return BackupCreateResponse.model_validate(result)


@router.get(
    "/api/v1/backups",
    response_model=list[BackupInfo],
)
async def list_backups() -> list[BackupInfo]:
    return [BackupInfo.model_validate(item) for item in BackupService().list_backups()]


@router.post(
    "/api/v1/exports",
    response_model=ExportCreateResponse,
    status_code=201,
)
async def create_export(
    db: AsyncSession = Depends(get_db),
) -> ExportCreateResponse:
    result = await ExportService(db).create_export()
    return ExportCreateResponse.model_validate(result)


@router.get(
    "/api/v1/exports",
    response_model=list[ExportInfo],
)
async def list_exports(
    db: AsyncSession = Depends(get_db),
) -> list[ExportInfo]:
    return [ExportInfo.model_validate(item) for item in ExportService(db).list_exports()]


@router.post(
    "/api/v1/imports/dry-run",
    response_model=ImportDryRunResponse,
)
async def dry_run_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ImportDryRunResponse:
    archive_path = await _save_upload(file)
    try:
        result = await ImportService(db).dry_run(archive_path)
        return ImportDryRunResponse.model_validate(result)
    finally:
        archive_path.unlink(missing_ok=True)


@router.post(
    "/api/v1/imports",
    response_model=ImportApplyResponse,
)
async def apply_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ImportApplyResponse:
    archive_path = await _save_upload(file)
    try:
        result = await ImportService(db).apply(archive_path)
        return ImportApplyResponse.model_validate(result)
    finally:
        archive_path.unlink(missing_ok=True)


@router.post(
    "/api/v1/imports/from-export/{filename}",
    response_model=ImportApplyResponse,
)
async def apply_import_from_export(
    filename: str,
    db: AsyncSession = Depends(get_db),
) -> ImportApplyResponse:
    archive_path = _safe_join(export_dir(), filename)
    if not archive_path.exists():
        raise AppError("Export archive not found", code="NOT_FOUND", status_code=404)
    result = await ImportService(db).apply(archive_path)
    return ImportApplyResponse.model_validate(result)


async def _save_upload(file: UploadFile) -> Path:
    suffix = Path(file.filename or "upload.zip").suffix or ".zip"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        content = await file.read()
        handle.write(content)
        return Path(handle.name)
