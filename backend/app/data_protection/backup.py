from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from backend.app.data_protection.constants import BACKUP_RETENTION_COUNT, EXPORT_SCHEMA_VERSION
from backend.app.data_protection.paths import backup_dir, resolve_sqlite_path


class BackupService:
    def __init__(
        self,
        *,
        db_path: Path | None = None,
        target_dir: Path | None = None,
        retention: int = BACKUP_RETENTION_COUNT,
    ) -> None:
        self._db_path = db_path or resolve_sqlite_path()
        self._target_dir = target_dir or backup_dir()
        self._retention = retention

    def create_backup(self) -> dict[str, str | int]:
        self._target_dir.mkdir(parents=True, exist_ok=True)
        if not self._db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self._db_path}")

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"gym_tracker_{stamp}_v{EXPORT_SCHEMA_VERSION}.db"
        destination = self._target_dir / filename

        source = sqlite3.connect(self._db_path)
        try:
            destination_conn = sqlite3.connect(destination)
            try:
                source.backup(destination_conn)
            finally:
                destination_conn.close()
        finally:
            source.close()

        removed = self._enforce_retention()
        return {
            "filename": filename,
            "path": str(destination),
            "removed_old_backups": removed,
        }

    def list_backups(self) -> list[dict[str, str | int]]:
        self._target_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(
            self._target_dir.glob("gym_tracker_*.db"),
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

    def _enforce_retention(self) -> int:
        files = sorted(
            self._target_dir.glob("gym_tracker_*.db"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        removed = 0
        for obsolete in files[self._retention :]:
            obsolete.unlink(missing_ok=True)
            removed += 1
        return removed
