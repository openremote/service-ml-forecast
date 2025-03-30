import json
import logging.config
from collections.abc import Generator
from http import HTTPStatus
from pathlib import Path

import pytest
import respx

from service_ml_forecast import find_project_root
from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.config import env
from service_ml_forecast.logging_config import LOGGING_CONFIG
from service_ml_forecast.models.ml_config import ProphetMLConfig
from service_ml_forecast.services.ml_config_storage_service import MLConfigStorageService
from service_ml_forecast.util.fs_util import FsUtil

PROJECT_ROOT = find_project_root()

logging.config.dictConfig(LOGGING_CONFIG)

# Common test data used across multiple tests
TEST_ASSET_ID = "44ORIhkDVAlT97dYGUD9n5"
TEST_ATTRIBUTE_NAME = "powerTotalConsumers"
TEST_OLDEST_TIMESTAMP = 1716153600000  # 2024-05-20 00:00:00 UTC

# Mock URLs and credentials
MOCK_OPENREMOTE_URL = "https://openremote.local"
MOCK_KEYCLOAK_URL = "https://keycloak.local"
MOCK_SERVICE_USER = "service_user"
MOCK_SERVICE_USER_SECRET = "service_user_secret"
MOCK_ACCESS_TOKEN = "mock_access_token"
MOCK_TOKEN_EXPIRY_SECONDS = 60


TEST_TMP_DIR = "/tests/.tmp"

# Overwrite model and config storage paths for testing purposes
env.MODELS_DIR = f"{TEST_TMP_DIR}/models"
env.CONFIGS_DIR = f"{TEST_TMP_DIR}/configs"


def cleanup_test_configs() -> None:
    """Cleanup test configs after all tests have run."""
    FsUtil.delete_directory(env.CONFIGS_DIR)


def cleanup_test_models() -> None:
    """Cleanup test models after all tests have run."""
    FsUtil.delete_directory(env.MODELS_DIR)


# Automatically clean up test files after all tests have run
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_tmp_dir() -> Generator[None, None, None]:
    """Cleanup test files after all tests have run."""
    yield
    FsUtil.delete_directory(TEST_TMP_DIR)


# Create an OpenRemote client for testing against a real instance
@pytest.fixture
def openremote_client() -> OpenRemoteClient | None:
    """Create an OpenRemote client for testing against a real instance."""
    from service_ml_forecast.config import ENV

    try:
        client = OpenRemoteClient(
            openremote_url=ENV.OPENREMOTE_URL,
            keycloak_url=ENV.OPENREMOTE_KEYCLOAK_URL,
            service_user=ENV.OPENREMOTE_SERVICE_USER,
            service_user_secret=ENV.OPENREMOTE_SERVICE_USER_SECRET,
        )
        if not client.health_check():
            pytest.skip(reason="Unable to reach the OpenRemote Manager API")

        return client

    except Exception as e:
        pytest.skip(reason=f"Failed to create OpenRemote client: {e}")


# Create a mock OpenRemote client with mocked authentication
@pytest.fixture
def mock_openremote_client() -> OpenRemoteClient | None:
    """Create a mock OpenRemote client with mocked authentication."""
    with respx.mock(base_url=MOCK_KEYCLOAK_URL) as respx_mock:
        # Mock the authentication endpoint
        respx_mock.post("/auth/realms/master/protocol/openid-connect/token").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json={
                    "access_token": MOCK_ACCESS_TOKEN,
                    "token_type": "Bearer",
                    "expires_in": MOCK_TOKEN_EXPIRY_SECONDS,
                },
            )
        )

        client = OpenRemoteClient(
            openremote_url=MOCK_OPENREMOTE_URL,
            keycloak_url=MOCK_KEYCLOAK_URL,
            service_user=MOCK_SERVICE_USER,
            service_user_secret=MOCK_SERVICE_USER_SECRET,
        )
        return client


# Fixture for the MLConfigStorageService
@pytest.fixture
def ml_config_storage_service() -> MLConfigStorageService:
    return MLConfigStorageService()


@pytest.fixture
def prophet_basic_config() -> ProphetMLConfig:
    config_path = Path(__file__).parent / "ml/resources/prophet-windspeed-config.json"
    with open(config_path) as f:
        return ProphetMLConfig(**json.load(f))


@pytest.fixture
def prophet_multi_variable_config() -> ProphetMLConfig:
    config_path = Path(__file__).parent / "ml/resources/prophet-tariff-config.json"
    with open(config_path) as f:
        return ProphetMLConfig(**json.load(f))


@pytest.fixture
def windspeed_mock_datapoints() -> list[AssetDatapoint]:
    windspeed_data_path = Path(__file__).parent / "ml/resources/mock-datapoints-windspeed.json"
    with open(windspeed_data_path) as f:
        datapoints: list[AssetDatapoint] = json.load(f)
        return datapoints


@pytest.fixture
def tariff_mock_datapoints() -> list[AssetDatapoint]:
    tariff_data_path = Path(__file__).parent / "ml/resources/mock-datapoints-tariff.json"
    with open(tariff_data_path) as f:
        datapoints: list[AssetDatapoint] = json.load(f)
        return datapoints
