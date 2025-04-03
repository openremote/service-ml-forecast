from fastapi import APIRouter, HTTPException

from service_ml_forecast.models.ml_model_config import MLModelConfig
from service_ml_forecast.services.ml_model_config_service import MLModelConfigService

router = APIRouter(prefix="/model/config", tags=["model_config"])


config_service = MLModelConfigService()


@router.get("/")
async def get_model_config(model_id: str) -> MLModelConfig:
    config = config_service.get(model_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Model config not found")
    return config
