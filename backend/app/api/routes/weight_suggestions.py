from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.schemas.models_ml import WeightSuggestionResponse
from backend.app.services.weight_suggestions import WeightSuggestionService

router = APIRouter(tags=["weight-suggestions"])


def get_weight_suggestion_service(
    db: AsyncSession = Depends(get_db),
) -> WeightSuggestionService:
    return WeightSuggestionService(db)


@router.get(
    "/api/v1/weight-suggestions",
    response_model=WeightSuggestionResponse,
)
async def get_weight_suggestion(
    exercise_id: int = Query(...),
    service: WeightSuggestionService = Depends(get_weight_suggestion_service),
) -> WeightSuggestionResponse:
    return await service.suggest(exercise_id=exercise_id)
