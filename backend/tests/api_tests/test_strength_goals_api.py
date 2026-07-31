def _create_exercise(client, name: str = "Bench Press") -> int:
    response = client.post(
        "/api/v1/exercises",
        json={"name": name, "muscle_group": "Chest"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _add_set(
    client,
    *,
    exercise_id: int,
    workout_date: str,
    weight_kg: str,
    reps: int,
) -> None:
    session = client.post(
        "/api/v1/sessions",
        json={"workout_date": workout_date, "split_type": "PUSH"},
    )
    assert session.status_code == 201
    created = client.post(
        f"/api/v1/sessions/{session.json()['id']}/sets",
        json={
            "exercise_id": exercise_id,
            "set_number": 1,
            "weight_kg": weight_kg,
            "reps": reps,
            "is_warmup": False,
        },
    )
    assert created.status_code == 201


def test_create_and_list_strength_goal(client) -> None:
    exercise_id = _create_exercise(client)
    created = client.post(
        "/api/v1/strength-goals",
        json={
            "exercise_id": exercise_id,
            "target_1rm_kg": "140.00",
            "target_date": "2026-12-01",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "ACTIVE"
    assert payload["target_1rm_kg"] == "140.00"
    assert payload["target_date"] == "2026-12-01"
    assert "forecast" not in payload
    assert "predicted" not in payload

    listed = client.get(
        "/api/v1/strength-goals",
        params={"exercise_id": exercise_id, "status": "ACTIVE"},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_one_active_goal_per_exercise_archives_previous(client) -> None:
    exercise_id = _create_exercise(client, "Squat")
    first = client.post(
        "/api/v1/strength-goals",
        json={"exercise_id": exercise_id, "target_1rm_kg": "150"},
    ).json()
    second = client.post(
        "/api/v1/strength-goals",
        json={"exercise_id": exercise_id, "target_1rm_kg": "160"},
    ).json()
    assert second["status"] == "ACTIVE"

    previous = client.get(f"/api/v1/strength-goals/{first['id']}")
    assert previous.status_code == 200
    assert previous.json()["status"] == "ARCHIVED"

    actives = client.get(
        "/api/v1/strength-goals",
        params={"exercise_id": exercise_id, "status": "ACTIVE"},
    ).json()
    assert len(actives) == 1
    assert actives[0]["id"] == second["id"]


def test_goal_auto_achieved_from_history(client) -> None:
    exercise_id = _create_exercise(client, "Deadlift")
    _add_set(
        client,
        exercise_id=exercise_id,
        workout_date="2026-07-01",
        weight_kg="100",
        reps=5,
    )
    created = client.post(
        "/api/v1/strength-goals",
        json={"exercise_id": exercise_id, "target_1rm_kg": "116"},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "ACHIEVED"


def test_goal_stays_active_until_target_reached(client) -> None:
    exercise_id = _create_exercise(client, "OHP")
    created = client.post(
        "/api/v1/strength-goals",
        json={"exercise_id": exercise_id, "target_1rm_kg": "130"},
    ).json()
    assert created["status"] == "ACTIVE"

    _add_set(
        client,
        exercise_id=exercise_id,
        workout_date="2026-07-02",
        weight_kg="100",
        reps=5,
    )
    still_active = client.get(f"/api/v1/strength-goals/{created['id']}")
    assert still_active.json()["status"] == "ACTIVE"

    _add_set(
        client,
        exercise_id=exercise_id,
        workout_date="2026-07-03",
        weight_kg="120",
        reps=5,
    )
    achieved = client.get(f"/api/v1/strength-goals/{created['id']}")
    assert achieved.json()["status"] == "ACHIEVED"


def test_archive_and_update_target_date(client) -> None:
    exercise_id = _create_exercise(client, "Row")
    created = client.post(
        "/api/v1/strength-goals",
        json={
            "exercise_id": exercise_id,
            "target_1rm_kg": "110",
            "target_date": "2026-10-01",
        },
    ).json()
    archived = client.patch(
        f"/api/v1/strength-goals/{created['id']}",
        json={"status": "ARCHIVED", "target_date": None},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"
    assert archived.json()["target_date"] is None


def test_missing_goal_returns_404(client) -> None:
    response = client.get("/api/v1/strength-goals/99999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_goal_rejects_unknown_exercise(client) -> None:
    response = client.post(
        "/api/v1/strength-goals",
        json={"exercise_id": 99999, "target_1rm_kg": "100"},
    )
    assert response.status_code == 404
