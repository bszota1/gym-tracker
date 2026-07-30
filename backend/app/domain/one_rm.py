from decimal import ROUND_HALF_UP, Decimal

_ONE = Decimal("1")
_THIRTY = Decimal("30")
_TWO_DECIMALS = Decimal("0.01")


def calculate_1rm(weight_kg: Decimal, reps: int) -> Decimal:
    if reps <= 0:
        raise ValueError("reps must be positive")

    if weight_kg < 0:
        raise ValueError("weight_kg must be non-negative")

    if reps == 1:
        value: Decimal = weight_kg
    else:
        value: Decimal = weight_kg * (_ONE + Decimal(reps) / _THIRTY)

    return value.quantize(_TWO_DECIMALS, rounding=ROUND_HALF_UP)
