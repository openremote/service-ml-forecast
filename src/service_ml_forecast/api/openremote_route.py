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

from fastapi import APIRouter, Depends

from service_ml_forecast.clients.openremote.models import Asset
from service_ml_forecast.dependencies import get_openremote_service
from service_ml_forecast.services.openremote_service import OpenRemoteService

router = APIRouter(prefix="/openremote", tags=["OpenRemote"])


# e.g. /openremote/assets?realm=master
@router.get("/assets")
async def get_assets(
    realm: str, openremote_service: OpenRemoteService = Depends(get_openremote_service)
) -> list[Asset]:
    return openremote_service.get_assets_with_historical_datapoints(realm)


# e.g. /openremote/assets?ids=123,456,789&realm=master
@router.get("/assets")
async def get_assets_by_ids(
    ids: list[str], realm: str, openremote_service: OpenRemoteService = Depends(get_openremote_service)
) -> list[Asset]:
    return openremote_service.get_assets_by_ids(ids, realm)
