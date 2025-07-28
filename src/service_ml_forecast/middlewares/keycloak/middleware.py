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

Authentication and Authorization Steps:
1. Check if the request path matches any excluded routes
2. Extract and validate the Bearer token from the Authorization header
3. Validate token format before processing
4. Extract and validate the Key ID (kid) from the token header
5. Extract and validate the issuer URL from the token
6. Validate the issuer URL against the list of valid issuers
7. Construct the JWKS URL using the validated issuer URL
8. Get the JWKS from the JWKS endpoint with proper caching
9. Validate JWKS keys structures
10. Verify the token signature using the public key from JWKS
11. Inject the validated user context into the request state
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
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from service_ml_forecast.config import ENV
from service_ml_forecast.middlewares.keycloak.constants import (
    ERROR_INTERNAL_SERVER_ERROR,
    ERROR_INVALID_TOKEN,
    ERROR_MISSING_AUTH_HEADER,
    ERROR_TOKEN_EXPIRED,
    ERROR_UNEXPECTED_ERROR,
    JWKS_CACHE_TTL_SECONDS,
    JWKS_ENDPOINT_PATH,
    JWKS_REQUEST_TIMEOUT_SECONDS,
    JWT_ALGORITHM_RS256,
    JWT_KEY_TYPE_RSA,
    JWT_KEY_USE_SIGNATURE,
)
from service_ml_forecast.middlewares.keycloak.models import IssuerProvider, KeycloakTokenPayload, UserContext

logger = logging.getLogger(__name__)


def _jwks_cache_key(f: Any, issuer: str, kid: str, *args: Any, **kwargs: Any) -> str:
    """Generate cache key for JWKS based on issuer and key ID."""
    return f"{issuer}:{kid}"


@cached(ttl=JWKS_CACHE_TTL_SECONDS, cache=Cache.MEMORY, key_builder=_jwks_cache_key)  # type: ignore[misc]
async def _get_jwks(issuer: str, kid: str, valid_issuers: list[str]) -> dict[str, Any]:
    """Get JWKS from Keycloak based on the issuer URL.

    Args:
        issuer: The issuer URL of the token.
        kid: The Key ID (kid) of the token used to identify the public key.
        valid_issuers: List of valid issuer URLs to validate against.

    Returns:
        The JWKS as a dictionary.

    Raises:
        HTTPException: If the JWKS URL is invalid or the request fails.

    Remarks:
        The JWKS is cached for 10 minutes, allowing for local and offline token validation.
        The issuer URL must follow the pattern: <keycloak_url>/auth/realms/<realm_name>/
    """
    if issuer not in valid_issuers:
        raise jwt.exceptions.InvalidTokenError(f"Invalid issuer URL: {issuer}. Not in the list of valid issuers.")

    # Construct JWKS URL using the provided keycloak_url
    jwks_url = f"{issuer}{JWKS_ENDPOINT_PATH}"

    try:
        async with httpx.AsyncClient(verify=ENV.ML_VERIFY_SSL, timeout=JWKS_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            return cast(dict[str, Any], response.json())

    except httpx.RequestError as e:
        logger.error(f"Error requesting JWKS from {jwks_url}: {e}", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=ERROR_INVALID_TOKEN) from e
    except Exception as e:
        logger.error(f"Unexpected error processing JWKS response from {jwks_url}: {e}", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=ERROR_INVALID_TOKEN) from e


async def _verify_jwt_token(token: str, valid_issuers: list[str]) -> dict[str, Any]:
    """Verify the JWT token using the public key obtained from Keycloak's JWKS endpoint.

    Args:
        token: The JWT token to verify.
        valid_issuers: List of valid issuer URLs to validate against.

    Returns:
        The decoded payload of the JWT token.

    Raises:
        HTTPException: If the token is invalid.
    """
    try:
        # Extract and validate token header
        unverified_header = jwt.get_unverified_header(token)
        if not unverified_header or "kid" not in unverified_header:
            raise jwt.exceptions.InvalidTokenError("Invalid token header: Missing kid")

        kid = unverified_header["kid"]

        # Ensure the token uses the RS256 algorithm (Keycloak default)
        if unverified_header.get("alg") != JWT_ALGORITHM_RS256:
            raise jwt.exceptions.InvalidTokenError("Invalid token algorithm: Expected RS256")

        # Decode the token without verifying (we don't have the public key yet)
        unverified_payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})

        # Extract required claims
        audience = unverified_payload.get("aud")
        if not audience:
            raise jwt.exceptions.InvalidTokenError("Audience claim missing in token")

        issuer = unverified_payload.get("iss")
        if not issuer:
            raise jwt.exceptions.InvalidTokenError("Issuer missing in token")

        # Get the JWKS for the issuer
        jwks = await _get_jwks(issuer, kid, valid_issuers)

        # Find the matching public key from JWKS
        public_key_material: RSAPublicKey | None = None
        for key in jwks.get("keys", []):
            # Validate key properties
            is_valid_key = (
                key.get("kid") == kid
                and key.get("use") == JWT_KEY_USE_SIGNATURE
                and key.get("kty") == JWT_KEY_TYPE_RSA
                and key.get("alg") == JWT_ALGORITHM_RS256
                and re.match(r"^[A-Za-z0-9_-]+$", key.get("kid", ""))
            )

            if is_valid_key:
                try:
                    public_key_instance = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    if isinstance(public_key_instance, RSAPublicKey):
                        public_key_material = public_key_instance
                        break
                except Exception as e:
                    logger.warning(f"Could not load public key for kid {kid} from JWK: {e}")

        if not public_key_material:
            raise jwt.exceptions.InvalidTokenError(f"Public key not found for kid: {kid}")

        # Verify the token with the public key, audience and issuer
        payload = jwt.decode(
            token,
            public_key_material,
            algorithms=[JWT_ALGORITHM_RS256],
            audience=audience,
            issuer=issuer,
        )
        return cast(dict[str, Any], payload)

    # Handle common JWT errors
    except jwt.ExpiredSignatureError as e:
        logger.info("Token validation failed: Expired signature")
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=ERROR_TOKEN_EXPIRED) from e
    except jwt.InvalidIssuerError as e:
        logger.error("Token validation failed: Invalid issuer", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=ERROR_INVALID_TOKEN) from e
    except jwt.InvalidAudienceError as e:
        logger.error("Token validation failed: Invalid audience", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=ERROR_INVALID_TOKEN) from e
    except jwt.exceptions.InvalidTokenError as e:
        logger.error(f"Token validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=ERROR_INVALID_TOKEN) from e
    except HTTPException as e:
        raise e  # Propagate the HTTPException
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=ERROR_INVALID_TOKEN) from e


def _is_excluded_route(path: str, excluded_routes: list[str]) -> bool:
    """Check if the path matches any of the excluded routes."""
    for route in excluded_routes:
        # Handle routes that start with "/" by adding API root path prefix
        if route.startswith("/"):
            full_route_with_prefix = ENV.ML_API_ROOT_PATH + route if ENV.ML_API_ROOT_PATH else route
            if path.startswith(full_route_with_prefix):
                return True

        # Direct path matching
        if path.startswith(route):
            return True

    return False


class KeycloakMiddleware(BaseHTTPMiddleware):
    """
    Middleware that verifies Bearer token against Keycloak's JWKS endpoint.
    Routes can be excluded from authentication by providing a list of route paths.

    The middleware can be configured with either:
    - A static list of valid issuer URLs
    - A callable function that returns a list of valid issuer URLs
    - A callable function that returns None (for dynamic issuer validation)
    """

    def __init__(
        self,
        app: ASGIApp,
        excluded_routes: list[str] | None = None,
        valid_issuers: list[str] | None = None,
        issuer_provider: IssuerProvider | None = None,
    ):
        super().__init__(app)
        self.excluded_routes: list[str] = list(excluded_routes) if excluded_routes else []
        self.valid_issuers: list[str] | None = valid_issuers
        self.issuer_provider: IssuerProvider | None = issuer_provider

        if self.valid_issuers is None and self.issuer_provider is None:
            raise ValueError("Either valid_issuers or issuer_provider must be provided")

    async def _get_valid_issuers(self) -> list[str]:
        """Get the list of valid issuers, either from static list or dynamic provider."""
        if self.valid_issuers is not None:
            return self.valid_issuers

        if self.issuer_provider is not None:
            issuers = self.issuer_provider()
            if issuers is None:
                logger.warning("Issuer provider returned None, no valid issuers available")
                raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=ERROR_INTERNAL_SERVER_ERROR)
            return issuers

        # This should never happen due to constructor validation
        raise ValueError("No issuer configuration available")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip excluded routes from authentication
        if _is_excluded_route(path, self.excluded_routes):
            return await call_next(request)

        try:
            # Extract Bearer token from Authorization header
            auth_header = request.headers.get("Authorization")
            token = None

            if auth_header:
                token_match = re.match(r"^bearer\s+(.+)$", auth_header, re.IGNORECASE)
                if token_match:
                    token = token_match.group(1)

            if not token:
                logger.warning("Authorization header missing or malformed")
                raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=ERROR_MISSING_AUTH_HEADER)

            # Get valid issuers and verify the token
            valid_issuers = await self._get_valid_issuers()
            payload = await _verify_jwt_token(token, valid_issuers)

            # Create user context and inject into request state
            token_payload = KeycloakTokenPayload(**payload)
            user_context = UserContext(token_payload)
            request.state.user = user_context

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
                content={"detail": ERROR_UNEXPECTED_ERROR},
            )

        response = await call_next(request)
        return response

    @staticmethod
    def get_user_context(request: Request) -> UserContext | None:
        """Get the user context from the request state.

        Returns:
            The UserContext object if the request has a valid user context, None otherwise.
        """
        if not hasattr(request.state, "user"):
            return None
        return cast(UserContext, request.state.user)
