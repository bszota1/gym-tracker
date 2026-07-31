from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.ml.model_types import (
    MODEL_TYPE_ISOLATION_FOREST,
    MODEL_TYPE_PROPHET_ONE_RM,
)
from backend.app.schemas.models_ml import (
    AnomalyListResponse,
    ModelStatusResponse,
    ModelTrainResponse,
)
from backend.app.services.model_training import ModelTrainingService

router = APIRouter(tags=["models"])


def get_model_training_service(
    db: AsyncSession = Depends(get_db),
) -> ModelTrainingService:
    return ModelTrainingService(db)


@router.get("/api/v1/models/status", response_model=ModelStatusResponse)
async def get_model_status(
    exercise_id: int = Query(...),
    model_type: str = Query(...),
    service: ModelTrainingService = Depends(get_model_training_service),
) -> ModelStatusResponse:
    payload = await service.get_status(exercise_id=exercise_id, model_type=model_type)
    return ModelStatusResponse(**payload)


@router.post("/api/v1/models/train/forecast", response_model=ModelTrainResponse)
async def train_forecast_model(
    exercise_id: int = Query(...),
    service: ModelTrainingService = Depends(get_model_training_service),
) -> ModelTrainResponse:
    payload = await service.train_forecast(exercise_id=exercise_id)
    return ModelTrainResponse(**payload)


@router.post("/api/v1/models/train/anomalies", response_model=ModelTrainResponse)
async def train_anomaly_model(
    exercise_id: int = Query(...),
    service: ModelTrainingService = Depends(get_model_training_service),
) -> ModelTrainResponse:
    payload = await service.train_anomalies(exercise_id=exercise_id)
    return ModelTrainResponse(**payload)


@router.get("/api/v1/anomalies", response_model=AnomalyListResponse)
async def list_anomalies(
    exercise_id: int = Query(...),
    service: ModelTrainingService = Depends(get_model_training_service),
) -> AnomalyListResponse:
    payload = await service.list_anomalies(exercise_id=exercise_id)
    return AnomalyListResponse(**payload)


@router.get("/api/v1/models/types")
async def list_model_types() -> dict[str, list[str]]:
    return {
        "types": [MODEL_TYPE_PROPHET_ONE_RM, MODEL_TYPE_ISOLATION_FOREST],
    }
