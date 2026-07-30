from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.daily_metrics import (
    DailyMetricCreate,
    DailyMetricResponse,
    DailyMetricUpdate,
)
from backend.app.services.daily_metrics import DailyMetricService

router = APIRouter(tags=["daily-metrics"])


def get_daily_metric_service(db: AsyncSession = Depends(get_db)) -> DailyMetricService:
    return DailyMetricService(db)


@router.post(
    "/api/v1/daily-metrics",
    response_model=DailyMetricResponse,
    status_code=201,
)
async def create_daily_metric(
    data: DailyMetricCreate,
    service: DailyMetricService = Depends(get_daily_metric_service),
) -> DailyMetricResponse:
    daily_metric = await service.create(data)
    return DailyMetricResponse.model_validate(daily_metric)


@router.get(
    "/api/v1/daily-metrics",
    response_model=list[DailyMetricResponse],
)
async def list_daily_metrics(
    date_from: date | None = None,
    date_to: date | None = None,
    service: DailyMetricService = Depends(get_daily_metric_service),
) -> list[DailyMetricResponse]:
    daily_metrics = await service.list(date_from=date_from, date_to=date_to)
    return [
        DailyMetricResponse.model_validate(daily_metric)
        for daily_metric in daily_metrics
    ]


@router.get(
    "/api/v1/daily-metrics/{metric_date}",
    response_model=DailyMetricResponse,
)
async def get_daily_metric(
    metric_date: date,
    service: DailyMetricService = Depends(get_daily_metric_service),
) -> DailyMetricResponse:
    daily_metric = await service.get_by_date(metric_date)
    return DailyMetricResponse.model_validate(daily_metric)


@router.patch(
    "/api/v1/daily-metrics/{metric_date}",
    response_model=DailyMetricResponse,
)
async def update_daily_metric(
    metric_date: date,
    data: DailyMetricUpdate,
    service: DailyMetricService = Depends(get_daily_metric_service),
) -> DailyMetricResponse:
    daily_metric = await service.update(metric_date, data)
    return DailyMetricResponse.model_validate(daily_metric)


@router.delete(
    "/api/v1/daily-metrics/{metric_date}",
    status_code=204,
)
async def delete_daily_metric(
    metric_date: date,
    service: DailyMetricService = Depends(get_daily_metric_service),
) -> Response:
    await service.delete(metric_date)
    return Response(status_code=204)
