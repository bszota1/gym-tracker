from __future__ import annotations

from datetime import date

from backend.app.ml.anomaly_alerts import assess_negative_drop_alert
from backend.app.ml.anomaly_features import AnomalyFeatureRow
from backend.app.ml.anomaly_severity import (
    ALERT_MESSAGE,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    classify_alert_severity,
    enrich_drop_alert,
)


def test_severity_levels_from_score_and_drop() -> None:
    assert (
        classify_alert_severity(anomaly_score=-0.01, pct_dev_roll_7=-6.0) == SEVERITY_LOW
    )
    assert (
        classify_alert_severity(anomaly_score=-0.01, pct_dev_roll_7=-10.0)
        == SEVERITY_MEDIUM
    )
    assert (
        classify_alert_severity(anomaly_score=-0.2, pct_dev_roll_7=-6.0) == SEVERITY_HIGH
    )


def test_enriched_alert_separates_facts_and_assumptions() -> None:
    row = AnomalyFeatureRow(
        date=date(2026, 5, 1),
        one_rm_kg=90.0,
        features={
            "pct_dev_roll_7": -12.0,
            "sleep_hours": None,
            "rpe": 9.0,
            "prev_volume_kg": 500.0,
        },
    )
    assessment = assess_negative_drop_alert(
        row,
        is_outlier=True,
        anomaly_score=-0.2,
    )
    enriched = enrich_drop_alert(assessment, row)
    assert enriched.alert is True
    assert enriched.severity == SEVERITY_HIGH
    assert enriched.message == ALERT_MESSAGE
    assert "medical" not in enriched.message.lower() or "not a medical" in enriched.message
    assert enriched.context.rpe_is_fact is True
    assert enriched.context.sleep_is_fact is False
    assert any("RPE" in fact for fact in enriched.context.facts)
    assert any("Sleep was not recorded" in item for item in enriched.context.assumptions)
