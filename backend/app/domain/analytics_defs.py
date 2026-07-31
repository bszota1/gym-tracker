from __future__ import annotations

from decimal import Decimal

ROLLING_WINDOW_DAYS = 7
MAX_REPS_FOR_STRENGTH_TREND = 12
BODY_WEIGHT_GOAL_MIN_KG = 70
BODY_WEIGHT_GOAL_MAX_KG = 95
BODY_WEIGHT_TARGET_KG = 90
OVERVIEW_METRICS_WINDOW_DAYS = 7
INCLUDE_WARMUPS_IN_VOLUME = False
ANALYTICS_SEMANTICS_VERSION = "1"


def is_eligible_for_strength_trend(*, is_warmup: bool, reps: int) -> bool:
    if is_warmup:
        return False
    if reps > MAX_REPS_FOR_STRENGTH_TREND:
        return False
    return True


def set_volume_kg(weight_kg: Decimal, reps: int) -> Decimal:
    return weight_kg * reps
