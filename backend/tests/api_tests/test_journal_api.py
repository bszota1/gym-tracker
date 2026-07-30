from decimal import Decimal


def test_full_journal_workflow_calculates_1rm(client) -> None:
    exercise = client.post(
        "/api/v1/exercises",
        json={"name": "Bench Press", "muscle_group": "Chest"},
    )
    assert exercise.status_code == 201
    exercise_id = exercise.json()["id"]

    session = client.post(
        "/api/v1/sessions",
        json={"workout_date": "2026-07-30", "split_type": "PUSH", "notes": None},
    )
    assert session.status_code == 201
    session_id = session.json()["id"]

    # ensure_day created empty daily metric
    day = client.get("/api/v1/daily-metrics/2026-07-30")
    assert day.status_code == 200

    created_set = client.post(
        f"/api/v1/sessions/{session_id}/sets",
        json={
            "exercise_id": exercise_id,
            "set_number": 1,
            "weight_kg": "100",
            "reps": 5,
            "rpe": "8.0",
            "is_warmup": False,
        },
    )
    assert created_set.status_code == 201
    payload = created_set.json()
    assert payload["calculated_1rm"] == "116.67"
    assert "calculated_1rm" not in {
        "exercise_id": exercise_id,
        "set_number": 1,
        "weight_kg": "100",
        "reps": 5,
    }
    set_id = payload["id"]

    patched = client.patch(
        f"/api/v1/sets/{set_id}",
        json={"reps": 1, "weight_kg": "120"},
    )
    assert patched.status_code == 200
    assert patched.json()["calculated_1rm"] == "120.00"


def test_duplicate_exercise_name_returns_409(client) -> None:
    first = client.post("/api/v1/exercises", json={"name": "Squat"})
    assert first.status_code == 201
    duplicate = client.post("/api/v1/exercises", json={"name": "squat"})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "CONFLICT"


def test_archive_exercise_blocks_new_sets(client) -> None:
    exercise = client.post("/api/v1/exercises", json={"name": "Deadlift"}).json()
    session = client.post(
        "/api/v1/sessions",
        json={"workout_date": "2026-07-31", "split_type": "PULL"},
    ).json()

    archive = client.patch(
        f"/api/v1/exercises/{exercise['id']}",
        json={"is_active": False},
    )
    assert archive.status_code == 200
    assert archive.json()["is_active"] is False

    blocked = client.post(
        f"/api/v1/sessions/{session['id']}/sets",
        json={
            "exercise_id": exercise["id"],
            "set_number": 1,
            "weight_kg": "100",
            "reps": 5,
        },
    )
    assert blocked.status_code == 409


def test_delete_day_with_session_returns_409(client) -> None:
    client.post("/api/v1/sessions", json={"workout_date": "2026-08-01", "split_type": "LEGS"})
    response = client.delete("/api/v1/daily-metrics/2026-08-01")
    assert response.status_code == 409


def test_set_validation_rejects_bad_rpe(client) -> None:
    exercise = client.post("/api/v1/exercises", json={"name": "OHP"}).json()
    session = client.post(
        "/api/v1/sessions",
        json={"workout_date": "2026-08-02", "split_type": "PUSH"},
    ).json()
    response = client.post(
        f"/api/v1/sessions/{session['id']}/sets",
        json={
            "exercise_id": exercise["id"],
            "set_number": 1,
            "weight_kg": "40",
            "reps": 8,
            "rpe": "7.3",
        },
    )
    assert response.status_code == 422


def test_missing_set_returns_404(client) -> None:
    response = client.get("/api/v1/sets/99999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_client_cannot_send_calculated_1rm(client) -> None:
    exercise = client.post("/api/v1/exercises", json={"name": "Row"}).json()
    session = client.post(
        "/api/v1/sessions",
        json={"workout_date": "2026-08-03", "split_type": "PULL"},
    ).json()
    response = client.post(
        f"/api/v1/sessions/{session['id']}/sets",
        json={
            "exercise_id": exercise["id"],
            "set_number": 1,
            "weight_kg": "60",
            "reps": 8,
            "calculated_1rm": "999",
        },
    )
    # Extra field ignored by default Pydantic v2, or 422 depending on config.
    # Either way client must not control calculated_1rm.
    if response.status_code == 201:
        assert Decimal(response.json()["calculated_1rm"]) != Decimal("999")
    else:
        assert response.status_code == 422
