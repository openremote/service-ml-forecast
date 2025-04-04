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


def bind_exception_handlers(app: FastAPI) -> None:
    """Bind all exception handlers with the FastAPI application."""

    # Handle ResourceNotFoundError exceptions
    app.add_exception_handler(ResourceNotFoundError, resource_not_found_handler)

    # Handle ResourceAlreadyExistsError exceptions
    app.add_exception_handler(ResourceAlreadyExistsError, resource_already_exists_handler)
