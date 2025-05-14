import importlib
import json
import logging.config
import shutil
import sys
import tempfile
import types
from collections.abc import Generator
from http import HTTPStatus
from pathlib import Path

import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.config import DIRS
from service_ml_forecast.dependencies import get_config_service
from service_ml_forecast.logging_config import LOGGING_CONFIG
from service_ml_forecast.models.model_config import ProphetModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService
from service_ml_forecast.services.model_storage_service import ModelStorageService
from service_ml_forecast.services.openremote_service import OpenRemoteService

logging.config.dictConfig(LOGGING_CONFIG)

# Common test data used across multiple tests
TEST_ASSET_ID = "44ORIhkDVAlT97dYGUD9n5"
TEST_ATTRIBUTE_NAME = "powerTotalConsumers"
TEST_OLDEST_TIMESTAMP = 1716153600000  # 2024-05-20 00:00:00 UTC

# Mock URLs and credentials
MOCK_OPENREMOTE_URL = "https://openremote.local"
MOCK_KEYCLOAK_URL = "https://keycloak.local/auth"
MOCK_SERVICE_USER = "service_user"
MOCK_SERVICE_USER_SECRET = "service_user_secret"
MOCK_ACCESS_TOKEN = "mock_access_token"
MOCK_TOKEN_EXPIRY_SECONDS = 60

# FASTAPI SERVER
FASTAPI_TEST_HOST = "127.0.0.1"
FASTAPI_TEST_PORT = 8007

# Create a temporary directory for tests
TEST_TMP_DIR: Path = Path(tempfile.mkdtemp(prefix="service_ml_forecast_test_"))

# Override directory constants for tests
DIRS.ML_BASE_DIR = TEST_TMP_DIR
DIRS.ML_MODELS_DATA_DIR = TEST_TMP_DIR / "models"
DIRS.ML_CONFIGS_DATA_DIR = TEST_TMP_DIR / "configs"


# Clean up temporary directory after each test call
@pytest.fixture(scope="function", autouse=True)
def cleanup_test_tmp_dir() -> Generator[None]:
    yield
    shutil.rmtree(TEST_TMP_DIR, ignore_errors=True)


@pytest.fixture
def openremote_client() -> OpenRemoteClient | None:
    """Create an OpenRemote client for testing against a real instance."""
    from service_ml_forecast.config import ENV

    try:
        client = OpenRemoteClient(
            openremote_url=ENV.ML_OR_URL,
            keycloak_url=ENV.ML_OR_KEYCLOAK_URL,
            service_user=ENV.ML_OR_SERVICE_USER,
            service_user_secret=ENV.ML_OR_SERVICE_USER_SECRET,
        )
        if not client.health_check():
            pytest.skip(reason="Unable to reach the OpenRemote Manager API")

        return client

    except Exception as e:
        pytest.skip(reason=f"Failed to create OpenRemote client: {e}")


@pytest.fixture
def mock_openremote_client() -> OpenRemoteClient | None:
    """Create a mock OpenRemote client with mocked authentication."""
    with respx.mock(base_url=MOCK_KEYCLOAK_URL) as respx_mock:
        # Mock the authentication endpoint
        respx_mock.post("/realms/master/protocol/openid-connect/token").mock(
            return_value=respx.MockResponse(
                HTTPStatus.OK,
                json={
                    "access_token": MOCK_ACCESS_TOKEN,
                    "token_type": "Bearer",
                    "expires_in": MOCK_TOKEN_EXPIRY_SECONDS,
                },
            ),
        )

        client = OpenRemoteClient(
            openremote_url=MOCK_OPENREMOTE_URL,
            keycloak_url=MOCK_KEYCLOAK_URL,
            service_user=MOCK_SERVICE_USER,
            service_user_secret=MOCK_SERVICE_USER_SECRET,
        )
        return client


@pytest.fixture
def config_service(mock_openremote_service: OpenRemoteService) -> ModelConfigService:
    return ModelConfigService(mock_openremote_service)


@pytest.fixture
def model_storage() -> ModelStorageService:
    return ModelStorageService()


@pytest.fixture
def prophet_basic_config() -> ProphetModelConfig:
    config_path = Path(__file__).parent / "ml/resources/prophet-windspeed-config.json"
    with open(config_path) as f:
        return ProphetModelConfig(**json.load(f))


@pytest.fixture
def prophet_multi_variable_config() -> ProphetModelConfig:
    config_path = Path(__file__).parent / "ml/resources/prophet-tariff-config.json"
    with open(config_path) as f:
        return ProphetModelConfig(**json.load(f))


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


@pytest.fixture
def openremote_service(openremote_client: OpenRemoteClient) -> OpenRemoteService:
    return OpenRemoteService(openremote_client)


@pytest.fixture
def mock_openremote_service(mock_openremote_client: OpenRemoteClient) -> OpenRemoteService:
    service = OpenRemoteService(mock_openremote_client)

    # Mock get assets by ids, allows external validation to go through
    def mock_get_assets_by_ids(self: OpenRemoteService, realm: str, asset_ids: list[str]) -> list[dict[str, str]]:
        return [{"id": asset_id, "realm": realm} for asset_id in asset_ids]

    service.get_assets_by_ids = types.MethodType(mock_get_assets_by_ids, service)  # type: ignore[method-assign]
    return service


def get_fresh_app(keycloak_enabled: bool) -> FastAPI:
    """Get a fresh instance of the app with the given keycloak setting."""
    # Remove any cached modules to ensure we get a fresh app
    for module in list(sys.modules.keys()):
        if module.startswith("service_ml_forecast.main"):
            del sys.modules[module]

    # Set environment variable
    from service_ml_forecast.config import ENV

    ENV.ML_API_MIDDLEWARE_KEYCLOAK = keycloak_enabled

    # Import the app fresh
    import service_ml_forecast.main

    importlib.reload(service_ml_forecast.main)

    return service_ml_forecast.main.app


@pytest.fixture
def mock_test_client(config_service: ModelConfigService) -> TestClient:
    """Create a FastAPI TestClient instance with mocked services and disabled auth."""
    app = get_fresh_app(keycloak_enabled=False)

    # Mock dependencies
    app.dependency_overrides[get_config_service] = lambda: config_service

    return TestClient(app)


@pytest.fixture
def mock_test_client_with_keycloak(config_service: ModelConfigService) -> TestClient:
    """Create a FastAPI TestClient instance with mocked services and enabled auth."""
    app = get_fresh_app(keycloak_enabled=True)

    # Mock dependencies
    app.dependency_overrides[get_config_service] = lambda: config_service

    return TestClient(app)
