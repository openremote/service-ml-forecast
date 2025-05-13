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
OpenRemote API routes.

These routes are used to retrieve data from OpenRemote. E.g. proxy requests to the OpenRemote API.
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query

from service_ml_forecast.clients.openremote.models import Asset, RealmConfig
from service_ml_forecast.dependencies import get_openremote_service
from service_ml_forecast.services.openremote_service import OpenRemoteService

router = APIRouter(prefix="/openremote/{realm}", tags=["OpenRemote Proxy API"])


@router.get(
    "/assets",
    summary="Retrieve assets from an OpenRemote realm that store datapoints",
    responses={
        HTTPStatus.OK: {"description": "Assets have been retrieved"},
    },
)
async def get_assets(
    realm: str, openremote_service: OpenRemoteService = Depends(get_openremote_service)
) -> list[Asset]:
    return openremote_service.get_assets_with_historical_datapoints(realm)


@router.get(
    "/assets/ids",
    summary="Retrieve assets from an OpenRemote realm by a comma-separated list of Asset IDs",
    responses={
        HTTPStatus.OK: {"description": "Assets have been retrieved"},
    },
)
async def get_assets_by_ids(
    realm: str,
    ids_str: str = Query(..., alias="ids", description="Comma-separated list of asset IDs"),
    openremote_service: OpenRemoteService = Depends(get_openremote_service),
) -> list[Asset]:
    ids_list = [asset_id.strip() for asset_id in ids_str.split(",") if asset_id.strip()]
    return openremote_service.get_assets_by_ids(realm, ids_list)


@router.get(
    "/realm/config",
    summary="Retrieve the realm configuration of an OpenRemote realm",
    responses={
        HTTPStatus.OK: {"description": "Realm configuration has been retrieved"},
        HTTPStatus.NOT_FOUND: {"description": "Realm configuration not found"},
    },
)
async def get_realm_config(
    realm: str, openremote_service: OpenRemoteService = Depends(get_openremote_service)
) -> RealmConfig:
    config = openremote_service.get_realm_config(realm)

    if config is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Realm configuration not found")

    return config
