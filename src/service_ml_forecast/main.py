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

import logging.config
from collections.abc import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from service_ml_forecast import __app_info__
from service_ml_forecast.api import model_config_route, openremote_route
from service_ml_forecast.api.route_exception_handlers import register_exception_handlers
from service_ml_forecast.config import ENV
from service_ml_forecast.dependencies import get_openremote_service
from service_ml_forecast.logging_config import LOGGING_CONFIG
from service_ml_forecast.services.model_scheduler import ModelScheduler

# Load the logging configuration
logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)


# FastAPI Lifecycle, handles startup and shutdown tasks
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    logger.info("FastAPI instance starting")

    yield  # yield to the FastAPI app
    logger.info("FastAPI instance shutting down")


app = FastAPI(
    title=__app_info__.name,
    description=__app_info__.description,
    version=__app_info__.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

if not ENV.ML_PUBLISH_DOCS:
    app.docs_url = None
    app.redoc_url = None
    app.openapi_url = None

# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Adjust to be stricter
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Include Routers ---
app.include_router(model_config_route.router)
app.include_router(openremote_route.router)


# --- Exception Handlers ---
register_exception_handlers(app)


def initialize_background_services() -> None:
    """Initialize background services, these run in the background and are not part of the FastAPI lifecycle"""
    # Setup the ML Model Scheduler
    model_scheduler = ModelScheduler(get_openremote_service())
    model_scheduler.start()


if __name__ == "__main__":
    logger.info("Application details: %s", __app_info__)

    initialize_background_services()
    reload = ENV.is_development()
    uvicorn.run("service_ml_forecast.main:app", host="0.0.0.0", port=8000, reload=reload)
