from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.analytics.service import AnalyticsService
from backend.app.db.session import get_db
from backend.app.schemas.analytics import (
    BodyWeightTrendResponse,
    OneRmTrendResponse,
    OverviewResponse,
    RecoveryResponse,
    StrengthVsWeightResponse,
)

router = APIRouter(tags=["analytics"])


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get(
    "/api/v1/analytics/body-weight",
    response_model=BodyWeightTrendResponse,
)
async def get_body_weight_trend(
    date_from: date = Query(...),
    date_to: date = Query(...),
    service: AnalyticsService = Depends(get_analytics_service),
) -> BodyWeightTrendResponse:
    payload = await service.body_weight_trend(date_from, date_to)
    return BodyWeightTrendResponse.model_validate(payload)


@router.get(
    "/api/v1/analytics/one-rm",
    response_model=OneRmTrendResponse,
)
async def get_one_rm_trend(
    exercise_id: int = Query(..., ge=1),
    date_from: date = Query(...),
    date_to: date = Query(...),
    service: AnalyticsService = Depends(get_analytics_service),
) -> OneRmTrendResponse:
    payload = await service.one_rm_trend(date_from, date_to, exercise_id)
    return OneRmTrendResponse.model_validate(payload)


@router.get(
    "/api/v1/analytics/strength-vs-weight",
    response_model=StrengthVsWeightResponse,
)
async def get_strength_vs_weight(
    exercise_id: int = Query(..., ge=1),
    date_from: date = Query(...),
    date_to: date = Query(...),
    service: AnalyticsService = Depends(get_analytics_service),
) -> StrengthVsWeightResponse:
    payload = await service.strength_vs_body_weight(date_from, date_to, exercise_id)
    return StrengthVsWeightResponse.model_validate(payload)


@router.get(
    "/api/v1/analytics/recovery",
    response_model=RecoveryResponse,
)
async def get_recovery(
    date_from: date = Query(...),
    date_to: date = Query(...),
    exercise_id: int | None = Query(default=None, ge=1),
    service: AnalyticsService = Depends(get_analytics_service),
) -> RecoveryResponse:
    payload = await service.recovery(date_from, date_to, exercise_id=exercise_id)
    return RecoveryResponse.model_validate(payload)


@router.get(
    "/api/v1/analytics/overview",
    response_model=OverviewResponse,
)
async def get_overview(
    as_of: date | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> OverviewResponse:
    payload = await service.overview(as_of=as_of)
    return OverviewResponse.model_validate(payload)
