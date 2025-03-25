import time

from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.ml_models.model_util import FeatureDatapoints, TrainingDataset
from service_ml_forecast.ml_models.prophet_model_provider import ProphetModelProvider
from service_ml_forecast.schemas.model_config import ModelInputAssetAttribute, ModelType, ProphetModelConfig

# Import shared test data from conftest.py
from tests.conftest import TEST_ASSET_ID, TEST_ATTRIBUTE_NAME

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
    model_provider = ProphetModelProvider(PROPHET_MODEL_CONFIG)

    target_datapoints = openremote_client.retrieve_historical_datapoints(
        asset_id=TEST_ASSET_ID,
        attribute_name=TEST_ATTRIBUTE_NAME,
        from_timestamp=1716153600000,
        to_timestamp=int(time.time() * 1000),
    )

    target_feature = FeatureDatapoints(
        attribute_name=TEST_ATTRIBUTE_NAME,
        datapoints=target_datapoints,
    )

    training_dataset = TrainingDataset(
        target=target_feature,
    )

    save_model = model_provider.train_model(training_dataset)
    assert save_model is not None
    assert save_model()


def test_prophet_model_provider_predict(openremote_client: OpenRemoteClient) -> None:
    model_provider = ProphetModelProvider(PROPHET_MODEL_CONFIG)
    assert model_provider.generate_forecast()
