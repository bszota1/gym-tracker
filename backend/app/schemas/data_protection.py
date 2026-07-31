from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BackupInfo(BaseModel):
    filename: str
    path: str
    size_bytes: int | None = None
    removed_old_backups: int | None = None


class BackupCreateResponse(BaseModel):
    filename: str
    path: str
    removed_old_backups: int = 0


class ExportCreateResponse(BaseModel):
    filename: str
    path: str
    schema_version: str
    row_counts: dict[str, int]


class ExportInfo(BaseModel):
    filename: str
    path: str
    size_bytes: int


class ImportDryRunResponse(BaseModel):
    ok: bool
    schema_version: str
    tables: dict[str, str]
    row_counts: dict[str, int]
    conflicts: list[dict[str, Any]] = Field(default_factory=list)


class ImportApplyResponse(BaseModel):
    imported: bool
    backup: BackupCreateResponse
    schema_version: str
    row_counts: dict[str, int]
