import json
import logging.config
import shutil
import tempfile
import threading
from collections.abc import Generator
from http import HTTPStatus
from pathlib import Path

import pytest
import respx
import uvicorn

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.config import ENV
from service_ml_forecast.logging_config import LOGGING_CONFIG
from service_ml_forecast.main import app
from service_ml_forecast.models.model_config import ProphetModelConfig
from service_ml_forecast.services.model_config_service import ModelConfigService
from service_ml_forecast.services.model_storage_service import ModelStorageService
from service_ml_forecast.services.openremote_data_service import OpenRemoteDataService

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

# FASTAPI SERVER
FASTAPI_TEST_HOST = "127.0.0.1"
FASTAPI_TEST_PORT = 8007

# Create a temporary directory for tests
TEST_TMP_DIR: Path = Path(tempfile.mkdtemp(prefix="service_ml_forecast_test_"))

ENV.ML_BASE_DIR = TEST_TMP_DIR
ENV.ML_MODELS_DIR = TEST_TMP_DIR / "models"
ENV.ML_CONFIGS_DIR = TEST_TMP_DIR / "configs"


# Clean up temporary directory after each test call
@pytest.fixture(scope="function", autouse=True)
def cleanup_test_tmp_dir() -> Generator[None]:
    yield
    shutil.rmtree(TEST_TMP_DIR, ignore_errors=True)


# Create an instance of our FastAPI server for use in E2E tests
@pytest.fixture(scope="session")
def fastapi_server() -> Generator[None]:
    """Run the fastapi server via uvicorn in a separate thread."""
    config = uvicorn.Config(app=app, host=FASTAPI_TEST_HOST, port=FASTAPI_TEST_PORT, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run)
    thread.daemon = True
    thread.start()
    yield

    # Allow the server to shut down gracefully
    server.should_exit = True


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
        respx_mock.post("/auth/realms/master/protocol/openid-connect/token").mock(
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
def config_service() -> ModelConfigService:
    return ModelConfigService()


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
def or_data_service(openremote_client: OpenRemoteClient) -> OpenRemoteDataService:
    return OpenRemoteDataService(openremote_client)


@pytest.fixture
def mock_or_data_service(mock_openremote_client: OpenRemoteClient) -> OpenRemoteDataService:
    return OpenRemoteDataService(mock_openremote_client)
