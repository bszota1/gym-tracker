from __future__ import annotations

from api_errors import (
    ApiConflictError,
    ApiConnectionError,
    ApiNotFoundError,
    ApiServerError,
    ApiTimeoutError,
    ApiValidationError,
)


def test_connection_error_message() -> None:
    assert "połączyć" in ApiConnectionError("x").user_message().lower()


def test_timeout_error_message() -> None:
    assert "czas" in ApiTimeoutError("x").user_message().lower()


def test_not_found_uses_custom_message() -> None:
    assert ApiNotFoundError("Brak dnia").user_message() == "Brak dnia"


def test_conflict_default_message() -> None:
    assert "Konflikt" in ApiConflictError("").user_message()


def test_validation_with_details() -> None:
    message = ApiValidationError("bad", details=[{"loc": ["rpe"]}]).user_message()
    assert message.startswith("Niepoprawne dane")


def test_server_error_message() -> None:
    assert "serwera" in ApiServerError("boom").user_message().lower()
