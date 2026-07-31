from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.app.data_protection.backup import BackupService
from backend.app.data_protection.constants import EXPORT_SCHEMA_VERSION


def test_sqlite_backup_api_creates_restorable_copy(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    backups = tmp_path / "backups"
    backups.mkdir()

    conn = sqlite3.connect(source)
    conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO demo(name) VALUES ('alpha')")
    conn.commit()
    conn.close()

    service = BackupService(db_path=source, target_dir=backups, retention=2)
    first = service.create_backup()
    assert Path(str(first["path"])).exists()
    assert EXPORT_SCHEMA_VERSION in str(first["filename"])

    restored = tmp_path / "restored.db"
    src = sqlite3.connect(str(first["path"]))
    dst = sqlite3.connect(restored)
    src.backup(dst)
    dst.close()
    src.close()

    check = sqlite3.connect(restored)
    row = check.execute("SELECT name FROM demo").fetchone()
    check.close()
    assert row == ("alpha",)

    service.create_backup()
    service.create_backup()
    listed = service.list_backups()
    assert len(listed) == 2
