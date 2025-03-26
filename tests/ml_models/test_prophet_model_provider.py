import json
import time
from pathlib import Path

import pytest

from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.ml_models.model_provider_factory import ModelProviderFactory
from service_ml_forecast.ml_models.model_util import FeatureDatapoints, TrainingFeatureSet
from service_ml_forecast.schemas.model_config import ProphetModelConfig


@pytest.fixture
def prophet_model_config() -> ProphetModelConfig:
    config_path = Path(__file__).parent / "prophet_model_config.json"
    with open(config_path) as f:
        return ProphetModelConfig(**json.load(f))


@pytest.fixture
def prophet_model_config_with_regressors() -> ProphetModelConfig:
    config_path = Path(__file__).parent / "prophet_model_regressor_config.json"
    with open(config_path) as f:
        return ProphetModelConfig(**json.load(f))


def test_prophet_model_provider_train(
    openremote_client: OpenRemoteClient, prophet_model_config: ProphetModelConfig
) -> None:
    model_provider = ModelProviderFactory.create_provider(prophet_model_config)

    target_datapoints = openremote_client.retrieve_historical_datapoints(
        asset_id=prophet_model_config.target.asset_id,
        attribute_name=prophet_model_config.target.attribute_name,
        from_timestamp=prophet_model_config.target.cutoff_timestamp,
        to_timestamp=int(time.time() * 1000),
    )

    target_feature = FeatureDatapoints(
        attribute_name=prophet_model_config.target.attribute_name,
        datapoints=target_datapoints,
    )

    training_dataset = TrainingFeatureSet(
        target=target_feature,
    )

    save_model = model_provider.train_model(training_dataset)
    assert save_model is not None
    assert save_model()


def test_prophet_model_provider_predict(
    openremote_client: OpenRemoteClient, prophet_model_config: ProphetModelConfig
) -> None:
    model_provider = ModelProviderFactory.create_provider(prophet_model_config)

    forecast = model_provider.generate_forecast()

    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) > 0
