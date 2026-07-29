from backend.app.core.config import get_settings
from pathlib import Path

def ensure_data_directories() -> None:
    settings = get_settings()

    db_path = Path("data")
    db_path.mkdir(parents=True, exist_ok=True)

    Path(settings.model_dir).mkdir(parents=True, exist_ok=True)