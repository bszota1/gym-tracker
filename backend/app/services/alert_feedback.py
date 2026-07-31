from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.db.models.alert_feedback import AlertFeedback
from backend.app.ml.alert_feedback_analysis import summarize_alert_feedback
from backend.app.ml.anomaly_alerts import DROP_ALERT_THRESHOLD_VERSION
from backend.app.ml.pipeline_contract import FEATURE_PIPELINE_VERSION
from backend.app.repositories.alert_feedback import AlertFeedbackRepository
from backend.app.repositories.exercises import ExerciseRepository
from backend.app.repositories.model_runs import ModelRunRepository
from backend.app.schemas.alert_feedback import (
    AlertFeedbackCreate,
    AlertFeedbackSummaryResponse,
)


class AlertFeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._feedback = AlertFeedbackRepository(session)
        self._exercises = ExerciseRepository(session)
        self._runs = ModelRunRepository(session)

    async def create(self, data: AlertFeedbackCreate) -> AlertFeedback:
        exercise = await self._exercises.get_by_id(data.exercise_id)
        if exercise is None:
            raise NotFoundError("Exercise not found")

        if data.model_run_id is not None:
            run = await self._runs.get_by_id(data.model_run_id)
            if run is None:
                raise NotFoundError("Model run not found")

        existing = await self._feedback.get_by_key(
            exercise_id=data.exercise_id,
            alert_date=data.alert_date,
            model_run_id=data.model_run_id,
        )
        if existing is not None:
            raise ConflictError("Feedback already exists for this alert")

        row = AlertFeedback(
            exercise_id=data.exercise_id,
            alert_date=data.alert_date,
            model_run_id=data.model_run_id,
            model_type=data.model_type,
            feature_pipeline_version=FEATURE_PIPELINE_VERSION,
            threshold_version=DROP_ALERT_THRESHOLD_VERSION,
            rating=data.rating,
        )
        created = await self._feedback.create(row)
        await self._session.commit()
        await self._session.refresh(created)
        return created

    async def summarize(
        self,
        *,
        exercise_id: int,
        threshold_version: str | None = None,
    ) -> AlertFeedbackSummaryResponse:
        exercise = await self._exercises.get_by_id(exercise_id)
        if exercise is None:
            raise NotFoundError("Exercise not found")

        version = threshold_version or DROP_ALERT_THRESHOLD_VERSION
        rows = await self._feedback.list_for_exercise(
            exercise_id=exercise_id,
            threshold_version=version,
        )
        summary = summarize_alert_feedback(
            [row.rating for row in rows],
            threshold_version=version,
        )
        return AlertFeedbackSummaryResponse(
            exercise_id=exercise_id,
            total=summary.total,
            useful=summary.useful,
            not_useful=summary.not_useful,
            useful_rate=summary.useful_rate,
            threshold_version=version,
            auto_model_update=summary.auto_model_update,
        )
