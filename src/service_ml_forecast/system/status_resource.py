import logging
import time

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class HealthCheckResponse(BaseModel):
    status: str = Field(default="healthy", description="Status of the service")
    timestamp: float = Field(default=time.time(), description="Timestamp of the request")
    version: str = Field(description="Version of the service")
    service: str = Field(description="Name of the service")


def get_status_router(app: FastAPI) -> APIRouter:
    router = APIRouter(
        prefix="/api/system",
        tags=["system"],
        responses={500: {"description": "Internal server error"}},
    )

    @router.get("/health", response_model=HealthCheckResponse)
    async def health_check() -> HealthCheckResponse:
        """
        Health check endpoint that verifies the service is running
        and provides additional system information.
        """
        try:
            return HealthCheckResponse(version=app.version, service=app.title)
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise

    return router
