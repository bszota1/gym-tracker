from __future__ import annotations


def test_body_weight_analytics_empty_range(client) -> None:
    response = client.get(
        "/api/v1/analytics/body-weight",
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["points"] == []
    assert payload["trend"] == []
    assert payload["meta"]["semantics_version"] == "1"


def test_analytics_rejects_inverted_date_range(client) -> None:
    response = client.get(
        "/api/v1/analytics/body-weight",
        params={"date_from": "2026-02-01", "date_to": "2026-01-01"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_one_rm_and_overview_endpoints(client) -> None:
    exercise = client.post(
        "/api/v1/exercises",
        json={"name": "Bench Analytics", "muscle_group": "Chest"},
    ).json()
    client.post(
        "/api/v1/daily-metrics",
        json={
            "metric_date": "2026-07-01",
            "body_weight_kg": "82.5",
            "calories_kcal": 2600,
            "sleep_hours": "7.5",
        },
    )
    session = client.post(
        "/api/v1/sessions",
        json={"workout_date": "2026-07-01", "split_type": "PUSH"},
    ).json()
    client.post(
        f"/api/v1/sessions/{session['id']}/sets",
        json={
            "exercise_id": exercise["id"],
            "set_number": 1,
            "weight_kg": "100",
            "reps": 5,
            "rpe": "8.0",
            "is_warmup": False,
        },
    )

    one_rm = client.get(
        "/api/v1/analytics/one-rm",
        params={
            "exercise_id": exercise["id"],
            "date_from": "2026-07-01",
            "date_to": "2026-07-31",
        },
    )
    assert one_rm.status_code == 200
    one_rm_payload = one_rm.json()
    assert len(one_rm_payload["points"]) == 1
    assert one_rm_payload["points"][0]["is_lifetime_pr"] is True

    vs = client.get(
        "/api/v1/analytics/strength-vs-weight",
        params={
            "exercise_id": exercise["id"],
            "date_from": "2026-07-01",
            "date_to": "2026-07-31",
        },
    )
    assert vs.status_code == 200
    assert vs.json()["points"][0]["body_weight_kg"] == 82.5

    recovery = client.get(
        "/api/v1/analytics/recovery",
        params={
            "date_from": "2026-07-01",
            "date_to": "2026-07-31",
            "exercise_id": exercise["id"],
        },
    )
    assert recovery.status_code == 200
    assert recovery.json()["points"][0]["sleep_hours"] == 7.5

    overview = client.get(
        "/api/v1/analytics/overview",
        params={"as_of": "2026-07-01"},
    )
    assert overview.status_code == 200
    overview_payload = overview.json()
    assert overview_payload["body_weight"]["value"] == 82.5
    assert overview_payload["sessions_this_week"]["value"] >= 1
