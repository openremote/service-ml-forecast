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
Exception handlers for the FastAPI application.
"""

from http.client import CONFLICT, NOT_FOUND

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from service_ml_forecast.common.exceptions import ResourceAlreadyExistsError, ResourceNotFoundError


async def resource_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle ResourceNotFoundError exceptions.
    Returns:
        A JSON response with a 404 status code.
    """
    return JSONResponse(
        status_code=NOT_FOUND,
        content={"error": str(exc)},
    )


async def resource_already_exists_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle ResourceAlreadyExistsError exceptions.
    Returns:
        A JSON response with a 409 status code.
    """
    return JSONResponse(
        status_code=CONFLICT,
        content={"error": str(exc)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Binds the additional exception handlers to the FastAPI application.

    Args:
        app: The FastAPI application to bind the exception handlers to.
    """

    app.add_exception_handler(ResourceNotFoundError, resource_not_found_handler)
    app.add_exception_handler(ResourceAlreadyExistsError, resource_already_exists_handler)
