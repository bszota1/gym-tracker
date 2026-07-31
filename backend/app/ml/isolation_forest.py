from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from backend.app.ml.anomaly_features import (
    ANOMALY_FEATURE_COLUMNS,
    AnomalyFeatureRow,
    anomaly_feature_matrix,
)

MIN_SESSIONS_FOR_ISOLATION_FOREST = 8
ISOLATION_FOREST_RANDOM_STATE = 42
ISOLATION_FOREST_CONTAMINATION = "auto"


@dataclass(frozen=True, slots=True)
class AnomalyScoreDistribution:
    n: int
    min_score: float
    max_score: float
    mean_score: float
    p25: float
    p50: float
    p75: float


@dataclass(frozen=True, slots=True)
class IsolationForestTrainResult:
    pipeline: Pipeline
    score_distribution: AnomalyScoreDistribution
    n_samples: int
    feature_names: tuple[str, ...]
    contamination: str | float
    random_state: int


def build_isolation_forest_pipeline(
    *,
    random_state: int = ISOLATION_FOREST_RANDOM_STATE,
    contamination: str | float = ISOLATION_FOREST_CONTAMINATION,
) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                IsolationForest(
                    contamination=contamination,
                    random_state=random_state,
                    n_estimators=100,
                ),
            ),
        ]
    )


def _score_distribution(scores: np.ndarray) -> AnomalyScoreDistribution:
    return AnomalyScoreDistribution(
        n=int(scores.size),
        min_score=float(np.min(scores)),
        max_score=float(np.max(scores)),
        mean_score=float(np.mean(scores)),
        p25=float(np.percentile(scores, 25)),
        p50=float(np.percentile(scores, 50)),
        p75=float(np.percentile(scores, 75)),
    )


def train_isolation_forest(
    feature_rows: list[AnomalyFeatureRow],
    *,
    min_sessions: int = MIN_SESSIONS_FOR_ISOLATION_FOREST,
    random_state: int = ISOLATION_FOREST_RANDOM_STATE,
    contamination: str | float = ISOLATION_FOREST_CONTAMINATION,
) -> IsolationForestTrainResult:
    if len(feature_rows) < min_sessions:
        raise ValueError(
            f"Need at least {min_sessions} sessions for Isolation Forest, "
            f"got {len(feature_rows)}"
        )
    matrix, feature_names = anomaly_feature_matrix(feature_rows)
    pipeline = build_isolation_forest_pipeline(
        random_state=random_state,
        contamination=contamination,
    )
    pipeline.fit(matrix)
    scores = pipeline.decision_function(matrix)
    return IsolationForestTrainResult(
        pipeline=pipeline,
        score_distribution=_score_distribution(np.asarray(scores, dtype=float)),
        n_samples=len(feature_rows),
        feature_names=feature_names,
        contamination=contamination,
        random_state=random_state,
    )


def score_anomaly_points(
    pipeline: Pipeline,
    feature_rows: list[AnomalyFeatureRow],
) -> list[tuple[AnomalyFeatureRow, bool, float]]:
    if not feature_rows:
        return []
    matrix, _ = anomaly_feature_matrix(feature_rows)
    labels = pipeline.predict(matrix)
    scores = pipeline.decision_function(matrix)
    assessed: list[tuple[AnomalyFeatureRow, bool, float]] = []
    for row, label, score in zip(feature_rows, labels, scores, strict=True):
        is_outlier = int(label) == -1
        assessed.append((row, is_outlier, float(score)))
    return assessed


def default_feature_names() -> tuple[str, ...]:
    return ANOMALY_FEATURE_COLUMNS
