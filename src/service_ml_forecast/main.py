import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from service_ml_forecast import __app_info__
from service_ml_forecast.config import config

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:

    if __app_info__ is None:
        logger.error("App initialization failed: Failed to read app info")
        raise Exception("App initialization failed: Failed to read app info")

    app = FastAPI(
        title=__app_info__.name,
        description=__app_info__.description,
        version=__app_info__.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    if not config.PUBLIC_DOCS:
        app.docs_url = None
        app.redoc_url = None
        app.openapi_url = None

    # Add CORS middleware
    # TODO: In production, replace with specific origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
