from uuid import UUID

from fastapi import APIRouter, HTTPException

from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService

router = APIRouter(prefix="/model/config", tags=["Model Config Endpoints"])


config_service = ModelConfigService()

# TODO: Permissions and realm access control
# User realm will be extracted from the token
# But that doesnt always work if we have a super user with access to all realms

# TODO: Asset name for get all configs (DTO?)
# The list returned should also contain the asset name, so we retrieve that on the service layer
# (we can query via openremote api)
# So will need a response model for only returning the necessary data for the table with the asset name
# We can also add a proxy route and let the frontend call a seperate api to  get a list of assets with their names
# We need the proxy route anyways for filling up the dropdowns for assets and attributes with valid meta configs


@router.post(
    "/",
    summary="Create a new model config",
    response_description="The created model config",
    responses={
        200: {"model": ModelConfig},
    },
)
async def create_model_config(model_config: ModelConfig) -> ModelConfig:
    saved_config = config_service.save(model_config)
    if saved_config is None:
        raise HTTPException(status_code=500, detail="Internal server error, failed to save model config")

    return saved_config


@router.get(
    "/{id}",
    summary="Get a model config",
    response_description="The model config",
    responses={
        200: {"model": ModelConfig},
    },
)
async def get_model_config(id: UUID) -> ModelConfig:
    config = config_service.get(id)
    if config is None:
        raise HTTPException(status_code=404, detail="Model config not found")
    return config


@router.get(
    "/",
    summary="Get all model configs with optional realm filter",
    response_description="The list of model configs",
    responses={
        200: {"model": list[ModelConfig]},
    },
)
async def get_model_configs(realm: str | None = None) -> list[ModelConfig]:
    return config_service.get_all(realm)


@router.put(
    "/",
    summary="Update a model config",
    response_description="The updated model config",
    responses={
        200: {"model": ModelConfig},
    },
)
async def update_model_config(model_config: ModelConfig) -> ModelConfig | None:
    updated_config = config_service.update(model_config)
    if updated_config is None:
        raise HTTPException(status_code=500, detail="Internal server error, failed to update model config")

    return updated_config


@router.delete(
    "/{id}",
    summary="Delete a model config",
    response_description="True if the model config was deleted successfully",
    responses={
        200: {"model": bool},
    },
)
async def delete_model_config(id: UUID) -> bool:
    if not config_service.delete(id):
        raise HTTPException(status_code=500, detail="Internal server error, failed to delete model config")

    return True
