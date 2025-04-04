from uuid import UUID

import httpx

from tests.conftest import FASTAPI_SERVER_HOST, FASTAPI_SERVER_PORT

# Test data
TEST_CONFIG_ID = "d3c143a6-1018-4ebd-932b-a509eb7ab841"
TEST_REALM = "master"
TEST_ASSET_ID = "41ORIplRVAlT97dYGUD9n5"
TEST_ATTRIBUTE_NAME = "test-attribute"
TEST_CUTOFF_TIMESTAMP = 1716153600000
BASE_URL = f"http://{FASTAPI_SERVER_HOST}:{FASTAPI_SERVER_PORT}"


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


def test_create_model_config(fastapi_server: None) -> None:
    """Test creating a new model config."""

    config = create_test_config()

    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/model/config/", json=config)
        assert response.status_code == httpx.codes.OK
        saved_config = response.json()
        assert saved_config["id"] == TEST_CONFIG_ID
        assert saved_config["realm"] == TEST_REALM
        assert saved_config["name"] == "Test Model"
        assert saved_config["type"] == "prophet"
        assert saved_config["target"]["asset_id"] == TEST_ASSET_ID
        assert saved_config["target"]["attribute_name"] == TEST_ATTRIBUTE_NAME


def test_get_model_config(fastapi_server: None) -> None:
    """Test getting a model config by ID."""
    with httpx.Client() as client:
        # First create a config
        config = create_test_config()
        client.post(f"{BASE_URL}/model/config/", json=config)

        # Retrieve the config
        response = client.get(f"{BASE_URL}/model/config/{TEST_CONFIG_ID}")
        assert response.status_code == httpx.codes.OK
        data = response.json()
        assert data["id"] == str(TEST_CONFIG_ID)
        assert data["realm"] == TEST_REALM


def test_get_model_config_not_found(fastapi_server: None) -> None:
    """Test getting a non-existent model config."""
    non_existent_id = UUID("87654321-4321-8765-4321-876543210987")
    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/model/config/{non_existent_id}")
        assert response.status_code == httpx.codes.NOT_FOUND


def test_get_all_model_configs(fastapi_server: None) -> None:
    """Test getting all model configs with realm filter."""
    with httpx.Client() as client:
        # First create a config
        config = create_test_config()
        client.post(f"{BASE_URL}/model/config/", json=config)

        # Test without realm filter
        response = client.get(f"{BASE_URL}/model/config/")
        assert response.status_code == httpx.codes.OK
        data = response.json()
        assert len(data) == 1  # Should find the config we just created

        # Test with an invalid realm filter, we should get an empty list
        response = client.get(f"{BASE_URL}/model/config/?realm={'test-realm'}")
        assert response.status_code == httpx.codes.OK
        data = response.json()
        assert len(data) == 0


def test_update_model_config(fastapi_server: None) -> None:
    """Test updating a model config."""
    with httpx.Client() as client:
        # Create a config
        config = create_test_config()
        client.post(f"{BASE_URL}/model/config/", json=config)

        # Then update it
        updated_config = config
        updated_config["name"] = "Updated Test Model"

        response = client.put(f"{BASE_URL}/model/config/", json=updated_config)
        assert response.status_code == httpx.codes.OK
        saved_config = response.json()
        assert saved_config["id"] == TEST_CONFIG_ID
        assert saved_config["realm"] == TEST_REALM
        assert saved_config["name"] == "Updated Test Model"


def test_delete_model_config(fastapi_server: None) -> None:
    """Test deleting a model config."""
    with httpx.Client() as client:
        # First create a config
        config = create_test_config()
        client.post(f"{BASE_URL}/model/config/", json=config)

        # Then delete it
        response = client.delete(f"{BASE_URL}/model/config/{TEST_CONFIG_ID}")
        assert response.status_code == httpx.codes.OK
        assert response.json() is True

        # Verify it's deleted
        response = client.get(f"{BASE_URL}/model/config/{TEST_CONFIG_ID}")
        assert response.status_code == httpx.codes.NOT_FOUND
