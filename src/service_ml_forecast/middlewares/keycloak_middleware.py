import logging
from http import HTTPStatus
from typing import Any, cast
from urllib.parse import urlparse

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from service_ml_forecast.config import ENV

logger = logging.getLogger(__name__)


async def _get_jwks(keycloak_url: str, issuer: str) -> dict[str, Any]:
    """Get JWKS from Keycloak based on the issuer URL."""

    try:
        parsed_url = urlparse(issuer)
        path_segments = [segment for segment in parsed_url.path.split("/") if segment]

        realms_index = path_segments.index("realms")
        if realms_index + 1 < len(path_segments):
            realm_name = path_segments[realms_index + 1]
        else:
            raise ValueError("Path structure invalid: expected realm name after 'realms'")

        if not realm_name:
            raise ValueError("Realm name cannot be empty.")

        # Construct the JWKS URL using the base URL from env and the extracted realm
        jwks_url = f"{keycloak_url}/realms/{realm_name}/protocol/openid-connect/certs"

    except Exception as e:
        logger.error(f"Error constructing JWKS URL from issuer '{issuer}': {e}", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="An unexpected error occurred") from e

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            return cast(dict[str, Any], response.json())

    except Exception as e:
        logger.error(f"Unexpected error processing JWKS response from {jwks_url}: {e}", exc_info=True)
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="An unexpected error occurred") from e


async def _verify_jwt_token(token: str, keycloak_url: str) -> dict[str, Any]:
    """Verify the JWT token using the public key obtained from Keycloak's JWKS endpoint."""

    try:
        unverified_header = jwt.get_unverified_header(token)
        if not unverified_header or "kid" not in unverified_header:
            raise jwt.exceptions.InvalidTokenError("Invalid token header")

        kid = unverified_header["kid"]

        # Decode the token without verifying (we dont have the public key yet)
        unverified_payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
        issuer = unverified_payload.get("iss")
        if not issuer:
            raise jwt.exceptions.InvalidTokenError("Issuer missing in token")

        # Get audience from the token
        audience = unverified_payload.get("aud")
        if not audience:
            raise jwt.exceptions.InvalidTokenError("Audience claim missing in token")

        # Ensure issuer begins with the OpenRemote URL
        if not issuer.startswith(ENV.ML_OR_URL):
            raise jwt.exceptions.InvalidTokenError("Issuer does not match expected keycloak URL")

        # Try and get the JWKS
        jwks = await _get_jwks(keycloak_url, issuer)
        public_key_material: RSAPublicKey | None = None

        # Construct the public key from the JWKS
        for key in jwks.get("keys", []):
            if key.get("kid") == kid and key.get("use") == "sig" and key.get("kty") == "RSA":
                try:
                    public_key_instance = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    if isinstance(public_key_instance, RSAPublicKey):
                        public_key_material = public_key_instance
                        break
                except Exception as e:
                    logger.warning(f"Could not load public key for kid {kid} from JWK: {e}")

        if not public_key_material:
            raise jwt.exceptions.InvalidTokenError(f"Public key not found for kid: {kid}")

        # Decode the token with the public key
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
        raise HTTPException(status_code=401, detail="Token has expired") from e
    except jwt.exceptions.InvalidTokenError as e:
        logger.warning(f"Token validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e
    except HTTPException as e:
        raise e  # Propagate the HTTPException
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Failed to validate token") from e


class KeycloakMiddleware(BaseHTTPMiddleware):
    """
    Verifies Bearer token against OR_ML_KEYCLOAK_URL's JWKS endpoint.
    Attributes:
        excluded_paths: A set of relative paths that do not require authentication.
    """

    def __init__(self, app: ASGIApp, keycloak_url: str, excluded_paths: list[str] | None = None):
        super().__init__(app)
        self.excluded_paths: set[str] = set(excluded_paths) if excluded_paths else set()
        self.keycloak_url = keycloak_url

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Handle OPTIONS requests for CORS preflight
        if request.method == "OPTIONS":
            return Response(
                status_code=HTTPStatus.OK,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type",
                },
            )

        # Check if the request path is in the excluded paths (with or without the API root path)
        for excluded_path in self.excluded_paths:
            if request.url.path.startswith(ENV.ML_API_ROOT_PATH + excluded_path) or request.url.path.startswith(
                excluded_path
            ):
                return await call_next(request)

        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header:
            parts = auth_header.split()
            header_split_length = 2
            if len(parts) == header_split_length and parts[0].lower() == "bearer":
                token = parts[1]

        if not token:
            logger.warning("Authorization header missing")
            return JSONResponse(
                status_code=HTTPStatus.UNAUTHORIZED,
                content={"detail": "Not authenticated or invalid format"},
            )

        try:
            payload = await _verify_jwt_token(token, self.keycloak_url)
            request.state.user = payload
        except HTTPException as e:
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

        return await call_next(request)
