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

from http.client import OK

from fastapi import APIRouter, Depends, HTTPException, Query

from service_ml_forecast.clients.openremote.models import Asset, RealmConfig
from service_ml_forecast.dependencies import get_openremote_service
from service_ml_forecast.services.openremote_service import OpenRemoteService

router = APIRouter(prefix="/openremote", tags=["OpenRemote Assets"])


# e.g. /openremote/assets?realm=master
@router.get(
    "/assets",
    summary="Retrieve assets that have attributes that store historical data",
    responses={
        OK: {"description": "Assets have been retrieved"},
    },
)
async def get_assets(
    realm: str, openremote_service: OpenRemoteService = Depends(get_openremote_service)
) -> list[Asset]:
    return openremote_service.get_assets_with_historical_datapoints(realm)


# e.g. /openremote/assets/ids?realm=master&ids=123,456,789
@router.get(
    "/assets/ids",
    summary="Retrieve assets by a comma-separated list of Asset IDs",
    responses={
        OK: {"description": "Assets have been retrieved"},
    },
)
async def get_assets_by_ids(
    realm: str,
    ids_str: str = Query(..., alias="ids", description="Comma-separated list of asset IDs"),
    openremote_service: OpenRemoteService = Depends(get_openremote_service),
) -> list[Asset]:
    ids_list = [asset_id.strip() for asset_id in ids_str.split(",") if asset_id.strip()]
    return openremote_service.get_assets_by_ids(ids_list, realm)


# e.g. /openremote/realm/config/master
@router.get(
    "/realm/config/{realm}",
    summary="Retrieve the configuration of a realm",
    responses={
        OK: {"description": "Realm configuration has been retrieved"},
    },
)
async def get_realm_config(
    realm: str, openremote_service: OpenRemoteService = Depends(get_openremote_service)
) -> RealmConfig:
    config = openremote_service.get_realm_config(realm)

    if config is None:
        raise HTTPException(status_code=404, detail="Realm configuration not found")

    return config
