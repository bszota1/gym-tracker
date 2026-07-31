from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.app.ml.freshness import assess_model_freshness
from backend.app.ml.model_types import (
    FRESHNESS_FRESH,
    FRESHNESS_STALE_AGE,
    FRESHNESS_STALE_DATA,
)


def test_freshness_fingerprint_and_age() -> None:
    trained_at = datetime(2026, 1, 1, tzinfo=UTC)
    fresh = assess_model_freshness(
        trained_fingerprint="abc",
        current_fingerprint="abc",
        trained_at=trained_at,
        now=trained_at + timedelta(days=1),
    )
    assert fresh.status == FRESHNESS_FRESH
    assert fresh.warnings == ()

    stale_data = assess_model_freshness(
        trained_fingerprint="abc",
        current_fingerprint="xyz",
        trained_at=trained_at,
        now=trained_at + timedelta(days=1),
    )
    assert stale_data.status == FRESHNESS_STALE_DATA
    assert "data_fingerprint_changed" in stale_data.warnings

    stale_age = assess_model_freshness(
        trained_fingerprint="abc",
        current_fingerprint="abc",
        trained_at=trained_at,
        now=trained_at + timedelta(days=30),
        max_age_days=14,
    )
    assert stale_age.status == FRESHNESS_STALE_AGE
    assert "model_age_exceeded" in stale_age.warnings
