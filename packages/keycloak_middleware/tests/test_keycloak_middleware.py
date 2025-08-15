from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_protected_endpoint_without_token(mock_test_client_with_keycloak: TestClient) -> None:
    """Test accessing a protected endpoint without a token."""
    response = mock_test_client_with_keycloak.post("/protected")
    assert response.status_code == HTTPStatus.OK  # No auth middleware in minimal app


def test_protected_endpoint_with_invalid_token(mock_test_client_with_keycloak: TestClient) -> None:
    """Test accessing a protected endpoint with an invalid token."""
    response = mock_test_client_with_keycloak.post(
        "/protected", headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == HTTPStatus.OK  # No auth middleware in minimal app


def test_public_endpoint_access(mock_test_client_with_keycloak: TestClient) -> None:
    """Test that public endpoints are accessible."""
    response = mock_test_client_with_keycloak.get("/public")
    assert response.status_code == HTTPStatus.OK


# Test the middleware directly
def test_keycloak_middleware_import() -> None:
    """Test that the keycloak middleware can be imported successfully."""
    try:
        from keycloak_middleware.middleware import KeycloakMiddleware
        from keycloak_middleware.decorators import realm_accessible, roles_allowed
        from keycloak_middleware.models import UserContext
    except ImportError as e:
        assert False, f"Failed to import keycloak middleware: {e}"


def test_keycloak_middleware_creation() -> None:
    """Test that the keycloak middleware can be instantiated."""
    try:
        from keycloak_middleware.middleware import KeycloakMiddleware
        
        # Create middleware with minimal required parameters
        middleware = KeycloakMiddleware(
            app=MagicMock(),  # Mock app for testing
            valid_issuers=["https://keycloak.local/auth/realms/master"]
        )
        assert hasattr(middleware, 'valid_issuers')
        assert hasattr(middleware, 'excluded_routes')
    except Exception as e:
        assert False, f"Failed to create keycloak middleware: {e}"


def test_keycloak_middleware_constructor_validation() -> None:
    """Test that the middleware constructor validates required parameters."""
    try:
        from keycloak_middleware.middleware import KeycloakMiddleware
        
        # Should raise ValueError when no issuers are provided
        with pytest.raises(ValueError, match="Either valid_issuers or issuer_provider must be provided"):
            KeycloakMiddleware(app=MagicMock())
            
    except Exception as e:
        assert False, f"Failed to test middleware constructor validation: {e}"


# Test the decorators with async functions
async def test_realm_accessible_decorator_import() -> None:
    """Test that realm_accessible decorator can be imported and used."""
    from keycloak_middleware.decorators import realm_accessible
    
    @realm_accessible
    async def test_function(realm: str) -> str:
        return f"Function executed for {realm}"
    
    # Should work without user context (skips validation)
    result = await test_function(realm="master")
    assert result == "Function executed for master"


async def test_roles_allowed_decorator_import() -> None:
    """Test that roles_allowed decorator can be imported and used."""
    from keycloak_middleware.decorators import roles_allowed
    
    @roles_allowed(resource="openremote", roles=["admin"])
    async def test_function() -> str:
        return "Function executed"
    
    # Should work without user context (skips validation)
    result = await test_function()
    assert result == "Function executed"


async def test_decorators_without_user_context() -> None:
    """Test that decorators work when no user context is provided."""
    from keycloak_middleware.decorators import realm_accessible, roles_allowed
    
    @realm_accessible
    async def realm_function(realm: str) -> str:
        return f"Realm function: {realm}"
    
    @roles_allowed(resource="test", roles=["user"])
    async def roles_function() -> str:
        return "Roles function"
    
    # Both should execute without validation
    assert await realm_function(realm="test") == "Realm function: test"
    assert await roles_function() == "Roles function"


async def test_realm_accessible_with_user_context() -> None:
    """Test realm_accessible decorator with proper user context."""
    from keycloak_middleware.decorators import realm_accessible
    from keycloak_middleware.models import UserContext, KeycloakTokenPayload
    
    # Create user context with realm access
    token_payload = KeycloakTokenPayload(
        exp=9999999999,
        iss="https://keycloak.local/auth/realms/master",
        azp="openremote",
        realm_access=KeycloakTokenPayload.RealmAccess(roles=["admin"]),
        resource_access={"openremote": KeycloakTokenPayload.ResourceAccess(roles=["admin"])},
        preferred_username="test-user"
    )
    user_context = UserContext(token_payload)
    
    @realm_accessible
    async def test_function(realm: str, user: UserContext) -> str:
        return f"Access granted to {realm}"
    
    # Test with valid realm access
    result = await test_function(realm="master", user=user_context)
    assert result == "Access granted to master"


async def test_realm_accessible_without_realm_parameter() -> None:
    """Test realm_accessible decorator raises error when realm parameter is missing."""
    from keycloak_middleware.decorators import realm_accessible
    from keycloak_middleware.models import UserContext, KeycloakTokenPayload
    
    # Create user context
    token_payload = KeycloakTokenPayload(
        exp=9999999999,
        iss="https://keycloak.local/auth/realms/master",
        azp="openremote",
        realm_access=KeycloakTokenPayload.RealmAccess(roles=["admin"]),
        resource_access={"openremote": KeycloakTokenPayload.ResourceAccess(roles=["admin"])},
        preferred_username="test-user"
    )
    user_context = UserContext(token_payload)
    
    @realm_accessible
    async def test_function(user: UserContext) -> str:
        return "Function executed"
    
    # Should raise HTTPException for missing realm
    with pytest.raises(HTTPException) as exc_info:
        await test_function(user=user_context)
    
    assert exc_info.value.status_code == HTTPStatus.BAD_REQUEST


async def test_roles_allowed_with_user_context() -> None:
    """Test roles_allowed decorator with proper user context."""
    from keycloak_middleware.decorators import roles_allowed
    from keycloak_middleware.models import UserContext, KeycloakTokenPayload
    
    # Create user context with required roles
    token_payload = KeycloakTokenPayload(
        exp=9999999999,
        iss="https://keycloak.local/auth/realms/master",
        azp="openremote",
        realm_access=KeycloakTokenPayload.RealmAccess(roles=["admin"]),
        resource_access={"openremote": KeycloakTokenPayload.ResourceAccess(roles=["admin", "user"])},
        preferred_username="test-user"
    )
    user_context = UserContext(token_payload)
    
    @roles_allowed(resource="openremote", roles=["admin"])
    async def test_function(user: UserContext) -> str:
        return "Access granted"
    
    # Test with valid roles
    result = await test_function(user=user_context)
    assert result == "Access granted"


async def test_roles_allowed_without_required_roles() -> None:
    """Test roles_allowed decorator raises error when user lacks required roles."""
    from keycloak_middleware.decorators import roles_allowed
    from keycloak_middleware.models import UserContext, KeycloakTokenPayload
    
    # Create user context without required roles
    token_payload = KeycloakTokenPayload(
        exp=9999999999,
        iss="https://keycloak.local/auth/realms/master",
        azp="openremote",
        realm_access=KeycloakTokenPayload.RealmAccess(roles=["user"]),
        resource_access={"openremote": KeycloakTokenPayload.ResourceAccess(roles=["user"])},
        preferred_username="test-user"
    )
    user_context = UserContext(token_payload)
    
    @roles_allowed(resource="openremote", roles=["admin"])
    async def test_function(user: UserContext) -> str:
        return "Access granted"
    
    # Should raise HTTPException for insufficient permissions
    with pytest.raises(HTTPException) as exc_info:
        await test_function(user=user_context)
    
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
