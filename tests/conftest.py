import logging.config
from http import HTTPStatus

import pytest
import respx

from service_ml_forecast import find_project_root
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.config import env
from service_ml_forecast.logging_config import LOGGING_CONFIG

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

# Overwrite model and config storage paths for testing purposes
env.MODELS_DIR = "/tests/.tmp/models"
env.CONFIGS_DIR = "/tests/.tmp/configs"


# FIXTURES
@pytest.fixture
def openremote_client() -> OpenRemoteClient:
    """Create an OpenRemote client for testing against a real instance."""
    from service_ml_forecast.config import env

    try:
        client = OpenRemoteClient(
            openremote_url=env.OPENREMOTE_URL,
            keycloak_url=env.OPENREMOTE_KEYCLOAK_URL,
            service_user=env.OPENREMOTE_SERVICE_USER,
            service_user_secret=env.OPENREMOTE_SERVICE_USER_SECRET,
        )
        if not client.health_check():
            pytest.skip(reason="OpenRemote API not available")

        return client

    except Exception as e:
        pytest.skip(reason=f"Failed to create OpenRemoteClient: {e}")


@pytest.fixture
def mock_openremote_client() -> OpenRemoteClient:
    """Create a mock OpenRemote client with mocked authentication."""
    with respx.mock(base_url=MOCK_KEYCLOAK_URL) as respx_mock:
        # Mock the token endpoint
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
