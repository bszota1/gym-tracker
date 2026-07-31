from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from backend.app.ml.model_types import (
    FRESHNESS_FRESH,
    FRESHNESS_STALE_AGE,
    FRESHNESS_STALE_DATA,
    MODEL_MAX_AGE_DAYS,
)


@dataclass(frozen=True, slots=True)
class ModelFreshness:
    status: str
    warnings: tuple[str, ...]
    trained_fingerprint: str
    current_fingerprint: str
    trained_at: datetime
    age_days: int
    max_age_days: int

    @property
    def is_fresh(self) -> bool:
        return self.status == FRESHNESS_FRESH


def assess_model_freshness(
    *,
    trained_fingerprint: str,
    current_fingerprint: str,
    trained_at: datetime,
    now: datetime | None = None,
    max_age_days: int = MODEL_MAX_AGE_DAYS,
) -> ModelFreshness:
    current = now or datetime.now(UTC)
    if trained_at.tzinfo is None:
        trained_at = trained_at.replace(tzinfo=UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)

    age = current - trained_at
    age_days = max(0, int(age.total_seconds() // 86400))
    warnings: list[str] = []

    if trained_fingerprint != current_fingerprint:
        status = FRESHNESS_STALE_DATA
        warnings.append("data_fingerprint_changed")
    elif age > timedelta(days=max_age_days):
        status = FRESHNESS_STALE_AGE
        warnings.append("model_age_exceeded")
    else:
        status = FRESHNESS_FRESH

    return ModelFreshness(
        status=status,
        warnings=tuple(warnings),
        trained_fingerprint=trained_fingerprint,
        current_fingerprint=current_fingerprint,
        trained_at=trained_at,
        age_days=age_days,
        max_age_days=max_age_days,
    )
