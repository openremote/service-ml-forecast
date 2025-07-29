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
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Model config API routes.

These routes are used to create, retrieve, update and delete model configs.
"""

from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from openremote_client import ClientRoles

from service_ml_forecast.dependencies import OAUTH2_SCHEME, OPENREMOTE_KC_RESOURCE, get_config_service
from service_ml_forecast.middlewares.keycloak.decorators import realm_accessible, roles_allowed
from service_ml_forecast.middlewares.keycloak.middleware import KeycloakMiddleware
from service_ml_forecast.middlewares.keycloak.models import UserContext
from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService

router = APIRouter(
    prefix="/api/{realm}/configs",
    tags=["Forecast Configs"],
    dependencies=[
        Depends(OAUTH2_SCHEME),
    ],
)


@router.post(
    "",
    summary="Create a new model config",
    responses={
        HTTPStatus.OK: {"description": "Model config has been created"},
        HTTPStatus.CONFLICT: {"description": "Model config already exists"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
        HTTPStatus.FORBIDDEN: {"description": "Forbidden - insufficient permissions"},
    },
)
@realm_accessible
@roles_allowed(resource=OPENREMOTE_KC_RESOURCE, roles=[ClientRoles.WRITE_ADMIN_ROLE])
async def create_model_config(
    user: Annotated[UserContext, Depends(KeycloakMiddleware.get_user_context)],
    realm: str,
    model_config: ModelConfig,
    config_service: ModelConfigService = Depends(get_config_service),
) -> ModelConfig:
    return config_service.create(realm, model_config)


@router.get(
    "/{id}",
    summary="Retrieve a model config",
    responses={
        HTTPStatus.OK: {"description": "Model config has been retrieved"},
        HTTPStatus.NOT_FOUND: {"description": "Model config not found"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
        HTTPStatus.FORBIDDEN: {"description": "Forbidden - insufficient permissions"},
    },
)
@realm_accessible
@roles_allowed(resource=OPENREMOTE_KC_RESOURCE, roles=[ClientRoles.READ_ADMIN_ROLE])
async def get_model_config(
    user: Annotated[UserContext, Depends(KeycloakMiddleware.get_user_context)],
    realm: str,
    id: UUID,
    config_service: ModelConfigService = Depends(get_config_service),
) -> ModelConfig:
    return config_service.get(realm, id)


@router.get(
    "",
    summary="Retrieve all model configs for a given realm",
    responses={
        HTTPStatus.OK: {"description": "List of model configs has been retrieved"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
        HTTPStatus.FORBIDDEN: {"description": "Forbidden - insufficient permissions"},
    },
)
@realm_accessible
@roles_allowed(resource=OPENREMOTE_KC_RESOURCE, roles=[ClientRoles.READ_ADMIN_ROLE])
async def get_model_configs(
    user: Annotated[UserContext, Depends(KeycloakMiddleware.get_user_context)],
    realm: str,
    config_service: ModelConfigService = Depends(get_config_service),
) -> list[ModelConfig]:
    return config_service.get_all(realm)


@router.put(
    "/{id}",
    summary="Update a model config",
    responses={
        HTTPStatus.OK: {"description": "Model config has been updated"},
        HTTPStatus.NOT_FOUND: {"description": "Model config not found"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
        HTTPStatus.FORBIDDEN: {"description": "Forbidden - insufficient permissions"},
    },
)
@realm_accessible
@roles_allowed(resource=OPENREMOTE_KC_RESOURCE, roles=[ClientRoles.WRITE_ADMIN_ROLE])
async def update_model_config(
    user: Annotated[UserContext, Depends(KeycloakMiddleware.get_user_context)],
    realm: str,
    id: UUID,
    model_config: ModelConfig,
    config_service: ModelConfigService = Depends(get_config_service),
) -> ModelConfig:
    if model_config.realm != realm:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Model does not match realm")

    return config_service.update(realm, id, model_config)


@router.delete(
    "/{id}",
    summary="Delete a model config",
    responses={
        HTTPStatus.OK: {"description": "Model config has been deleted"},
        HTTPStatus.NOT_FOUND: {"description": "Model config not found"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
        HTTPStatus.FORBIDDEN: {"description": "Forbidden - insufficient permissions"},
    },
)
@realm_accessible
@roles_allowed(resource=OPENREMOTE_KC_RESOURCE, roles=[ClientRoles.WRITE_ADMIN_ROLE])
async def delete_model_config(
    user: Annotated[UserContext, Depends(KeycloakMiddleware.get_user_context)],
    realm: str,
    id: UUID,
    config_service: ModelConfigService = Depends(get_config_service),
) -> JSONResponse:
    config_service.delete(realm, id)
    return JSONResponse(status_code=HTTPStatus.OK, content={"message": "Model config deleted successfully"})
