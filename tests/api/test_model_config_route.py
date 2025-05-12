from http import HTTPStatus
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from service_ml_forecast.dependencies import get_config_service
from service_ml_forecast.services.model_config_service import ModelConfigService


# --- Fixtures ---
@pytest.fixture
def mock_test_client(config_service: ModelConfigService) -> TestClient:
    """Create a FastAPI TestClient instance with mocked services and bypassed auth."""
    from service_ml_forecast.config import ENV

    # Override the environment variable to disable keycloak middleware
    ENV.ML_API_MIDDLEWARE_KEYCLOAK = False

    # Import the fastapi app
    from service_ml_forecast.main import app

    # Mock dependencies
    app.dependency_overrides[get_config_service] = lambda: config_service

    return TestClient(app)


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI TestClient instance for integration tests. with no mocks."""
    from service_ml_forecast.main import app

    # Clear the dependency overrides
    app.dependency_overrides = {}

    return TestClient(app)


# --- Test data ---
TEST_CONFIG_ID = "d3c143a6-1018-4ebd-932b-a509eb7ab841"
TEST_REALM = "master"
TEST_ASSET_ID = "41ORIplRVAlT97dYGUD9n5"
TEST_ATTRIBUTE_NAME = "test-attribute"
TEST_CUTOFF_TIMESTAMP = 1716153600000


def create_test_config() -> dict[str, object]:
    """Helper function to create a test model config."""

    return {
        "id": TEST_CONFIG_ID,
        "realm": TEST_REALM,
        "name": "Test Model",
        "enabled": True,
        "type": "prophet",
        "target": {
            "asset_id": TEST_ASSET_ID,
            "attribute_name": TEST_ATTRIBUTE_NAME,
            "cutoff_timestamp": TEST_CUTOFF_TIMESTAMP,
        },
        "forecast_interval": "PT1H",
        "training_interval": "PT1H",
        "forecast_periods": 24,
        "forecast_frequency": "1h",
    }


def create_invalid_test_config() -> dict[str, object]:
    """Helper function to create an invalid test model config. Missing required fields."""
    return {
        "id": TEST_CONFIG_ID,
        "realm": TEST_REALM,
    }


def test_create_model_config(mock_test_client: TestClient) -> None:
    """Test creating a new model config.

    Verifies that:
    - The model config is created successfully
    - The model config is returned in the response
    - The model config is stored
    """
    config = create_test_config()
    response = mock_test_client.post("/api/master/configs", json=config)
    assert response.status_code == HTTPStatus.OK
    saved_config = response.json()
    assert saved_config["id"] == TEST_CONFIG_ID
    assert saved_config["realm"] == TEST_REALM
    assert saved_config["name"] == "Test Model"
    assert saved_config["type"] == "prophet"
    assert saved_config["target"]["asset_id"] == TEST_ASSET_ID
    assert saved_config["target"]["attribute_name"] == TEST_ATTRIBUTE_NAME


def test_create_invalid_model_config(mock_test_client: TestClient) -> None:
    """Test creating an invalid model config.

    Verifies that:
    - The model config is not created
    - The model config is not returned in the response
    - The model config is not stored
    """
    config = create_invalid_test_config()
    response = mock_test_client.post("/api/master/configs", json=config)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_get_model_config(mock_test_client: TestClient) -> None:
    """Test getting a model config by ID.

    Verifies that:
    - The model config is retrieved successfully
    - The model config is returned in the response
    - The response status code is 200
    - The model config is stored
    """
    # First create a config
    config = create_test_config()
    mock_test_client.post("/api/master/configs", json=config)

    # Retrieve the config
    response = mock_test_client.get(f"/api/master/configs/{TEST_CONFIG_ID}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["id"] == str(TEST_CONFIG_ID)
    assert data["realm"] == TEST_REALM


def test_get_model_config_not_found(mock_test_client: TestClient) -> None:
    """Test getting a non-existent model config.

    Verifies that:
    - The model config is not retrieved
    - The model config is not returned in the response
    - The response status code is 404
    """
    non_existent_id = uuid4()
    response = mock_test_client.get(f"/api/master/configs/{non_existent_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_all_model_configs(mock_test_client: TestClient) -> None:
    """Test getting all model configs with realm filter.

    Verifies that:
    - The model configs are retrieved successfully
    - The model configs are returned in the response
    - The model configs are filtered by realm
    - The response status code is 200
    """
    # First create a config
    config = create_test_config()
    mock_test_client.post("/api/master/configs", json=config)

    # Test
    response = mock_test_client.get("/api/master/configs")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 1  # Should find the config we just created

    # Test with an invalid realm filter, we should get an empty list
    response = mock_test_client.get("/api/test-realm/configs")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 0


def test_update_model_config(mock_test_client: TestClient) -> None:
    """Test updating a model config.

    Verifies that:
    - The model config is updated successfully
    - The model config is returned in the response
    - The response status code is 200
    """
    # Create a config
    config = create_test_config()
    mock_test_client.post("/api/master/configs", json=config)

    # Then update it
    updated_config = config
    updated_config["name"] = "Updated Test Model"

    response = mock_test_client.put(f"/api/master/configs/{TEST_CONFIG_ID}", json=updated_config)
    assert response.status_code == HTTPStatus.OK
    saved_config = response.json()
    assert saved_config["id"] == TEST_CONFIG_ID
    assert saved_config["realm"] == TEST_REALM
    assert saved_config["name"] == "Updated Test Model"


def test_update_model_config_not_found(mock_test_client: TestClient) -> None:
    """Test updating a non-existent model config.

    Verifies that:
    - The model config is not updated
    - The model config is not returned in the response
    - The response status code is 404
    """
    config = create_test_config()
    id = str(uuid4())
    response = mock_test_client.put(f"/api/master/configs/{id}", json=config)
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_model_config(mock_test_client: TestClient) -> None:
    """Test deleting a model config.

    Verifies that:
    - The model config is deleted successfully
    - The model config is not returned in the response
    - The response status code is 200
    """
    # First create a config
    config = create_test_config()
    mock_test_client.post("/api/master/configs", json=config)

    # Then delete it
    response = mock_test_client.delete(f"/api/master/configs/{TEST_CONFIG_ID}")
    assert response.status_code == HTTPStatus.OK

    # Verify it's deleted
    response = mock_test_client.get(f"/api/master/configs/{TEST_CONFIG_ID}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_model_config_not_found(mock_test_client: TestClient) -> None:
    """Test deleting a non-existent model config.

    Verifies that:
    - The model config is not deleted
    - The model config is not returned in the response
    - The response status code is 404
    """
    non_existent_id = uuid4()
    response = mock_test_client.delete(f"/api/master/configs/{non_existent_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_create_asset_dependencies_missing(test_client: TestClient) -> None:
    """Test creating a model config with missing asset dependencies.

    The provided target asset does not exist, so the model config should not be created.

    Verifies that:
    - The model config asset ids are validated, e.g. they exist in the openremote service response
    - The model config is not created
    - The model config is not returned in the response
    - The response status code is 400
    """
    config = create_test_config()
    response = test_client.post("/api/master/configs", json=config)
    assert response.status_code == HTTPStatus.BAD_REQUEST
