from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.forecast import ForecastResponse
from backend.app.services.forecast import ForecastService

router = APIRouter(tags=["forecasts"])


def get_forecast_service(db: AsyncSession = Depends(get_db)) -> ForecastService:
    return ForecastService(db)


@router.get(
    "/api/v1/forecasts/strength",
    response_model=ForecastResponse,
)
async def get_strength_forecast(
    exercise_id: int = Query(...),
    goal_id: int = Query(...),
    service: ForecastService = Depends(get_forecast_service),
) -> ForecastResponse:
    return await service.get_strength_forecast(
        exercise_id=exercise_id,
        goal_id=goal_id,
    )
