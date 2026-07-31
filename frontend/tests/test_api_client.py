from __future__ import annotations

from typing import Any
from unittest.mock import patch

import api_client
import httpx
import pytest
from api_errors import (
    ApiConflictError,
    ApiConnectionError,
    ApiNotFoundError,
    ApiTimeoutError,
    ApiValidationError,
)


def _response(
    status_code: int,
    payload: dict[str, Any] | None = None,
    *,
    content: bytes | None = None,
) -> httpx.Response:
    request = httpx.Request("GET", "http://test/api/v1/example")
    if content is not None:
        return httpx.Response(status_code, content=content, request=request)
    return httpx.Response(status_code, json=payload, request=request)


def test_get_maps_404() -> None:
    response = _response(
        404,
        {"error": {"message": "missing", "code": "NOT_FOUND"}},
    )
    with (
        patch("api_client.httpx.request", return_value=response),
        pytest.raises(ApiNotFoundError),
    ):
        api_client._request("GET", "/missing")


def test_post_maps_409() -> None:
    response = _response(
        409,
        {"error": {"message": "duplicate", "code": "CONFLICT"}},
    )
    with (
        patch("api_client.httpx.request", return_value=response),
        pytest.raises(ApiConflictError),
    ):
        api_client._request("POST", "/exercises", json={"name": "Squat"})


def test_post_maps_422() -> None:
    response = _response(
        422,
        {"detail": [{"loc": ["body", "rpe"], "msg": "bad"}]},
    )
    with (
        patch("api_client.httpx.request", return_value=response),
        pytest.raises(ApiValidationError),
    ):
        api_client._request("POST", "/sets", json={})


def test_timeout_maps_to_api_timeout() -> None:
    with (
        patch(
            "api_client.httpx.request",
            side_effect=httpx.TimeoutException("slow"),
        ),
        pytest.raises(ApiTimeoutError),
    ):
        api_client._request("POST", "/sessions", json={})


def test_connection_error_maps() -> None:
    with (
        patch(
            "api_client.httpx.request",
            side_effect=httpx.ConnectError("down"),
        ),
        pytest.raises(ApiConnectionError),
    ):
        api_client._request("GET", "/exercises")


def test_get_retries_on_timeout_then_succeeds() -> None:
    ok = _response(200, [{"id": 1}])
    side_effects: list[Any] = [httpx.TimeoutException("slow"), ok]
    with (
        patch("api_client.httpx.request", side_effect=side_effects) as mocked,
        patch("api_client.time.sleep"),
    ):
        result = api_client._request("GET", "/exercises")
    assert result == [{"id": 1}]
    assert mocked.call_count == 2


def test_post_does_not_retry_on_timeout() -> None:
    with (
        patch(
            "api_client.httpx.request",
            side_effect=httpx.TimeoutException("slow"),
        ) as mocked,
        pytest.raises(ApiTimeoutError),
    ):
        api_client._request("POST", "/sessions", json={})
    assert mocked.call_count == 1


def test_list_session_sets_builds_path() -> None:
    with patch("api_client._request", return_value=[]) as mocked:
        api_client.list_session_sets(42)
    mocked.assert_called_once_with("GET", "/sessions/42/sets")


def test_create_set_payload() -> None:
    with patch("api_client._request", return_value={"id": 1}) as mocked:
        api_client.create_set(
            7,
            exercise_id=3,
            set_number=1,
            weight_kg=100,
            reps=5,
            rpe=8,
            is_warmup=False,
        )
    mocked.assert_called_once()
    args, kwargs = mocked.call_args
    assert args[0] == "POST"
    assert args[1] == "/sessions/7/sets"
    assert kwargs["json"]["exercise_id"] == 3
    assert "calculated_1rm" not in kwargs["json"]
