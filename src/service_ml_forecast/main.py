from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from service_ml_forecast.system.status_resource import get_status_router
from service_ml_forecast import __app_info__
import logging

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title=__app_info__.name,
        description=__app_info__.description,
        version=__app_info__.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: In production, replace with specific origin
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(get_status_router(app))

    return app

app = create_app()
