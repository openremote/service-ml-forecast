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

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService

router = APIRouter(prefix="/model/config", tags=["Model Configs"])


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
    responses={
        OK: {"description": "Model config has been created"},
        CONFLICT: {"description": "Model config already exists"},
    },
)
async def create_model_config(model_config: ModelConfig) -> ModelConfig:
    return config_service.save(model_config)


@router.get(
    "/{id}",
    summary="Get a model config",
    responses={
        OK: {"description": "Model config has been retrieved"},
        NOT_FOUND: {"description": "Model config not found"},
    },
)
async def get_model_config(id: UUID) -> ModelConfig:
    return config_service.get(id)


@router.get(
    "/",
    summary="Get all model configs with optional realm filter",
    responses={
        OK: {"description": "List of model configs has been retrieved"},
    },
)
async def get_model_configs(realm: str | None = None) -> list[ModelConfig]:
    return config_service.get_all(realm)


@router.put(
    "/",
    summary="Update a model config",
    responses={
        OK: {"description": "Model config has been updated"},
        NOT_FOUND: {"description": "Model config not found"},
    },
)
async def update_model_config(model_config: ModelConfig) -> ModelConfig:
    return config_service.update(model_config)


@router.delete(
    "/{id}",
    summary="Delete a model config",
    responses={
        OK: {"description": "Model config has been deleted"},
        NOT_FOUND: {"description": "Model config not found"},
    },
)
async def delete_model_config(id: UUID) -> JSONResponse:
    config_service.delete(id)
    return JSONResponse(status_code=OK, content={"message": "Model config deleted successfully"})
