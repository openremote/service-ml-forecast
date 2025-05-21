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

"""Custom middleware for handling Keycloak authentication and authorization.

Every request goes through this middleware and is verified against the Keycloak JWKS endpoint.
Only endpoints that are excluded from authentication have their request forwarded to the next middleware.


Authentication and Authorization Steps:
1. Check if the request path matches any excluded routes
2. Extract and validate the Bearer token from the Authorization header
3. Validate token format before processing
4. Extract and validate the Key ID (kid) from the token header
5. Extract and validate the issuer URL from the token
6. Validate the issuer URL against the list of valid issuers based on the realms retrieved from OpenRemote
7. Construct the JWKS URL using the validated issuer URL
8. Get the JWKS from the JWKS endpoint with proper caching
9. Validate JWKS keys structures
10. Verify the token signature using the public key from JWKS
11. Check if the user has the required roles (write:admin, read:admin)
12. Inject the validated user payload into the request state
"""

import logging
import re
from http import HTTPStatus
from typing import Any, cast

import httpx
import jwt
from aiocache import Cache, cached
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import HTTPException
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from service_ml_forecast.config import ENV
from service_ml_forecast.dependencies import get_openremote_service

logger = logging.getLogger(__name__)


# --- Pydantic models for the Keycloak token payload ---
class ResourceRoles(BaseModel):
    """Represents the roles the user has in a resource e.g. realm."""

    roles: list[str]


class KeycloakTokenUserPayload(BaseModel):
    """Partial payload of the JWT token for handling resource access."""

    preferred_username: str
    resource_access: dict[str, ResourceRoles]


# TODO: Improve role checking and handling to enable more granular role-based access control
# See issue: https://github.com/openremote/service-ml-forecast/issues/32
RESOURCE_ACCESS_KEY = "openremote"
REQUIRED_ROLES = ["write:admin", "read:admin"]


@cached(ttl=30, cache=Cache.MEMORY, key="valid_issuers")  # type: ignore[misc]
async def _get_valid_issuers() -> list[str]:
    """Construct the list of valid issuers based on the enabled realms retrieved from OpenRemote.

    Returns:
        The list of valid issuers.

    Remarks:
        The list of valid issuers is cached for 30 seconds to reduce the number of requests to the OpenRemote Manager.
    """
    openremote_service = get_openremote_service()
    realms = openremote_service.get_realms()

    if realms is None:
        logger.warning("No realms could be retrieved from OpenRemote, could not construct valid issuers list")
        # Exception prevents the result from being cached
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Internal server error")

    urls = []
    for realm in realms:
        urls.append(f"{ENV.ML_OR_URL}/auth/realms/{realm.name}")

    logger.info(f"Constructed {len(urls)} valid issuers")
    return urls


def _jwks_cache_key(f: Any, issuer: str, kid: str, *args: Any, **kwargs: Any) -> str:
    return f"{issuer}:{kid}"


@cached(ttl=600, cache=Cache.MEMORY, key_builder=_jwks_cache_key)  # type: ignore[misc]
async def _get_jwks(issuer: str, kid: str) -> dict[str, Any]:
    """Get JWKS from Keycloak based on the issuer URL.

    Args:
        issuer: The issuer URL of the token.
        kid: The Key ID (kid) of the token used to identify the public key.

    Returns:
        The JWKS as a dictionary.

    Raises:
        HTTPException: If the JWKS URL is invalid or the request fails.

    Remarks:
        The JWKS is cached for 10 minutes, allowing for local and offline token validation.
        The issuer URL must follow the pattern: <keycloak_url>/auth/realms/<realm_name>/
    """
    valid_issuers = await _get_valid_issuers()
    if issuer not in valid_issuers:
        raise jwt.exceptions.InvalidTokenError(f"Invalid issuer URL: {issuer}. Not in the list of valid issuers.")

    # Construct JWKS URL using the provided keycloak_url
    jwks_url = f"{issuer}/protocol/openid-connect/certs"

    try:
        async with httpx.AsyncClient(verify=ENV.ML_VERIFY_SSL) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            return cast(dict[str, Any], response.json())

    except httpx.RequestError as e:
        logger.error(f"Error requesting JWKS from {jwks_url}: {e}", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid token") from e
    except Exception as e:
        logger.error(f"Unexpected error processing JWKS response from {jwks_url}: {e}", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid token") from e


async def _verify_jwt_token(token: str, keycloak_url: str) -> dict[str, Any]:
    """Verify the JWT token using the public key obtained from Keycloak's JWKS endpoint.

    Args:
        token: The JWT token to verify.
        keycloak_url: The URL of the Keycloak server.

    Returns:
        The decoded payload of the JWT token.

    Raises:
        HTTPException: If the token is invalid.
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
        if not unverified_header or "kid" not in unverified_header:
            raise jwt.exceptions.InvalidTokenError("Invalid token header: Missing kid")

        kid = unverified_header["kid"]

        # Ensure the token uses the RS256 algorithm (Keycloak default)
        if unverified_header.get("alg") != "RS256":
            raise jwt.exceptions.InvalidTokenError("Invalid token algorithm: Expected RS256")

        # Decode the token without verifying (we don't have the public key yet)
        unverified_payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})

        # Get audience from the token
        audience = unverified_payload.get("aud")
        if not audience:
            raise jwt.exceptions.InvalidTokenError("Audience claim missing in token")

        issuer = unverified_payload.get("iss")
        if not issuer:
            raise jwt.exceptions.InvalidTokenError("Issuer missing in token")

        # Try and get the JWKS for the issuer
        jwks = await _get_jwks(issuer, kid)

        public_key_material: RSAPublicKey | None = None

        # Construct the public key from the JWKS
        for key in jwks.get("keys", []):
            if (
                key.get("kid") == kid
                and key.get("use") == "sig"
                and key.get("kty") == "RSA"
                and re.match(r"^[A-Za-z0-9_-]+$", key.get("kid", ""))
                and key.get("alg") == "RS256"
            ):
                try:
                    public_key_instance = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    if isinstance(public_key_instance, RSAPublicKey):
                        public_key_material = public_key_instance
                        break
                except Exception as e:
                    logger.warning(f"Could not load public key for kid {kid} from JWK: {e}")

        if not public_key_material:
            raise jwt.exceptions.InvalidTokenError(f"Public key not found for kid: {kid}")

        # Finally, verify the token with the public key, verify the audience and issuer
        payload = jwt.decode(
            token,
            public_key_material,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
        )
        return cast(dict[str, Any], payload)

    # Handle common JWT errors
    except jwt.ExpiredSignatureError as e:
        logger.info("Token validation failed: Expired signature")
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Token has expired") from e
    except jwt.InvalidIssuerError as e:
        logger.error("Token validation failed: Invalid issuer", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid token") from e
    except jwt.InvalidAudienceError as e:
        logger.error("Token validation failed: Invalid audience", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid token") from e
    except jwt.exceptions.InvalidTokenError as e:
        logger.error(f"Token validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid token") from e
    except HTTPException as e:
        raise e  # Propagate the HTTPException
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Invalid token") from e


def _has_required_roles(user_payload: KeycloakTokenUserPayload) -> bool:
    """Check if the user has all the required roles. (write:admin, read:admin)"""

    resource_access = user_payload.resource_access.get(RESOURCE_ACCESS_KEY, ResourceRoles(roles=[]))
    return set(REQUIRED_ROLES).issubset(set(resource_access.roles))


def _is_excluded_route(path: str, excluded_routes: list[str]) -> bool:
    """Check if the path matches any of the excluded routes."""

    for route in excluded_routes:
        if route.startswith("/"):
            full_route_with_prefix = ENV.ML_API_ROOT_PATH + route if ENV.ML_API_ROOT_PATH else route
            if path.startswith(full_route_with_prefix):
                return True

        if path.startswith(route):
            return True

    return False


class KeycloakMiddleware(BaseHTTPMiddleware):
    """
    Middleware that verifies Bearer token against OR_ML_KEYCLOAK_URL's JWKS endpoint.
    Routes can be excluded from authentication by providing a list of route paths.
    """

    def __init__(self, app: ASGIApp, keycloak_url: str, excluded_routes: list[str] | None = None):
        super().__init__(app)
        self.excluded_routes: list[str] = list(excluded_routes) if excluded_routes else []
        self.keycloak_url = keycloak_url

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip excluded routes from authentication
        if _is_excluded_route(path, self.excluded_routes):
            return await call_next(request)

        try:
            auth_header = request.headers.get("Authorization")
            token = None

            # Extract the Bearer token from the Authorization header
            if auth_header:
                token_match = re.match(r"^bearer\s+(.+)$", auth_header, re.IGNORECASE)
                if token_match:
                    token = token_match.group(1)

            if not token:
                logger.warning("Authorization header missing or malformed")
                raise HTTPException(
                    status_code=HTTPStatus.UNAUTHORIZED, detail="Missing or malformed Authorization header"
                )

            # Verify the token via the JWKS endpoint
            payload = await _verify_jwt_token(token, self.keycloak_url)
            user_payload = KeycloakTokenUserPayload(**payload)

            # Check if the user has the required roles
            if not _has_required_roles(user_payload):
                logger.warning(
                    f"Insufficient permissions: missing required roles for user: {user_payload.preferred_username}"
                )
                raise HTTPException(
                    status_code=HTTPStatus.FORBIDDEN, detail="Insufficient permissions: missing required roles"
                )

            # Inject the user payload into the request state
            request.state.user = user_payload
        except HTTPException as e:
            logger.warning(f"Auth HTTPException status={e.status_code} detail='{e.detail}'")

            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
            )
        except Exception as e:
            logger.error(f"Unexpected error during token verification dispatch: {e}", exc_info=True)

            return JSONResponse(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                content={"detail": "An unexpected error occurred"},
            )

        # Sucessful, allow request to continue through the middleware
        logger.info(f"Token verified successfully for user: {request.state.user.preferred_username}")
        response = await call_next(request)
        return response
