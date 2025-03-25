
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.ml_models.prophet_model_provider import ProphetModelProvider
from service_ml_forecast.schemas.model_config import ModelInputAssetAttribute, ModelType, ProphetModelConfig

TEST_ASSET_ID = "44ORIhkDVAlT97dYGUD9n5"
TEST_ATTRIBUTE_NAME = "powerTotalConsumers"

PROPHET_MODEL_CONFIG = ProphetModelConfig(
    id="d3c119a6-1018-4ebd-932b-a509eb7ab730",
    name="Power Total Consumers Forecast",
    type=ModelType.PROPHET,
    target=ModelInputAssetAttribute(
        asset_id=TEST_ASSET_ID,
        attribute_name=TEST_ATTRIBUTE_NAME,
        cutoff_timestamp=1716153600000,
    ),
    forecast_interval="PT1H",  # 1 hour
    training_interval="PT1D",  # 1 day
    forecast_period="PT7D",  # 7 days
    forecast_datapoint_interval="PT1H",  # 1 hour
)


PROPHET_MODEL_CONFIG_WITH_REGRESSORS = PROPHET_MODEL_CONFIG.model_copy(deep=True)
PROPHET_MODEL_CONFIG_WITH_REGRESSORS.id = "d3c119a6-1018-4ebd-932b-a509eb7ab731"
PROPHET_MODEL_CONFIG_WITH_REGRESSORS.regressors = [
    ModelInputAssetAttribute(
        asset_id=TEST_ASSET_ID,
        attribute_name=TEST_ATTRIBUTE_NAME,
        cutoff_timestamp=1716153600000,
    )
]


def test_prophet_model_provider_train(openremote_client: OpenRemoteClient) -> None:
    model_provider = ProphetModelProvider(PROPHET_MODEL_CONFIG, openremote_client)
    assert model_provider.train_model()


def test_prophet_model_provider_train_no_datapoints(openremote_client: OpenRemoteClient) -> None:
    config = PROPHET_MODEL_CONFIG.model_copy(deep=True)
    # override the timestamp to a time where no datapoints are available
    config.predicted_asset_attribute.cutoff_timestamp = 2716153600000  # somewhere random in the future

    model_provider = ProphetModelProvider(config, openremote_client)
    assert not model_provider.train_model()


def test_prophet_model_provider_predict(openremote_client: OpenRemoteClient) -> None:
    model_provider = ProphetModelProvider(PROPHET_MODEL_CONFIG, openremote_client)
    assert model_provider.generate_forecast()
