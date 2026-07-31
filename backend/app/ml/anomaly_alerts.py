from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from backend.app.ml.anomaly_features import AnomalyFeatureRow

NEGATIVE_DROP_PCT_THRESHOLD = -5.0


@dataclass(frozen=True, slots=True)
class DropAlertAssessment:
    date: date
    is_outlier: bool
    anomaly_score: float
    pct_dev_roll_7: float | None
    alert: bool
    reason: str | None


def should_raise_negative_drop_alert(
    *,
    is_outlier: bool,
    pct_dev_roll_7: float | None,
    threshold_pct: float = NEGATIVE_DROP_PCT_THRESHOLD,
) -> bool:
    if not is_outlier:
        return False
    if pct_dev_roll_7 is None:
        return False
    if pct_dev_roll_7 >= 0:
        return False
    return pct_dev_roll_7 <= threshold_pct


def assess_negative_drop_alert(
    row: AnomalyFeatureRow,
    *,
    is_outlier: bool,
    anomaly_score: float,
    threshold_pct: float = NEGATIVE_DROP_PCT_THRESHOLD,
) -> DropAlertAssessment:
    pct_dev = row.features.get("pct_dev_roll_7")
    if isinstance(pct_dev, float):
        pct_value: float | None = pct_dev
    else:
        pct_value = None

    if not is_outlier:
        reason = "not_anomaly"
        alert = False
    elif pct_value is None:
        reason = "missing_trend_deviation"
        alert = False
    elif pct_value >= 0:
        reason = "positive_or_zero_deviation"
        alert = False
    elif pct_value > threshold_pct:
        reason = "drop_not_severe_enough"
        alert = False
    else:
        reason = "anomaly_with_negative_drop"
        alert = True

    return DropAlertAssessment(
        date=row.date,
        is_outlier=is_outlier,
        anomaly_score=anomaly_score,
        pct_dev_roll_7=pct_value,
        alert=alert,
        reason=reason,
    )


def assess_points_for_drop_alerts(
    scored_points: list[tuple[AnomalyFeatureRow, bool, float]],
    *,
    threshold_pct: float = NEGATIVE_DROP_PCT_THRESHOLD,
) -> list[DropAlertAssessment]:
    return [
        assess_negative_drop_alert(
            row,
            is_outlier=is_outlier,
            anomaly_score=score,
            threshold_pct=threshold_pct,
        )
        for row, is_outlier, score in scored_points
    ]
