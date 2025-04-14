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
Web API routes.

These routes are used to serve the web application.
"""

import logging
from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from service_ml_forecast.config import ENV

logger = logging.getLogger(__name__)

router = APIRouter(include_in_schema=False)

web_dist_dir = Path(ENV.ML_WEB_DIST_DIR)

if web_dist_dir.exists():
    router.mount("/static", StaticFiles(directory=str(web_dist_dir)), name="static")
else:
    logger.error(f"Web dist directory not found at {web_dist_dir}, bundle cannot be served")


@router.get(
    "/",
    summary="Serve the index.html file from the web dist directory.",
    responses={
        HTTPStatus.OK: {"description": "Index.html file has been served"},
        HTTPStatus.NOT_FOUND: {"description": "Index.html file not found"},
    },
)
async def serve_index() -> FileResponse:
    """Serve the index.html file from the web dist directory."""

    index_path = web_dist_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)


@router.get(
    "/{path:path}",
    summary="Serve static files or return index.html for SPA routing.",
    responses={
        HTTPStatus.OK: {"description": "Static file has been served"},
        HTTPStatus.NOT_FOUND: {"description": "Static file not found"},
    },
)
async def serve_spa(path: str) -> FileResponse:
    """Serve static files or return index.html for SPA routing."""

    requested_path = web_dist_dir / path

    # If the exact file exists, serve it (e.g. css, images, etc.)
    if requested_path.is_file():
        return FileResponse(requested_path)

    # Return index.html for client-side routing
    index_path = web_dist_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)
