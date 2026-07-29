from typing import Any

class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: list[Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)

class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: list[Any] | None = None) -> None:
        super().__init__(
            message,
            code="NOT_FOUND",
            status_code=404,
            details=details,
        )

class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", details: list[Any] | None = None) -> None:
        super().__init__(
            message,
            code="CONFLICT",
            status_code=409,
            details=details,
        )