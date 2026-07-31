from __future__ import annotations

from pathlib import Path


def _seed_journal(client) -> None:
    client.post(
        "/api/v1/exercises",
        json={"name": "Export Press", "muscle_group": "Chest"},
    )
    client.post(
        "/api/v1/daily-metrics",
        json={
            "metric_date": "2026-07-15",
            "body_weight_kg": "81.5",
            "calories_kcal": 2500,
            "sleep_hours": "7.0",
        },
    )
    session = client.post(
        "/api/v1/sessions",
        json={"workout_date": "2026-07-15", "split_type": "PUSH"},
    ).json()
    exercise_id = client.get("/api/v1/exercises").json()[0]["id"]
    client.post(
        f"/api/v1/sessions/{session['id']}/sets",
        json={
            "exercise_id": exercise_id,
            "set_number": 1,
            "weight_kg": "100",
            "reps": 5,
            "is_warmup": False,
        },
    )


def test_backup_endpoint(client) -> None:
    response = client.post("/api/v1/backups")
    assert response.status_code == 201
    payload = response.json()
    assert Path(payload["path"]).exists()

    listed = client.get("/api/v1/backups")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1


def test_export_import_round_trip(client) -> None:
    _seed_journal(client)

    exported = client.post("/api/v1/exports")
    assert exported.status_code == 201
    export_payload = exported.json()
    export_path = Path(export_payload["path"])
    assert export_path.exists()
    assert export_payload["row_counts"]["exercises"] == 1
    assert export_payload["row_counts"]["workout_sets"] == 1

    dry = client.post(
        "/api/v1/imports/dry-run",
        files={"file": (export_path.name, export_path.read_bytes(), "application/zip")},
    )
    assert dry.status_code == 200
    assert dry.json()["ok"] is True

    applied = client.post(
        "/api/v1/imports",
        files={"file": (export_path.name, export_path.read_bytes(), "application/zip")},
    )
    assert applied.status_code == 200
    body = applied.json()
    assert body["imported"] is True
    assert Path(body["backup"]["path"]).exists()

    exercises = client.get("/api/v1/exercises").json()
    assert len(exercises) == 1
    assert exercises[0]["name"] == "Export Press"

    day = client.get("/api/v1/daily-metrics/2026-07-15")
    assert day.status_code == 200
    assert day.json()["body_weight_kg"] == "81.50"


def test_failed_import_does_not_change_data(client) -> None:
    _seed_journal(client)
    before = client.get("/api/v1/exercises").json()

    response = client.post(
        "/api/v1/imports",
        files={"file": ("broken.zip", b"not-a-zip", "application/zip")},
    )
    assert response.status_code == 422

    after = client.get("/api/v1/exercises").json()
    assert after == before
