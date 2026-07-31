from __future__ import annotations

from pathlib import Path

from backend.app.core.config import get_settings


def resolve_sqlite_path(database_url: str | None = None) -> Path:
    url = database_url if database_url is not None else get_settings().database_url
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        raise ValueError(f"Unsupported database URL for file backup: {url}")
    raw = url.removeprefix(prefix)
    return Path(raw).expanduser().resolve()


def backup_dir() -> Path:
    path = Path(get_settings().backup_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def export_dir() -> Path:
    path = Path(get_settings().export_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()
