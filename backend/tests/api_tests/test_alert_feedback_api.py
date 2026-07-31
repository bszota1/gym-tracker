from __future__ import annotations

from backend.app.ml.anomaly_alerts import DROP_ALERT_THRESHOLD_VERSION
from backend.app.ml.model_types import MODEL_TYPE_ISOLATION_FOREST
from backend.app.ml.pipeline_contract import FEATURE_PIPELINE_VERSION


def _exercise(client) -> int:
    return client.post(
        "/api/v1/exercises",
        json={"name": "Feedback Lift"},
    ).json()["id"]


def test_create_feedback_and_summary_does_not_auto_update(client) -> None:
    exercise_id = _exercise(client)
    created = client.post(
        "/api/v1/anomaly-alerts/feedback",
        json={
            "exercise_id": exercise_id,
            "alert_date": "2026-07-10",
            "model_run_id": None,
            "model_type": MODEL_TYPE_ISOLATION_FOREST,
            "rating": "USEFUL",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["rating"] == "USEFUL"
    assert payload["threshold_version"] == DROP_ALERT_THRESHOLD_VERSION
    assert payload["feature_pipeline_version"] == FEATURE_PIPELINE_VERSION

    client.post(
        "/api/v1/anomaly-alerts/feedback",
        json={
            "exercise_id": exercise_id,
            "alert_date": "2026-07-11",
            "model_type": MODEL_TYPE_ISOLATION_FOREST,
            "rating": "NOT_USEFUL",
        },
    )

    summary = client.get(
        "/api/v1/anomaly-alerts/feedback/summary",
        params={"exercise_id": exercise_id},
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["total"] == 2
    assert body["useful"] == 1
    assert body["not_useful"] == 1
    assert body["useful_rate"] == 0.5
    assert body["auto_model_update"] is False
    assert body["threshold_version"] == DROP_ALERT_THRESHOLD_VERSION


def test_duplicate_feedback_conflicts(client) -> None:
    exercise_id = _exercise(client)
    payload = {
        "exercise_id": exercise_id,
        "alert_date": "2026-07-12",
        "model_type": MODEL_TYPE_ISOLATION_FOREST,
        "rating": "USEFUL",
    }
    assert client.post("/api/v1/anomaly-alerts/feedback", json=payload).status_code == 201
    duplicate = client.post("/api/v1/anomaly-alerts/feedback", json=payload)
    assert duplicate.status_code == 409
