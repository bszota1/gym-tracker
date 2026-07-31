from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.alert_feedback import (
    AlertFeedbackCreate,
    AlertFeedbackResponse,
    AlertFeedbackSummaryResponse,
)
from backend.app.services.alert_feedback import AlertFeedbackService

router = APIRouter(tags=["anomaly-alerts"])


def get_alert_feedback_service(
    db: AsyncSession = Depends(get_db),
) -> AlertFeedbackService:
    return AlertFeedbackService(db)


@router.post(
    "/api/v1/anomaly-alerts/feedback",
    response_model=AlertFeedbackResponse,
    status_code=201,
)
async def create_alert_feedback(
    data: AlertFeedbackCreate,
    service: AlertFeedbackService = Depends(get_alert_feedback_service),
) -> AlertFeedbackResponse:
    row = await service.create(data)
    return AlertFeedbackResponse.model_validate(row)


@router.get(
    "/api/v1/anomaly-alerts/feedback/summary",
    response_model=AlertFeedbackSummaryResponse,
)
async def summarize_alert_feedback(
    exercise_id: int = Query(...),
    threshold_version: str | None = Query(default=None),
    service: AlertFeedbackService = Depends(get_alert_feedback_service),
) -> AlertFeedbackSummaryResponse:
    return await service.summarize(
        exercise_id=exercise_id,
        threshold_version=threshold_version,
    )
