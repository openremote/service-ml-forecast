# Standard Library Imports
import logging
from typing import Any, Dict, cast
from urllib.parse import urlparse

# Third-Party Imports
import httpx
import jwt
import jwt.exceptions
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import HTTPException
# Removed unused OAuth2PasswordBearer
# from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from service_ml_forecast.config import ENV

logger = logging.getLogger(__name__)

# Get JWKS from Keycloak based on the issuer URL
async def _get_jwks(issuer: str) -> Dict[str, Any]:
    try:
        parsed_url = urlparse(issuer)
        # Split path by '/', removing empty strings from leading/trailing slashes
        path_segments = [segment for segment in parsed_url.path.split('/') if segment]

        # Find the index of 'realms'
        realms_index = path_segments.index('realms')
        # The realm name should be the next segment
        if realms_index + 1 < len(path_segments):
            realm_name = path_segments[realms_index + 1]
        else:
            # Raise if 'realms' is the last segment
            raise ValueError("Path structure invalid: expected realm name after 'realms'")

        if not realm_name: # Defensive check
            raise ValueError("Realm name cannot be empty.")

        # Construct the JWKS URL using the base URL from env and the extracted realm
        # Ensure the base URL doesn't have a trailing slash to avoid double slashes
        base_url = ENV.ML_OR_KEYCLOAK_URL.rstrip('/')
        jwks_url = f"{base_url}/realms/{realm_name}/protocol/openid-connect/certs"

    except ValueError as e:
        # Handles case where 'realms' is not found or realm_name is missing/empty
        logger.error(f"Could not extract realm name from issuer path '{parsed_url.path}': {e}", exc_info=False)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: Could not determine realm from issuer '{issuer}'")
    except Exception as e:
        # Catch any other unexpected errors during URL construction
        logger.error(f"Error constructing JWKS URL from issuer '{issuer}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            return cast(Dict[str, Any], response.json())
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    except Exception as e:
        logger.error(f"Unexpected error processing JWKS response from {jwks_url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Verify the JWT token using the public key obtained from Keycloak's JWKS endpoint
async def _verify_jwt_token(token: str) -> Dict[str, Any]:
    try:
        unverified_header = jwt.get_unverified_header(token)
        if not unverified_header or 'kid' not in unverified_header:
            raise jwt.exceptions.InvalidTokenError("Invalid token header")

        kid = unverified_header['kid']

        unverified_payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
        issuer = unverified_payload.get('iss')
        if not issuer:
            raise jwt.exceptions.InvalidTokenError("Issuer missing in token")

        # Try and get the JWKS
        jwks = await _get_jwks(issuer)
        public_key_material: RSAPublicKey | None = None

        for key in jwks.get('keys', []):
            if key.get('kid') == kid and key.get('use') == 'sig' and key.get('kty') == 'RSA':
                try:
                    public_key_instance = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    if isinstance(public_key_instance, RSAPublicKey):
                        public_key_material = public_key_instance
                        break
                except Exception as e:
                    logger.warning(f"Could not load public key for kid {kid} from JWK: {e}")

        if not public_key_material:
             raise jwt.exceptions.InvalidTokenError(f"Public key not found for kid: {kid}")

        payload = jwt.decode(
            token,
            public_key_material,
            algorithms=["RS256"],
            issuer=issuer,
        )
        return cast(Dict[str, Any], payload)

    # Handle common JWT errors
    except jwt.ExpiredSignatureError as e:
        logger.info("Token validation failed: Expired signature")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.exceptions.InvalidTokenError as e:
        logger.warning(f"Token validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Token validation failed unexpectedly")


class KeycloakMiddleware(BaseHTTPMiddleware):
    """
    Verifies Bearer token against Keycloak realm's JWKS endpoint.
    Attributes:
        excluded_paths: A set of URL paths that bypass authentication.
    """
    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: list[str] | None = None
    ):
        super().__init__(app)
        self.excluded_paths: set[str] = set(excluded_paths) if excluded_paths else set()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]

        if not token:
            logger.debug("Authorization header missing or invalid Bearer format.")
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated or invalid format"},
            )

        try:
            payload = await _verify_jwt_token(token)
            request.state.user = payload
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
            )
        except Exception as e:
            logger.error(f"Unexpected error during token verification dispatch: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "An unexpected error occurred during authentication."},
            )

        return await call_next(request)
