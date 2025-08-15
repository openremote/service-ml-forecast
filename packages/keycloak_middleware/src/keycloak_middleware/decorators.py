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
Keycloak decorators for FastAPI routes.

These decorators can be used to check if the user has access to the realm or resource.
"""

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from http import HTTPStatus
from typing import Any, cast

from fastapi import HTTPException

from keycloak_middleware.constants import (
    ERROR_INSUFFICIENT_PERMISSIONS,
    ERROR_REALM_REQUIRED,
)
from keycloak_middleware.models import UserContext

logger = logging.getLogger(__name__)


def _skip_decorator(kwargs: dict[str, Any]) -> bool:
    """Check if the decorator should be skipped.

    The keycloak middleware injects a UserContext object when the token could be validated.
    If the context is missing, it means either the middleware is not active or the token could not be validated.
    In both cases, we can skip the decorator checks to prevent them from running unnecessarily.
    """
    return cast(UserContext, kwargs.get("user")) is None


async def _execute_decorated_function(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Execute the decorated function.

    If the function is a coroutine, return the coroutine.
    Otherwise, execute and return the result of the function
    """
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def realm_accessible(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    @realm_accessible decorator checks whether the user has access to the realm.

    The decorated function must have 'realm' and 'user' parameters.
    """

    @wraps(func)
    async def decorator(*args: Any, **kwargs: Any) -> Any:
        if _skip_decorator(kwargs):
            return await _execute_decorated_function(func, *args, **kwargs)

        user_context = cast(UserContext, kwargs.get("user"))
        realm = kwargs.get("realm")

        if not realm:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=ERROR_REALM_REQUIRED)

        if not user_context.is_realm_accessible_by_user(realm):
            logger.warning(f"Request denied for user {user_context.get_username()}: missing realm access to {realm}")
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=ERROR_INSUFFICIENT_PERMISSIONS)

        return await _execute_decorated_function(func, *args, **kwargs)

    return decorator


def roles_allowed(*, resource: str, roles: list[str]) -> Callable[..., Any]:
    """
    @roles_allowed decorator that validates that the user has at least one of the required resource roles.

    Args:
        resource: The resource to check the roles for.
        roles: The roles to check for.

    The decorated function must have a 'user' parameter.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _skip_decorator(kwargs):
                return await _execute_decorated_function(func, *args, **kwargs)

            user_context = cast(UserContext, kwargs.get("user"))

            if not user_context.has_any_resource_role(resource, roles):
                logger.warning(f"Request denied for user {user_context.get_username()}: missing roles {roles}")
                raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=ERROR_INSUFFICIENT_PERMISSIONS)

            return await _execute_decorated_function(func, *args, **kwargs)

        return wrapper

    return decorator
