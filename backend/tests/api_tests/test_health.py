from fastapi.testclient import TestClient

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
