# Copyright 2025, OpenRemote Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from http.client import CONFLICT, NOT_FOUND, OK
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from service_ml_forecast.dependencies import get_config_service
from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService

router = APIRouter(prefix="/model/config", tags=["Model Configs"])


@router.post(
    "/",
    summary="Create a new model config",
    responses={
        OK: {"description": "Model config has been created"},
        CONFLICT: {"description": "Model config already exists"},
    },
)
async def create_model_config(
    model_config: ModelConfig, config_service: ModelConfigService = Depends(get_config_service)
) -> ModelConfig:
    return config_service.create(model_config)


@router.get(
    "/{id}",
    summary="Retrieve a model config by ID",
    responses={
        OK: {"description": "Model config has been retrieved"},
        NOT_FOUND: {"description": "Model config not found"},
    },
)
async def get_model_config(id: UUID, config_service: ModelConfigService = Depends(get_config_service)) -> ModelConfig:
    return config_service.get(id)


@router.get(
    "/",
    summary="Retrieve all model configs with optional realm filter",
    responses={
        OK: {"description": "List of model configs has been retrieved"},
    },
)
async def get_model_configs(
    realm: str | None = None, config_service: ModelConfigService = Depends(get_config_service)
) -> list[ModelConfig]:
    return config_service.get_all(realm)


@router.put(
    "/",
    summary="Update a model config",
    responses={
        OK: {"description": "Model config has been updated"},
        NOT_FOUND: {"description": "Model config not found"},
    },
)
async def update_model_config(
    model_config: ModelConfig, config_service: ModelConfigService = Depends(get_config_service)
) -> ModelConfig:
    return config_service.update(model_config)


@router.delete(
    "/{id}",
    summary="Delete a model config by ID",
    responses={
        OK: {"description": "Model config has been deleted"},
        NOT_FOUND: {"description": "Model config not found"},
    },
)
async def delete_model_config(
    id: UUID, config_service: ModelConfigService = Depends(get_config_service)
) -> JSONResponse:
    config_service.delete(id)
    return JSONResponse(status_code=OK, content={"message": "Model config deleted successfully"})
