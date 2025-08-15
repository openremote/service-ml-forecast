import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Mock URLs for testing
MOCK_KEYCLOAK_URL = "https://keycloak.local/auth/realms/master"


def create_minimal_app() -> FastAPI:
    """Create a minimal FastAPI app for testing."""
    app = FastAPI()
    
    @app.post("/protected")
    def protected_endpoint() -> dict[str, str]:
        return {"message": "Protected endpoint"}
    
    @app.get("/public")
    def public_endpoint() -> dict[str, str]:
        return {"message": "Public endpoint"}
    
    return app


@pytest.fixture
def mock_test_client_with_keycloak() -> TestClient:
    """Create a FastAPI TestClient instance with a minimal app."""
    app = create_minimal_app()
    return TestClient(app)
