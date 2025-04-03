from fastapi import APIRouter, HTTPException

from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService

router = APIRouter(prefix="/model/config", tags=["model_config"])


config_service = ModelConfigService()


@router.get("/")
async def get_model_config(model_id: str) -> ModelConfig:
    config = config_service.get(model_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Model config not found")
    return config
