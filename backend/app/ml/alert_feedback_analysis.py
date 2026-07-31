from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeedbackSummary:
    total: int
    useful: int
    not_useful: int
    useful_rate: float | None
    threshold_version: str | None
    auto_model_update: bool = False


def summarize_alert_feedback(
    ratings: list[str],
    *,
    threshold_version: str | None = None,
) -> FeedbackSummary:
    useful = sum(1 for rating in ratings if rating == "USEFUL")
    not_useful = sum(1 for rating in ratings if rating == "NOT_USEFUL")
    total = useful + not_useful
    useful_rate = (useful / total) if total else None
    return FeedbackSummary(
        total=total,
        useful=useful,
        not_useful=not_useful,
        useful_rate=useful_rate,
        threshold_version=threshold_version,
        auto_model_update=False,
    )
