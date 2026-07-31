from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.analytics.queries import AnalyticsQueries
from backend.app.ml.metrics_join import join_daily_metrics
from backend.app.ml.observations import select_daily_strength_observations
from backend.app.ml.pipeline_contract import (
    FEATURE_PIPELINE_VERSION,
    PipelineInput,
    PipelineMeta,
    PipelineResult,
)
from backend.app.ml.temporal_features import add_temporal_features


class FeatureDatasetBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self._queries = AnalyticsQueries(session)

    async def build_base(self, pipeline_input: PipelineInput) -> PipelineResult:
        date_from = pipeline_input.date_from or date(1970, 1, 1)
        date_to = pipeline_input.date_to or date(2100, 1, 1)

        set_rows = await self._queries.fetch_set_rows_for_strength(
            date_from=date_from,
            date_to=date_to,
            exercise_id=pipeline_input.exercise_id,
        )
        observations = select_daily_strength_observations(
            set_rows,
            exercise_id=pipeline_input.exercise_id,
        )

        if observations:
            obs_from = observations[0]["date"]
            obs_to = observations[-1]["date"]
            metric_rows = await self._queries.fetch_daily_metric_rows(obs_from, obs_to)
        else:
            metric_rows = []

        joined = join_daily_metrics(observations, metric_rows)
        rows = add_temporal_features(joined)
        meta = PipelineMeta(
            exercise_id=pipeline_input.exercise_id,
            feature_pipeline_version=FEATURE_PIPELINE_VERSION,
            date_from=rows[0]["date"] if rows else pipeline_input.date_from,
            date_to=rows[-1]["date"] if rows else pipeline_input.date_to,
            sample_count=len(rows),
            fingerprint=None,
            extras={
                "stage": "temporal_features",
                "forward_fill": False,
            },
        )
        return PipelineResult(rows=rows, meta=meta)
