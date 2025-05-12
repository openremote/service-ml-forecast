from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
from fastapi import HTTPException
from fastapi.testclient import TestClient

from tests.api.test_model_config_route import create_test_config


def test_create_model_without_token(mock_test_client_with_keycloak: TestClient) -> None:
    """Test creating a model config without a token.

    Verifies that:
    - The request is rejected with a 400 Bad Request status code
    """
    config = create_test_config()
    response = mock_test_client_with_keycloak.post("/api/master/configs", json=config)
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_create_model_with_invalid_token(mock_test_client_with_keycloak: TestClient) -> None:
    """Test creating a model config with an invalid token.

    Verifies that:
    - The request is rejected with a 401 Unauthorized status code
    """
    config = create_test_config()
    response = mock_test_client_with_keycloak.post(
        "/api/master/configs", json=config, headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@patch("service_ml_forecast.middlewares.keycloak_middleware._verify_jwt_token")
def test_token_with_missing_required_roles(
    mock_verify_jwt: AsyncMock, mock_test_client_with_keycloak: TestClient
) -> None:
    """Test accessing a protected endpoint with a token missing required roles.

    Verifies that:
    - The request is rejected with a 403 Forbidden status code when the token
      is valid but doesn't have the required roles
    """
    # Mock the token verification to return a valid payload but with insufficient roles
    mock_verify_jwt.return_value = {
        "name": "Test User",
        "resource_access": {
            "openremote": {
                "roles": ["some-other-role"]  # Missing required write:admin and read:admin roles
            }
        },
    }

    config = create_test_config()
    response = mock_test_client_with_keycloak.post(
        "/api/master/configs", json=config, headers={"Authorization": "Bearer valid-token-with-insufficient-roles"}
    )

    # Should be forbidden (not unauthorized) because token is valid but lacks permissions
    assert response.status_code == HTTPStatus.FORBIDDEN
    assert "Insufficient permissions" in response.json()["detail"]


def test_malformed_authorization_header(mock_test_client_with_keycloak: TestClient) -> None:
    """Test with malformed authorization headers.

    Verifies that:
    - The request is rejected with a 400 Bad Request status code when the Authorization header is malformed
    """
    config = create_test_config()

    # Test with empty Authorization header
    response = mock_test_client_with_keycloak.post("/api/master/configs", json=config, headers={"Authorization": ""})
    assert response.status_code == HTTPStatus.BAD_REQUEST

    # Test with Authorization header without Bearer prefix
    response = mock_test_client_with_keycloak.post(
        "/api/master/configs", json=config, headers={"Authorization": "token-without-bearer-prefix"}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST

    # Test with Authorization header with wrong prefix
    response = mock_test_client_with_keycloak.post(
        "/api/master/configs", json=config, headers={"Authorization": "Basic some-token"}
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


@patch("service_ml_forecast.middlewares.keycloak_middleware._verify_jwt_token")
def test_token_with_expired_signature(mock_verify_jwt: AsyncMock, mock_test_client_with_keycloak: TestClient) -> None:
    """Test with an expired token.

    Verifies that:
    - The request is rejected with a 401 Unauthorized status code when the token has expired
    """
    # Mock the token verification to raise an HTTPException with the correct status code
    mock_verify_jwt.side_effect = HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail="Token has expired")

    config = create_test_config()
    response = mock_test_client_with_keycloak.post(
        "/api/master/configs", json=config, headers={"Authorization": "Bearer expired-token"}
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert "expired" in response.json()["detail"].lower()


@patch("jwt.get_unverified_header")
def test_token_with_invalid_structure(mock_get_header: MagicMock, mock_test_client_with_keycloak: TestClient) -> None:
    """Test with a token that has an invalid structure.

    Verifies that:
    - The request is rejected with a 401 Unauthorized status code when the token structure is invalid
    """
    # Mock jwt.get_unverified_header to raise an exception for invalid token structure
    mock_get_header.side_effect = jwt.exceptions.DecodeError("Invalid token structure")

    config = create_test_config()
    response = mock_test_client_with_keycloak.post(
        "/api/master/configs", json=config, headers={"Authorization": "Bearer invalid-structure-token"}
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert "invalid token" in response.json()["detail"].lower()


def test_excluded_route_bypasses_authentication(mock_test_client_with_keycloak: TestClient) -> None:
    """Test that excluded routes bypass authentication.

    Verifies that:
    - Requests to excluded routes are processed without authentication
    - No token is required for these routes
    """
    response = mock_test_client_with_keycloak.get("/docs")
    assert response.status_code == HTTPStatus.OK
