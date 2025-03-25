import logging
import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from service_ml_forecast import __app_info__
from service_ml_forecast.config import env
from service_ml_forecast.logging_config import LOGGING_CONFIG

# Load the logging configuration
logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

if __app_info__ is None:
    logger.exception("App initialization failed: Failed to read app info")
    raise RuntimeError("App initialization failed: Failed to read app info")

app = FastAPI(
    title=__app_info__.name,
    description=__app_info__.description,
    version=__app_info__.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

if not env.PUBLISH_DOCS:
    app.docs_url = None
    app.redoc_url = None
    app.openapi_url = None

# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # TODO: Adjust to be stricter
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    logger.info("Starting application")
    logger.info("Application details: %s", __app_info__)
    reload = env.is_development()

    uvicorn.run("service_ml_forecast.main:app", host="0.0.0.0", port=8000, reload=reload)

