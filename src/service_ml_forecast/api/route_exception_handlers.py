"""
This module contains the exception handlers for the FastAPI application.

These need to be defined and registered with the FastAPI application otherwise
FastAPI will throw 500 errors to the client.
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
