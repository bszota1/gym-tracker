from __future__ import annotations

from backend.app.ml.model_types import MODEL_TYPE_PROPHET_ONE_RM


def test_model_status_no_model_not_deleted(client) -> None:
    exercise_id = client.post(
        "/api/v1/exercises",
        json={"name": "Status Lift"},
    ).json()["id"]
    response = client.get(
        "/api/v1/models/status",
        params={
            "exercise_id": exercise_id,
            "model_type": MODEL_TYPE_PROPHET_ONE_RM,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["has_model"] is False
    assert payload["deleted"] is False
    assert payload["freshness"] is None
    assert "no_model" in payload["warnings"]


def test_weight_suggestion_insufficient(client) -> None:
    exercise_id = client.post(
        "/api/v1/exercises",
        json={"name": "Weight Lift"},
    ).json()["id"]
    response = client.get(
        "/api/v1/weight-suggestions",
        params={"exercise_id": exercise_id},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_DATA"
