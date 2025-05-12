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

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from service_ml_forecast.clients.openremote.models import Asset, RealmConfig
from service_ml_forecast.config import ENV
from service_ml_forecast.services.openremote_proxy_service import OpenRemoteProxyService

router = APIRouter(prefix="/proxy/openremote/{realm}", tags=["OpenRemote Proxy API"])


async def get_token_from_request(request: Request) -> str:
    """Extract the token from the request's Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Missing or invalid Authorization header")
    return auth_header.replace("Bearer ", "")


@router.get(
    "/assets",
    summary="Retrieve assets from an OpenRemote realm that store datapoints",
    responses={
        HTTPStatus.OK: {"description": "Assets have been retrieved"},
    },
)
async def get_assets(realm: str, token: str = Depends(get_token_from_request)) -> list[Asset]:
    or_proxy_service = _build_proxy_service(token)
    return or_proxy_service.get_assets_with_historical_datapoints(realm)


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
    token: str = Depends(get_token_from_request),
) -> list[Asset]:
    ids_list = [asset_id.strip() for asset_id in ids_str.split(",") if asset_id.strip()]

    or_proxy_service = _build_proxy_service(token)
    return or_proxy_service.get_assets_by_ids(realm, ids_list)


@router.get(
    "/realm/config",
    summary="Retrieve the realm configuration of an OpenRemote realm",
    responses={
        HTTPStatus.OK: {"description": "Realm configuration has been retrieved"},
        HTTPStatus.NOT_FOUND: {"description": "Realm configuration not found"},
    },
)
async def get_realm_config(realm: str, token: str = Depends(get_token_from_request)) -> RealmConfig:
    or_proxy_service = _build_proxy_service(token)
    config = or_proxy_service.get_realm_config(realm)

    if config is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Realm configuration not found")

    return config


def _build_proxy_service(token: str) -> OpenRemoteProxyService:
    return OpenRemoteProxyService(openremote_url=ENV.ML_OR_URL, token=token)
