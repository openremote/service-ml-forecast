from http import HTTPStatus
from uuid import uuid4

from fastapi.testclient import TestClient

# Test data
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
    """Test creating a new model config."""
    config = create_test_config()
    response = mock_test_client.post("/api/model/configs", json=config)
    assert response.status_code == HTTPStatus.OK
    saved_config = response.json()
    assert saved_config["id"] == TEST_CONFIG_ID
    assert saved_config["realm"] == TEST_REALM
    assert saved_config["name"] == "Test Model"
    assert saved_config["type"] == "prophet"
    assert saved_config["target"]["asset_id"] == TEST_ASSET_ID
    assert saved_config["target"]["attribute_name"] == TEST_ATTRIBUTE_NAME


def test_create_invalid_model_config(mock_test_client: TestClient) -> None:
    """Test creating an invalid model config."""
    config = create_invalid_test_config()
    response = mock_test_client.post("/api/model/configs", json=config)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_get_model_config(mock_test_client: TestClient) -> None:
    """Test getting a model config by ID."""
    # First create a config
    config = create_test_config()
    mock_test_client.post("/api/model/configs", json=config)

    # Retrieve the config
    response = mock_test_client.get(f"/api/model/configs/{TEST_CONFIG_ID}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["id"] == str(TEST_CONFIG_ID)
    assert data["realm"] == TEST_REALM


def test_get_model_config_not_found(mock_test_client: TestClient) -> None:
    """Test getting a non-existent model config."""
    non_existent_id = uuid4()
    response = mock_test_client.get(f"/api/model/configs/{non_existent_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_all_model_configs(mock_test_client: TestClient) -> None:
    """Test getting all model configs with realm filter."""
    # First create a config
    config = create_test_config()
    mock_test_client.post("/api/model/configs", json=config)

    # Test
    response = mock_test_client.get(f"/api/model/configs?realm={TEST_REALM}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 1  # Should find the config we just created

    # Test with an invalid realm filter, we should get an empty list
    response = mock_test_client.get("/api/model/configs?realm=test-realm")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 0


def test_update_model_config(mock_test_client: TestClient) -> None:
    """Test updating a model config."""
    # Create a config
    config = create_test_config()
    mock_test_client.post("/api/model/configs", json=config)

    # Then update it
    updated_config = config
    updated_config["name"] = "Updated Test Model"

    response = mock_test_client.put(f"/api/model/configs/{TEST_CONFIG_ID}", json=updated_config)
    assert response.status_code == HTTPStatus.OK
    saved_config = response.json()
    assert saved_config["id"] == TEST_CONFIG_ID
    assert saved_config["realm"] == TEST_REALM
    assert saved_config["name"] == "Updated Test Model"


def test_update_model_config_not_found(mock_test_client: TestClient) -> None:
    """Test updating a non-existent model config."""
    config = create_test_config()
    id = str(uuid4())
    response = mock_test_client.put(f"/api/model/configs/{id}", json=config)
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_model_config(mock_test_client: TestClient) -> None:
    """Test deleting a model config."""
    # First create a config
    config = create_test_config()
    mock_test_client.post("/api/model/configs", json=config)

    # Then delete it
    response = mock_test_client.delete(f"/api/model/configs/{TEST_CONFIG_ID}")
    assert response.status_code == HTTPStatus.OK

    # Verify it's deleted
    response = mock_test_client.get(f"/api/model/configs/{TEST_CONFIG_ID}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_model_config_not_found(mock_test_client: TestClient) -> None:
    """Test deleting a non-existent model config."""
    non_existent_id = uuid4()
    response = mock_test_client.delete(f"/api/model/configs/{non_existent_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_create_asset_dependencies_missing(test_client: TestClient) -> None:
    """Test creating a model config with missing asset dependencies."""
    config = create_test_config()
    response = test_client.post("/api/model/configs", json=config)
    assert response.status_code == HTTPStatus.BAD_REQUEST  # Bad Request
