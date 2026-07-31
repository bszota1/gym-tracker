from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from backend.app.ml.anomaly_alerts import DropAlertAssessment
from backend.app.ml.anomaly_features import AnomalyFeatureRow

SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"

MEDIUM_DROP_PCT = 8.0
HIGH_DROP_PCT = 15.0
HIGH_SCORE_CUTOFF = -0.15
MEDIUM_SCORE_CUTOFF = -0.05

ALERT_MESSAGE = (
    "Recorded 1RM is below the recent trend. This may indicate potentially "
    "weaker readiness for this session. It is not a medical assessment."
)


@dataclass(frozen=True, slots=True)
class AlertContext:
    sleep_hours: float | None
    sleep_is_fact: bool
    rpe: float | None
    rpe_is_fact: bool
    prev_volume_kg: float | None
    prev_volume_is_fact: bool
    facts: tuple[str, ...]
    assumptions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EnrichedDropAlert:
    date: date
    alert: bool
    severity: str | None
    anomaly_score: float
    pct_dev_roll_7: float | None
    reason: str | None
    message: str | None
    context: AlertContext


def classify_alert_severity(
    *,
    anomaly_score: float,
    pct_dev_roll_7: float | None,
) -> str:
    drop_mag = 0.0
    if pct_dev_roll_7 is not None and pct_dev_roll_7 < 0:
        drop_mag = abs(pct_dev_roll_7)

    if drop_mag >= HIGH_DROP_PCT or anomaly_score <= HIGH_SCORE_CUTOFF:
        return SEVERITY_HIGH
    if drop_mag >= MEDIUM_DROP_PCT or anomaly_score <= MEDIUM_SCORE_CUTOFF:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def build_alert_context(row: AnomalyFeatureRow) -> AlertContext:
    sleep = row.features.get("sleep_hours")
    rpe = row.features.get("rpe")
    prev_volume = row.features.get("prev_volume_kg")
    sleep_value = sleep if isinstance(sleep, float) else None
    rpe_value = rpe if isinstance(rpe, float) else None
    volume_value = prev_volume if isinstance(prev_volume, float) else None

    facts: list[str] = []
    assumptions: list[str] = []

    pct = row.features.get("pct_dev_roll_7")
    if isinstance(pct, float):
        facts.append(f"1RM deviation vs 7-session trend: {pct:.1f}%")
    else:
        assumptions.append("Trend deviation was unavailable for this session")

    if sleep_value is not None:
        facts.append(f"Sleep recorded: {sleep_value:.1f} h")
    else:
        assumptions.append("Sleep was not recorded for this day")

    if rpe_value is not None:
        facts.append(f"Best-set RPE recorded: {rpe_value:.1f}")
    else:
        assumptions.append("Best-set RPE was not recorded")

    if volume_value is not None:
        facts.append(f"Previous session volume: {volume_value:.0f} kg")
    else:
        assumptions.append("Previous session volume was unavailable")

    return AlertContext(
        sleep_hours=sleep_value,
        sleep_is_fact=sleep_value is not None,
        rpe=rpe_value,
        rpe_is_fact=rpe_value is not None,
        prev_volume_kg=volume_value,
        prev_volume_is_fact=volume_value is not None,
        facts=tuple(facts),
        assumptions=tuple(assumptions),
    )


def enrich_drop_alert(
    assessment: DropAlertAssessment,
    row: AnomalyFeatureRow,
) -> EnrichedDropAlert:
    context = build_alert_context(row)
    if not assessment.alert:
        return EnrichedDropAlert(
            date=assessment.date,
            alert=False,
            severity=None,
            anomaly_score=assessment.anomaly_score,
            pct_dev_roll_7=assessment.pct_dev_roll_7,
            reason=assessment.reason,
            message=None,
            context=context,
        )
    severity = classify_alert_severity(
        anomaly_score=assessment.anomaly_score,
        pct_dev_roll_7=assessment.pct_dev_roll_7,
    )
    return EnrichedDropAlert(
        date=assessment.date,
        alert=True,
        severity=severity,
        anomaly_score=assessment.anomaly_score,
        pct_dev_roll_7=assessment.pct_dev_roll_7,
        reason=assessment.reason,
        message=ALERT_MESSAGE,
        context=context,
    )
