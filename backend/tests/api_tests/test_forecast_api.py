from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, timedelta

from backend.app.db.models.model_runs import ModelRun
from backend.app.ml.artifacts import save_prophet_artifact
from backend.app.ml.forecast_validation import ForecastSeries
from backend.app.ml.model_types import (
    ERROR_INSUFFICIENT_DATA,
    ERROR_NO_MODEL,
    MODEL_RUN_STATUS_SUCCESS,
    MODEL_TYPE_PROPHET_ONE_RM,
)
from backend.app.ml.pipeline_contract import FEATURE_PIPELINE_VERSION
from backend.app.ml.prophet_train import fit_prophet


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


def _seed_rising_history(client, exercise_id: int, *, count: int = 10) -> list[dict]:
    start = date(2026, 1, 1)
    rows: list[dict] = []
    for index in range(count):
        day = start + timedelta(days=5 * index)
        weight = 90 + index
        _add_set(
            client,
            exercise_id=exercise_id,
            workout_date=day.isoformat(),
            weight_kg=str(weight),
            reps=5,
        )
        # Epley approx stored by API; for fingerprint we rebuild from observations later
        rows.append({"date": day, "one_rm_kg": float(weight) * (1 + 5 / 30)})
    return rows


def test_forecast_insufficient_data(client) -> None:
    exercise_id = _create_exercise(client, "Empty Lift")
    goal = client.post(
        "/api/v1/strength-goals",
        json={"exercise_id": exercise_id, "target_1rm_kg": "150"},
    ).json()
    response = client.get(
        "/api/v1/forecasts/strength",
        params={"exercise_id": exercise_id, "goal_id": goal["id"]},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == ERROR_INSUFFICIENT_DATA


def test_forecast_no_model(client) -> None:
    exercise_id = _create_exercise(client, "No Model Lift")
    _seed_rising_history(client, exercise_id, count=10)
    goal = client.post(
        "/api/v1/strength-goals",
        json={"exercise_id": exercise_id, "target_1rm_kg": "200"},
    ).json()
    assert goal["status"] == "ACTIVE"
    response = client.get(
        "/api/v1/forecasts/strength",
        params={"exercise_id": exercise_id, "goal_id": goal["id"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == ERROR_NO_MODEL


def test_forecast_achieved_without_model(client) -> None:
    exercise_id = _create_exercise(client, "Achieved Lift")
    _add_set(
        client,
        exercise_id=exercise_id,
        workout_date="2026-07-01",
        weight_kg="100",
        reps=5,
    )
    goal = client.post(
        "/api/v1/strength-goals",
        json={"exercise_id": exercise_id, "target_1rm_kg": "100"},
    ).json()
    assert goal["status"] == "ACHIEVED"
    response = client.get(
        "/api/v1/forecasts/strength",
        params={"exercise_id": exercise_id, "goal_id": goal["id"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ACHIEVED"
    assert payload["reason"] == "already_achieved"
    assert payload["model_run_id"] is None
    assert payload["feature_pipeline_version"] == FEATURE_PIPELINE_VERSION


def test_forecast_with_saved_model_does_not_retrain(client) -> None:
    exercise_id = _create_exercise(client, "Prophet Lift")
    _seed_rising_history(client, exercise_id, count=10)
    goal = client.post(
        "/api/v1/strength-goals",
        json={"exercise_id": exercise_id, "target_1rm_kg": "200"},
    ).json()

    start = date(2026, 1, 1)
    series = ForecastSeries(
        dates=tuple(start + timedelta(days=5 * i) for i in range(10)),
        values=tuple(float(90 + i) * (1 + 5 / 30) for i in range(10)),
    )
    model = fit_prophet(series)
    artifact_name = f"prophet_one_rm_ex{exercise_id}.joblib"
    save_prophet_artifact(model, artifact_name)

    async def insert_run() -> int:
        async with client.session_factory() as session:
            run = ModelRun(
                model_type=MODEL_TYPE_PROPHET_ONE_RM,
                exercise_id=exercise_id,
                trained_at=datetime.now(UTC),
                data_fingerprint="seed-fingerprint",
                sample_count=10,
                metrics_json=json.dumps({"mae": 1.2, "baseline_mae": 2.0, "status": "ACCEPTED"}),
                artifact_path=artifact_name,
                status=MODEL_RUN_STATUS_SUCCESS,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)
            return int(run.id)

    run_id = asyncio.run(insert_run())

    first = client.get(
        "/api/v1/forecasts/strength",
        params={"exercise_id": exercise_id, "goal_id": goal["id"]},
    )
    assert first.status_code == 200
    payload = first.json()
    assert payload["model_run_id"] == run_id
    assert payload["status"] in {"PREDICTED", "UNAVAILABLE"}
    assert payload["sample_count"] == 10
    assert payload["freshness"] in {"FRESH", "STALE_DATA", "STALE_AGE"}
    assert "mae" in payload["metrics"]
    assert payload["warnings"] is not None

    second = client.get(
        "/api/v1/forecasts/strength",
        params={"exercise_id": exercise_id, "goal_id": goal["id"]},
    )
    assert second.status_code == 200
    assert second.json()["model_run_id"] == run_id

    async def count_runs() -> int:
        from sqlalchemy import func, select

        async with client.session_factory() as session:
            result = await session.execute(select(func.count()).select_from(ModelRun))
            return int(result.scalar_one())

    assert asyncio.run(count_runs()) == 1
