from backend.app.core.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.log_level == "INFO"


def test_get_settings_returns_settings() -> None:
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert "sqlite" in settings.database_url
