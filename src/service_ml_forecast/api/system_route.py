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

from fastapi import APIRouter
from pandas import __version__

router = APIRouter(prefix="/system", tags=["System"])


@router.get(
    "/health",
    summary="Retrieve the health of the service",
    responses={
        HTTPStatus.OK: {"description": "Service is healthy"},
    },
)
async def get_health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get(
    "/version",
    summary="Retrieve the version of the service",
)
async def get_version() -> dict[str, str]:
    return {"version": __version__}
