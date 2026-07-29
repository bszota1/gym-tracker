from backend.app.core.exceptions import AppError, ConflictError, NotFoundError


def test_not_found_error_defaults() -> None:
    error = NotFoundError("missing")
    assert error.code == "NOT_FOUND"
    assert error.status_code == 404
    assert error.message == "missing"
    assert error.details == []


def test_conflict_error_defaults() -> None:
    error = ConflictError("duplicate")
    assert error.code == "CONFLICT"
    assert error.status_code == 409
    assert isinstance(error, AppError)
