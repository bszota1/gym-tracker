from __future__ import annotations


def test_list_session_sets_endpoint(client) -> None:
    exercise = client.post(
        "/api/v1/exercises",
        json={"name": "Incline Press", "muscle_group": "Chest"},
    ).json()
    session = client.post(
        "/api/v1/sessions",
        json={"workout_date": "2026-08-10", "split_type": "PUSH"},
    ).json()

    empty = client.get(f"/api/v1/sessions/{session['id']}/sets")
    assert empty.status_code == 200
    assert empty.json() == []

    created = client.post(
        f"/api/v1/sessions/{session['id']}/sets",
        json={
            "exercise_id": exercise["id"],
            "set_number": 1,
            "weight_kg": "80",
            "reps": 8,
            "is_warmup": False,
        },
    )
    assert created.status_code == 201

    listed = client.get(f"/api/v1/sessions/{session['id']}/sets")
    assert listed.status_code == 200
    payload = listed.json()
    assert len(payload) == 1
    assert payload[0]["id"] == created.json()["id"]
    assert payload[0]["calculated_1rm"] == created.json()["calculated_1rm"]


def test_list_session_sets_missing_session_returns_404(client) -> None:
    response = client.get("/api/v1/sessions/99999/sets")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
