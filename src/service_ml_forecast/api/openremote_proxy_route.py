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
OpenRemote API Proxy routes.

These routes are used to proxy requests to the OpenRemote API using the extracted user token.
"""

from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from service_ml_forecast.clients.openremote.models import Asset, BasicRealm, RealmConfig
from service_ml_forecast.clients.openremote.openremote_proxy_client import OpenRemoteProxyClient
from service_ml_forecast.config import ENV
from service_ml_forecast.dependencies import oauth2_scheme
from service_ml_forecast.services.openremote_service import OpenRemoteService

router = APIRouter(prefix="/proxy/openremote/{realm}", tags=["OpenRemote Proxy API"])


@router.get(
    "/assets",
    summary="Retrieve assets that store datapoints",
    responses={
        HTTPStatus.OK: {"description": "Assets have been retrieved"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
    },
)
async def get_assets_with_historical_data(
    token: Annotated[str, Depends(oauth2_scheme)],
    realm: str,
    realm_query: str = Query(..., alias="realm_query", description="The realm used for the asset query"),
) -> list[Asset]:
    service = _build_proxied_openremote_service(token)
    assets = service.get_assets_with_historical_data(realm_query, realm)

    if assets is None:
        return []

    return assets


@router.get(
    "/assets/ids",
    summary="Retrieve assets by a comma-separated list of Asset IDs",
    responses={
        HTTPStatus.OK: {"description": "Assets have been retrieved"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
    },
)
async def get_assets_by_ids(
    token: Annotated[str, Depends(oauth2_scheme)],
    realm: str,
    realm_query: str = Query(..., alias="realm_query", description="The realm used for the asset query"),
    ids_str: str = Query(..., alias="ids", description="Comma-separated list of asset IDs"),
) -> list[Asset]:
    ids_list = [asset_id.strip() for asset_id in ids_str.split(",") if asset_id.strip()]

    service = _build_proxied_openremote_service(token)
    assets = service.get_assets_by_ids(realm_query, realm, ids_list)

    if assets is None:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Unable to retrieve assets")

    return assets


@router.get(
    "/realm/config",
    summary="Retrieve realm configuration",
    responses={
        HTTPStatus.OK: {"description": "Realm configuration has been retrieved"},
        HTTPStatus.NOT_FOUND: {"description": "Realm configuration not found"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
    },
)
async def get_realm_config(
    token: Annotated[str, Depends(oauth2_scheme)],
    realm: str,
) -> RealmConfig:
    service = _build_proxied_openremote_service(token)
    config = service.get_realm_config(realm)

    if config is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Realm configuration not found")

    return config


@router.get(
    "/realm/accessible",
    summary="Retrieve accessible realms for the current user",
    responses={
        HTTPStatus.OK: {"description": "Accessible realms have been retrieved"},
        HTTPStatus.UNAUTHORIZED: {"description": "Unauthorized"},
        HTTPStatus.INTERNAL_SERVER_ERROR: {"description": "Unable to retrieve realms"},
    },
)
async def get_accessible_realms(
    token: Annotated[str, Depends(oauth2_scheme)],
    realm: str,
) -> list[BasicRealm]:
    service = _build_proxied_openremote_service(token)
    realms = service.get_accessible_realms(realm)

    if realms is None:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Unable to retrieve realms")

    return realms


def _build_proxied_openremote_service(token: str) -> OpenRemoteService:
    """Build the OpenRemote service with a proxied client.

    Args:
        token: The token to use for the OpenRemote service.

    Returns:
        The OpenRemote service using the proxied client.
    """
    client = OpenRemoteProxyClient(openremote_url=ENV.ML_OR_URL, token=token)
    return OpenRemoteService(client)
