import uuid

import pytest

from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.ml_models.prophet_model_provider import ProphetModelProvider
from service_ml_forecast.schemas.model_config import ModelInputAssetAttribute, ModelType, ProphetModelConfig

TEST_ASSET_ID = "44ORIhkDVAlT97dYGUD9n5"
TEST_ATTRIBUTE_NAME = "powerTotalConsumers"

PROPHET_MODEL_CONFIG = ProphetModelConfig(
    id=str(uuid.uuid4()),
    name="Power Total Consumers Forecast",
    type=ModelType.PROPHET,
    predicted_asset_attribute=ModelInputAssetAttribute(
        asset_id=TEST_ASSET_ID,
        attribute_name=TEST_ATTRIBUTE_NAME,
        oldest_timestamp=1716153600000,
        newest_timestamp=1742750287563,
    ),
    forecast_interval="PT1H",  # 1 hour
    training_interval="PT1D",  # 1 day
    forecast_period="PT7D",  # 7 days
    forecast_datapoint_interval="PT1H",  # 1 hour
)


# TODO: Replace with a mocked client, and add mocked paths for the retrieve_historical_datapoints method
# We will use a local csv file for the datapoints (for testing purposes)
@pytest.fixture
def openremote_client() -> OpenRemoteClient:
    """Create an OpenRemote client for testing against a real instance."""
    from service_ml_forecast.config import env

    client = OpenRemoteClient(
        openremote_url=env.OPENREMOTE_URL,
        keycloak_url=env.OPENREMOTE_KEYCLOAK_URL,
        service_user=env.OPENREMOTE_SERVICE_USER,
        service_user_secret=env.OPENREMOTE_SERVICE_USER_SECRET,
    )

    # Skip tests if OpenRemote API is not available
    if not client.health_check():
        pytest.skip(reason="OpenRemote API not available")

    return client


def test_prophet_model_provider_train(openremote_client: OpenRemoteClient) -> None:
    model_provider = ProphetModelProvider(PROPHET_MODEL_CONFIG, openremote_client)
    # We can only assert whether the training was successful,
    # the predict method will then be tested for correctness
    assert model_provider.train()


def test_prophet_model_provider_train_no_datapoints(openremote_client: OpenRemoteClient) -> None:
    config = PROPHET_MODEL_CONFIG.model_copy(deep=True)
    config.predicted_asset_attribute.newest_timestamp = 1716153600000
    config.predicted_asset_attribute.oldest_timestamp = 1716153600000

    model_provider = ProphetModelProvider(config, openremote_client)
    # We can only assert whether the training was successful,
    # the predict method will then be tested for correctness
    assert not model_provider.train()
