from pathlib import Path

from backend.app.core.config import get_settings


def ensure_data_directories() -> None:
    settings = get_settings()

    Path("data").mkdir(parents=True, exist_ok=True)
    Path(settings.model_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.backup_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.export_dir).mkdir(parents=True, exist_ok=True)
