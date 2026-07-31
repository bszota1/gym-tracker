from __future__ import annotations

from datetime import date, timedelta

from backend.app.ml.anomaly_alerts import (
    NEGATIVE_DROP_PCT_THRESHOLD,
    assess_negative_drop_alert,
    should_raise_negative_drop_alert,
)
from backend.app.ml.anomaly_features import (
    ANOMALY_FEATURE_COLUMNS,
    MISSING_FEATURE_POLICY,
    AnomalyFeatureRow,
    anomaly_feature_matrix,
    build_anomaly_feature_rows,
)
from backend.app.ml.isolation_forest import (
    MIN_SESSIONS_FOR_ISOLATION_FOREST,
    score_anomaly_points,
    train_isolation_forest,
)
from backend.app.ml.temporal_features import add_temporal_features


def _base_row(
    day: date,
    one_rm: float,
    *,
    rpe: float | None = 8.0,
    volume: float = 400.0,
    sleep: float | None = 7.5,
    body_weight: float | None = 80.0,
) -> dict:
    return {
        "date": day,
        "one_rm_kg": one_rm,
        "weight_kg": one_rm * 0.9,
        "reps": 5,
        "rpe": rpe,
        "session_id": 1,
        "set_id": 1,
        "exercise_id": 5,
        "volume_kg": volume,
        "body_weight_kg": body_weight,
        "sleep_hours": sleep,
        "calories_kcal": 2500,
        "body_weight_missing": body_weight is None,
        "sleep_missing": sleep is None,
        "calories_missing": False,
    }


def _rising_then_drop(*, drop_to: float) -> list[dict]:
    start = date(2026, 1, 1)
    rows = [
        _base_row(start + timedelta(days=3 * index), 100.0 + index)
        for index in range(MIN_SESSIONS_FOR_ISOLATION_FOREST - 1)
    ]
    last_day = start + timedelta(days=3 * (MIN_SESSIONS_FOR_ISOLATION_FOREST - 1))
    rows.append(_base_row(last_day, drop_to, rpe=9.5, volume=200.0, sleep=5.0))
    return add_temporal_features(rows)


def test_anomaly_features_and_missing_policy() -> None:
    assert set(MISSING_FEATURE_POLICY) == set(ANOMALY_FEATURE_COLUMNS)
    rows = add_temporal_features(
        [
            _base_row(date(2026, 2, 1), 100.0, rpe=None, sleep=None, body_weight=None),
            _base_row(date(2026, 2, 4), 110.0),
        ]
    )
    features = build_anomaly_feature_rows(rows)
    assert features[0].features["one_rm_delta"] is None
    assert features[0].features["prev_volume_kg"] is None
    assert features[0].features["rpe"] is None
    assert features[0].features["sleep_hours"] is None
    assert features[0].features["body_weight_kg"] is None
    assert features[1].features["one_rm_delta"] == 10.0
    assert features[1].features["pct_dev_roll_7"] is not None
    matrix, names = anomaly_feature_matrix(features)
    assert names == ANOMALY_FEATURE_COLUMNS
    assert matrix.shape == (2, len(ANOMALY_FEATURE_COLUMNS))


def test_isolation_forest_trains_with_fixed_seed_pipeline() -> None:
    rows = _rising_then_drop(drop_to=70.0)
    feature_rows = build_anomaly_feature_rows(rows)
    first = train_isolation_forest(feature_rows)
    second = train_isolation_forest(feature_rows)
    assert first.n_samples == len(feature_rows)
    assert first.contamination == "auto"
    assert first.random_state == 42
    assert first.score_distribution.n == len(feature_rows)
    assert first.pipeline.named_steps["imputer"].strategy == "median"
    scores_a = first.pipeline.decision_function(anomaly_feature_matrix(feature_rows)[0])
    scores_b = second.pipeline.decision_function(anomaly_feature_matrix(feature_rows)[0])
    assert list(scores_a) == list(scores_b)


def test_negative_drop_alert_requires_anomaly_and_threshold() -> None:
    assert (
        should_raise_negative_drop_alert(is_outlier=True, pct_dev_roll_7=-8.0) is True
    )
    assert (
        should_raise_negative_drop_alert(is_outlier=True, pct_dev_roll_7=-2.0) is False
    )
    assert (
        should_raise_negative_drop_alert(is_outlier=False, pct_dev_roll_7=-20.0) is False
    )
    assert (
        should_raise_negative_drop_alert(is_outlier=True, pct_dev_roll_7=12.0) is False
    )

    good = AnomalyFeatureRow(
        date=date(2026, 3, 1),
        features={"pct_dev_roll_7": 15.0},
        one_rm_kg=130.0,
    )
    good_assessment = assess_negative_drop_alert(
        good,
        is_outlier=True,
        anomaly_score=-0.2,
    )
    assert good_assessment.alert is False
    assert good_assessment.reason == "positive_or_zero_deviation"

    drop = AnomalyFeatureRow(
        date=date(2026, 3, 2),
        features={"pct_dev_roll_7": NEGATIVE_DROP_PCT_THRESHOLD - 1},
        one_rm_kg=90.0,
    )
    drop_assessment = assess_negative_drop_alert(
        drop,
        is_outlier=True,
        anomaly_score=-0.3,
    )
    assert drop_assessment.alert is True
    assert drop_assessment.reason == "anomaly_with_negative_drop"


def test_scored_drop_does_not_alert_on_positive_outlier() -> None:
    start = date(2026, 4, 1)
    rows = [
        _base_row(start + timedelta(days=3 * index), 100.0 + 0.2 * index)
        for index in range(MIN_SESSIONS_FOR_ISOLATION_FOREST - 1)
    ]
    rows.append(
        _base_row(
            start + timedelta(days=3 * (MIN_SESSIONS_FOR_ISOLATION_FOREST - 1)),
            140.0,
            rpe=7.0,
        )
    )
    feature_rows = build_anomaly_feature_rows(add_temporal_features(rows))
    trained = train_isolation_forest(feature_rows)
    scored = score_anomaly_points(trained.pipeline, feature_rows)
    last_row, is_outlier, score = scored[-1]
    assessment = assess_negative_drop_alert(
        last_row,
        is_outlier=is_outlier,
        anomaly_score=score,
    )
    if is_outlier:
        assert assessment.alert is False
        assert assessment.reason == "positive_or_zero_deviation"
