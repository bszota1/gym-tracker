from __future__ import annotations

from typing import Any


class ApiClientError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        details: list[Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or []
        self.cause = cause
        super().__init__(message)

    def user_message(self) -> str:
        return self.message


class ApiConnectionError(ApiClientError):
    def user_message(self) -> str:
        return "Nie można połączyć się z API. Uruchom backend i spróbuj ponownie."


class ApiTimeoutError(ApiClientError):
    def user_message(self) -> str:
        return "Przekroczono czas oczekiwania na odpowiedź API. Spróbuj ponownie."


class ApiValidationError(ApiClientError):
    def user_message(self) -> str:
        if self.details:
            return f"Niepoprawne dane: {self.message}"
        return self.message or "Niepoprawne dane formularza."


class ApiNotFoundError(ApiClientError):
    def user_message(self) -> str:
        return self.message or "Nie znaleziono zasobu."


class ApiConflictError(ApiClientError):
    def user_message(self) -> str:
        return self.message or "Konflikt danych (np. duplikat lub zasób zależny)."


class ApiServerError(ApiClientError):
    def user_message(self) -> str:
        return "Wystąpił błąd serwera. Spróbuj ponownie później."
