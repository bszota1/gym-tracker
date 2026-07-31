from __future__ import annotations

import csv
import json
import zipfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.data_protection.constants import EXPORT_SCHEMA_VERSION, EXPORT_TABLES
from backend.app.data_protection.paths import export_dir


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


class ExportService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        target_dir: Path | None = None,
    ) -> None:
        self._session = session
        self._target_dir = target_dir or export_dir()

    async def create_export(self) -> dict[str, Any]:
        self._target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        zip_name = f"gym_tracker_export_{stamp}_v{EXPORT_SCHEMA_VERSION}.zip"
        zip_path = self._target_dir / zip_name

        table_files: dict[str, str] = {}
        row_counts: dict[str, int] = {}
        temp_dir = self._target_dir / f".tmp_export_{stamp}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            for table in EXPORT_TABLES:
                csv_name = f"{table}.csv"
                csv_path = temp_dir / csv_name
                count = await self._write_table_csv(table, csv_path)
                table_files[table] = csv_name
                row_counts[table] = count

            manifest = {
                "schema_version": EXPORT_SCHEMA_VERSION,
                "exported_at": datetime.now(UTC).isoformat(),
                "tables": table_files,
                "row_counts": row_counts,
            }
            manifest_path = temp_dir / "manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(manifest_path, arcname="manifest.json")
                for csv_name in table_files.values():
                    archive.write(temp_dir / csv_name, arcname=csv_name)
        finally:
            for path in temp_dir.glob("*"):
                path.unlink(missing_ok=True)
            temp_dir.rmdir()

        return {
            "filename": zip_name,
            "path": str(zip_path),
            "schema_version": EXPORT_SCHEMA_VERSION,
            "row_counts": row_counts,
        }

    async def _write_table_csv(self, table: str, path: Path) -> int:
        result = await self._session.execute(text(f"SELECT * FROM {table}"))
        rows = result.mappings().all()
        fieldnames = list(result.keys())
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: _cell(row[key]) for key in fieldnames})
        return len(rows)

    def list_exports(self) -> list[dict[str, str | int]]:
        self._target_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(
            self._target_dir.glob("gym_tracker_export_*.zip"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return [
            {
                "filename": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
            }
            for path in files
        ]
