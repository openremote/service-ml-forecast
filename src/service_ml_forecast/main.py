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

import logging.config
from collections.abc import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from service_ml_forecast import __app_info__
from service_ml_forecast.config import env
from service_ml_forecast.logging_config import LOGGING_CONFIG
from service_ml_forecast.services.training_scheduler import TrainingScheduler

# Load the logging configuration
logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

if __app_info__ is None:
    logger.critical("App initialization failed: Failed to read app info")
    raise RuntimeError("App initialization failed: Failed to read app info")


# FastAPI Lifecycle, handles startup and shutdown tasks
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup tasks
    logger.info("Starting application")
    logger.info("Application details: %s", __app_info__)

    # Initialize background services
    TrainingScheduler().start()

    yield

    # Shutdown tasks
    TrainingScheduler().stop()
    logger.info("Shutting down application")


app = FastAPI(
    title=__app_info__.name,
    description=__app_info__.description,
    version=__app_info__.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

if not env.PUBLISH_DOCS:
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


if __name__ == "__main__":
    reload = env.is_development()
    uvicorn.run("service_ml_forecast.main:app", host="0.0.0.0", port=8000, reload=reload)
