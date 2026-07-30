from decimal import ROUND_HALF_UP, Decimal


def calculate_1rm(weight_kg: Decimal, reps: int) -> Decimal:
    if reps <= 0:
        raise ValueError("reps must be psitive")

    if weight_kg < 0:
        raise ValueError("weight_kg must be non-negative")

    if reps == 1:
        return weight_kg
    else:
        return Decimal(ROUND_HALF_UP(weight_kg * (1 + reps / 30)))
