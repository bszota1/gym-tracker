from __future__ import annotations

import logging
import os
import time
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
from api_errors import (
    ApiClientError,
    ApiConflictError,
    ApiConnectionError,
    ApiNotFoundError,
    ApiServerError,
    ApiTimeoutError,
    ApiValidationError,
)

DEFAULT_TIMEOUT = 10.0
_SAFE_READ_RETRIES = 2
_SAFE_READ_RETRY_DELAY_SECONDS = 0.3

logger = logging.getLogger(__name__)


def get_api_root() -> str:
    host = os.getenv("GYM_API_HOST", "127.0.0.1")
    port = os.getenv("GYM_API_PORT", "8000")
    return f"http://{host}:{port}"


def get_api_base_url() -> str:
    return os.getenv("GYM_API_BASE_URL", "http://127.0.0.1:8000/api/v1")


def _parse_error_payload(response: httpx.Response) -> tuple[str, str | None, list[Any]]:
    try:
        payload = response.json()
    except ValueError:
        return response.text or "Request failed", None, []

    if isinstance(payload, dict) and "error" in payload and isinstance(payload["error"], dict):
        error = payload["error"]
        message = str(error.get("message") or "Request failed")
        code = error.get("code")
        details = error.get("details") or []
        return message, str(code) if code is not None else None, list(details)

    if isinstance(payload, dict) and "detail" in payload:
        detail = payload["detail"]
        if isinstance(detail, str):
            return detail, None, []
        if isinstance(detail, list):
            return "Validation failed", "VALIDATION_ERROR", detail
        return str(detail), None, []

    return "Request failed", None, []


def _raise_for_status(response: httpx.Response) -> None:
    if response.is_success or response.status_code == 204:
        return

    message, code, details = _parse_error_payload(response)
    status = response.status_code

    if status == 404:
        raise ApiNotFoundError(message, status_code=status, code=code, details=details)
    if status == 409:
        raise ApiConflictError(message, status_code=status, code=code, details=details)
    if status == 422:
        raise ApiValidationError(message, status_code=status, code=code, details=details)
    if status >= 500:
        raise ApiServerError(message, status_code=status, code=code, details=details)

    raise ApiClientError(message, status_code=status, code=code, details=details)


def _request(
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    url = f"{get_api_base_url().rstrip('/')}/{path.lstrip('/')}"
    method_upper = method.upper()
    attempts = 1 + (_SAFE_READ_RETRIES if method_upper == "GET" else 0)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = httpx.request(
                method_upper,
                url,
                json=json,
                params=params,
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            last_error = ApiTimeoutError("API request timed out", cause=exc)
            logger.warning("API timeout %s %s (attempt %s)", method_upper, url, attempt)
        except httpx.TransportError as exc:
            last_error = ApiConnectionError("API connection failed", cause=exc)
            logger.warning("API connection error %s %s (attempt %s)", method_upper, url, attempt)
        else:
            if response.status_code == 204:
                return None
            try:
                _raise_for_status(response)
            except ApiServerError as exc:
                if method_upper != "GET" or attempt >= attempts:
                    raise
                last_error = exc
                logger.warning(
                    "Retryable API error %s %s (attempt %s): %s",
                    method_upper,
                    url,
                    attempt,
                    exc,
                )
            else:
                if not response.content:
                    return None
                return response.json()

        if attempt < attempts:
            time.sleep(_SAFE_READ_RETRY_DELAY_SECONDS)

    assert last_error is not None
    raise last_error


def _drop_none(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _as_date_str(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return value


def _as_json_number(value: Decimal | float | int | str | None) -> float | int | str | None:
    if isinstance(value, Decimal):
        return float(value)
    return value


def list_exercises(is_active: bool | None = None) -> list[dict[str, Any]]:
    params = {"is_active": is_active} if is_active is not None else None
    return _request("GET", "/exercises", params=params)


def create_exercise(name: str, muscle_group: str | None = None) -> dict[str, Any]:
    return _request(
        "POST",
        "/exercises",
        json={"name": name, "muscle_group": muscle_group},
    )


def update_exercise(
    exercise_id: int,
    *,
    name: str | None = None,
    muscle_group: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    return _request(
        "PATCH",
        f"/exercises/{exercise_id}",
        json=_drop_none(
            {
                "name": name,
                "muscle_group": muscle_group,
                "is_active": is_active,
            }
        ),
    )


def get_daily_metric(metric_date: date | str) -> dict[str, Any]:
    return _request("GET", f"/daily-metrics/{_as_date_str(metric_date)}")


def list_daily_metrics(
    date_from: date | str | None = None,
    date_to: date | str | None = None,
) -> list[dict[str, Any]]:
    params = _drop_none(
        {
            "date_from": _as_date_str(date_from) if date_from is not None else None,
            "date_to": _as_date_str(date_to) if date_to is not None else None,
        }
    )
    return _request("GET", "/daily-metrics", params=params or None)


def create_daily_metric(
    metric_date: date | str,
    *,
    body_weight_kg: Decimal | float | None = None,
    calories_kcal: int | None = None,
    sleep_hours: Decimal | float | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return _request(
        "POST",
        "/daily-metrics",
        json={
            "metric_date": _as_date_str(metric_date),
            "body_weight_kg": _as_json_number(body_weight_kg),
            "calories_kcal": calories_kcal,
            "sleep_hours": _as_json_number(sleep_hours),
            "notes": notes,
        },
    )


def update_daily_metric(
    metric_date: date | str,
    *,
    body_weight_kg: Decimal | float | None = None,
    calories_kcal: int | None = None,
    sleep_hours: Decimal | float | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return _request(
        "PATCH",
        f"/daily-metrics/{_as_date_str(metric_date)}",
        json=_drop_none(
            {
                "body_weight_kg": _as_json_number(body_weight_kg),
                "calories_kcal": calories_kcal,
                "sleep_hours": _as_json_number(sleep_hours),
                "notes": notes,
            }
        ),
    )


def delete_daily_metric(metric_date: date | str) -> None:
    _request("DELETE", f"/daily-metrics/{_as_date_str(metric_date)}")


def list_sessions(
    date_from: date | str | None = None,
    date_to: date | str | None = None,
    split_type: str | None = None,
) -> list[dict[str, Any]]:
    params = _drop_none(
        {
            "date_from": _as_date_str(date_from) if date_from is not None else None,
            "date_to": _as_date_str(date_to) if date_to is not None else None,
            "split_type": split_type,
        }
    )
    return _request("GET", "/sessions", params=params or None)


def create_session(
    workout_date: date | str,
    split_type: str,
    notes: str | None = None,
) -> dict[str, Any]:
    return _request(
        "POST",
        "/sessions",
        json={
            "workout_date": _as_date_str(workout_date),
            "split_type": split_type,
            "notes": notes,
        },
    )


def get_session(session_id: int) -> dict[str, Any]:
    return _request("GET", f"/sessions/{session_id}")


def update_session(
    session_id: int,
    *,
    workout_date: date | str | None = None,
    split_type: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return _request(
        "PATCH",
        f"/sessions/{session_id}",
        json=_drop_none(
            {
                "workout_date": (_as_date_str(workout_date) if workout_date is not None else None),
                "split_type": split_type,
                "notes": notes,
            }
        ),
    )


def delete_session(session_id: int) -> None:
    _request("DELETE", f"/sessions/{session_id}")


def list_session_sets(session_id: int) -> list[dict[str, Any]]:
    return _request("GET", f"/sessions/{session_id}/sets")


def create_set(
    session_id: int,
    *,
    exercise_id: int,
    set_number: int,
    weight_kg: Decimal | float,
    reps: int,
    rpe: Decimal | float | None = None,
    is_warmup: bool = False,
) -> dict[str, Any]:
    return _request(
        "POST",
        f"/sessions/{session_id}/sets",
        json={
            "exercise_id": exercise_id,
            "set_number": set_number,
            "weight_kg": _as_json_number(weight_kg),
            "reps": reps,
            "rpe": _as_json_number(rpe),
            "is_warmup": is_warmup,
        },
    )


def get_set(set_id: int) -> dict[str, Any]:
    return _request("GET", f"/sets/{set_id}")


def update_set(
    set_id: int,
    *,
    exercise_id: int | None = None,
    set_number: int | None = None,
    weight_kg: Decimal | float | None = None,
    reps: int | None = None,
    rpe: Decimal | float | None = None,
    is_warmup: bool | None = None,
) -> dict[str, Any]:
    return _request(
        "PATCH",
        f"/sets/{set_id}",
        json=_drop_none(
            {
                "exercise_id": exercise_id,
                "set_number": set_number,
                "weight_kg": _as_json_number(weight_kg),
                "reps": reps,
                "rpe": _as_json_number(rpe),
                "is_warmup": is_warmup,
            }
        ),
    )


def delete_set(set_id: int) -> None:
    _request("DELETE", f"/sets/{set_id}")


def check_health(timeout_seconds: float = 5.0) -> tuple[bool, str]:
    url = f"{get_api_root()}/health"
    try:
        response = httpx.get(url, timeout=timeout_seconds)
        if response.status_code == 200:
            return True, f"API OK ({url})"
        return False, f"API returned {response.status_code} ({url})"
    except httpx.HTTPError as exc:
        return False, f"API unavailable ({url}): {exc.__class__.__name__}"
