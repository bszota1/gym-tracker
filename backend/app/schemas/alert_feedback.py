from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.common import APIModel

FeedbackRating = Literal["USEFUL", "NOT_USEFUL"]


class AlertFeedbackCreate(BaseModel):
    exercise_id: int
    alert_date: date
    model_run_id: int | None = None
    model_type: str = Field(min_length=1, max_length=50)
    rating: FeedbackRating


class AlertFeedbackResponse(APIModel):
    id: int
    exercise_id: int
    alert_date: date
    model_run_id: int | None
    model_type: str
    feature_pipeline_version: str
    threshold_version: str
    rating: FeedbackRating
    created_at: datetime


class AlertFeedbackSummaryResponse(BaseModel):
    exercise_id: int
    total: int
    useful: int
    not_useful: int
    useful_rate: float | None
    threshold_version: str
    auto_model_update: bool
