from __future__ import annotations

import csv
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AppError
from backend.app.data_protection.backup import BackupService
from backend.app.data_protection.constants import (
    DELETE_ORDER,
    EXPORT_SCHEMA_VERSION,
    EXPORT_TABLES,
)


class ImportService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        backup_service: BackupService | None = None,
    ) -> None:
        self._session = session
        self._backup_service = backup_service or BackupService()

    async def dry_run(self, archive_path: Path) -> dict[str, Any]:
        extracted = self._extract(archive_path)
        try:
            manifest = self._read_manifest(extracted)
            self._validate_manifest(manifest, extracted)
            conflicts = await self._collect_conflicts(extracted, manifest)
            return {
                "ok": len(conflicts) == 0,
                "schema_version": manifest["schema_version"],
                "tables": manifest.get("tables", {}),
                "row_counts": {
                    table: self._count_csv_rows(extracted / filename)
                    for table, filename in manifest["tables"].items()
                },
                "conflicts": conflicts,
            }
        finally:
            shutil.rmtree(extracted, ignore_errors=True)

    async def apply(self, archive_path: Path) -> dict[str, Any]:
        report = await self.dry_run(archive_path)
        if not report["ok"]:
            raise AppError(
                "Import validation failed",
                code="VALIDATION_ERROR",
                status_code=422,
                details=report["conflicts"],
            )

        backup = self._backup_service.create_backup()
        extracted = self._extract(archive_path)
        try:
            manifest = self._read_manifest(extracted)
            await self._replace_data(extracted, manifest)
            await self._session.commit()
            return {
                "imported": True,
                "backup": backup,
                "schema_version": manifest["schema_version"],
                "row_counts": report["row_counts"],
            }
        except Exception:
            await self._session.rollback()
            raise
        finally:
            shutil.rmtree(extracted, ignore_errors=True)

    def _extract(self, archive_path: Path) -> Path:
        if not archive_path.exists():
            raise AppError(
                "Export archive not found",
                code="NOT_FOUND",
                status_code=404,
            )
        temp_dir = Path(tempfile.mkdtemp(prefix="gym_import_"))
        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive.extractall(temp_dir)
        except zipfile.BadZipFile as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise AppError(
                "Invalid zip archive",
                code="VALIDATION_ERROR",
                status_code=422,
            ) from exc
        return temp_dir

    def _read_manifest(self, extracted: Path) -> dict[str, Any]:
        manifest_path = extracted / "manifest.json"
        if not manifest_path.exists():
            raise AppError(
                "manifest.json missing from archive",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _validate_manifest(self, manifest: dict[str, Any], extracted: Path) -> None:
        version = manifest.get("schema_version")
        if version != EXPORT_SCHEMA_VERSION:
            raise AppError(
                f"Unsupported schema_version: {version}",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        tables = manifest.get("tables")
        if not isinstance(tables, dict):
            raise AppError(
                "manifest.tables must be an object",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        missing = [table for table in EXPORT_TABLES if table not in tables]
        if missing:
            raise AppError(
                f"Missing tables in manifest: {', '.join(missing)}",
                code="VALIDATION_ERROR",
                status_code=422,
            )
        for table, filename in tables.items():
            if table not in EXPORT_TABLES:
                raise AppError(
                    f"Unexpected table in manifest: {table}",
                    code="VALIDATION_ERROR",
                    status_code=422,
                )
            if not (extracted / str(filename)).exists():
                raise AppError(
                    f"Missing CSV file: {filename}",
                    code="VALIDATION_ERROR",
                    status_code=422,
                )

    async def _collect_conflicts(
        self,
        extracted: Path,
        manifest: dict[str, Any],
    ) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        for table in EXPORT_TABLES:
            filename = manifest["tables"][table]
            path = extracted / filename
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    conflicts.append(
                        {"table": table, "message": "CSV has no header"}
                    )
                    continue
                for index, row in enumerate(reader, start=2):
                    if table == "exercises" and not (row.get("name") or "").strip():
                        conflicts.append(
                            {
                                "table": table,
                                "row": index,
                                "message": "exercise name is required",
                            }
                        )
                    if table == "workout_sets" and (
                        not row.get("session_id") or not row.get("exercise_id")
                    ):
                        conflicts.append(
                            {
                                "table": table,
                                "row": index,
                                "message": "session_id and exercise_id are required",
                            }
                        )
        return conflicts

    def _count_csv_rows(self, path: Path) -> int:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            return sum(1 for _ in reader)

    async def _replace_data(self, extracted: Path, manifest: dict[str, Any]) -> None:
        await self._session.execute(text("PRAGMA foreign_keys=ON"))
        for table in DELETE_ORDER:
            await self._session.execute(text(f"DELETE FROM {table}"))

        for table in EXPORT_TABLES:
            filename = manifest["tables"][table]
            path = extracted / filename
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                if not rows:
                    continue
                columns = list(reader.fieldnames or [])
                col_list = ", ".join(columns)
                placeholders = ", ".join(f":{column}" for column in columns)
                stmt = text(
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
                )
                payload = []
                for row in rows:
                    cleaned: dict[str, Any] = {}
                    for column in columns:
                        value = row.get(column, "")
                        cleaned[column] = None if value == "" else value
                    payload.append(cleaned)
                await self._session.execute(stmt, payload)
