from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import backend.app.main as main_module
from backend.app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_debug_not_found_uses_common_error_format() -> None:
    client = TestClient(create_app())
    response = client.get("/debug/not-found")
    assert response.status_code == 404
    payload = response.json()
    assert payload == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Daily metrics not found",
            "details": [],
        }
    }


@pytest.mark.usefixtures("tmp_path")
def test_readiness_returns_ready_when_checks_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FakeResult:
        def __init__(self, row: tuple[str] | None) -> None:
            self._row = row

        def first(self) -> tuple[str] | None:
            return self._row

    class FakeConnection:
        async def execute(self, statement: object) -> FakeResult:
            sql = str(statement)
            if "SELECT 1" in sql:
                return FakeResult(None)
            if "SELECT version_num FROM alembic_version" in sql:
                return FakeResult(("head-rev",))
            raise AssertionError(f"Unexpected query: {sql}")

    class FakeConnectCtx:
        async def __aenter__(self) -> FakeConnection:
            return FakeConnection()

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    class FakeEngine:
        def connect(self) -> FakeConnectCtx:
            return FakeConnectCtx()

    class FakeScriptDirectory:
        def get_current_head(self) -> str:
            return "head-rev"

    monkeypatch.setattr(main_module, "engine", FakeEngine())
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: SimpleNamespace(model_dir=str(tmp_path), api_host="127.0.0.1", api_port=8000),
    )
    monkeypatch.setattr(
        main_module.ScriptDirectory,
        "from_config",
        lambda _cfg: FakeScriptDirectory(),
    )

    client = TestClient(create_app())
    response = client.get("/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "migrations": "ok", "model_dir": "ok"},
    }


def test_readiness_returns_503_when_database_check_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeConnectCtx:
        async def __aenter__(self) -> None:
            raise RuntimeError("db unavailable")

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    class FakeEngine:
        def connect(self) -> FakeConnectCtx:
            return FakeConnectCtx()

    monkeypatch.setattr(main_module, "engine", FakeEngine())

    client = TestClient(create_app())
    response = client.get("/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "status": "not_ready",
            "checks": {"database": "down", "migrations": "outdated", "model_dir": "missing"},
        }
    }
