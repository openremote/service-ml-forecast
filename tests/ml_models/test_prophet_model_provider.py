import json
from pathlib import Path

import pytest

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.config import env
from service_ml_forecast.ml_models.model_provider_factory import ModelProviderFactory
from service_ml_forecast.ml_models.model_util import FeatureDatapoints, TrainingFeatureSet
from service_ml_forecast.schemas.model_config import ProphetModelConfig
from tests.conftest import PROJECT_ROOT


@pytest.fixture
def prophet_test_config() -> ProphetModelConfig:
    config_path = Path(__file__).parent / "resources/prophet_basic_test_config.json"
    with open(config_path) as f:
        return ProphetModelConfig(**json.load(f))


@pytest.fixture
def prophet_regressor_test_config() -> ProphetModelConfig:
    config_path = Path(__file__).parent / "resources/prophet_regressor_test_config.json"
    with open(config_path) as f:
        return ProphetModelConfig(**json.load(f))


def test_model_provider_train(prophet_test_config: ProphetModelConfig) -> None:
    tariff_data_path = Path(__file__).parent / "resources/mock_datapoints_tariff.json"
    with open(tariff_data_path) as f:
        tariff_data: list[AssetDatapoint] = json.load(f)

    model_provider = ModelProviderFactory.create_provider(prophet_test_config)

    save_model = model_provider.train_model(
        TrainingFeatureSet(
            target=FeatureDatapoints(attribute_name=prophet_test_config.target.attribute_name, datapoints=tariff_data)
        )
    )
    assert save_model is not None
    assert save_model()

    assert prophet_test_config.id is not None
    model_file_exists = Path(f"{PROJECT_ROOT}/{env.MODELS_DIR}/{prophet_test_config.id}.json")
    assert model_file_exists.exists()


def test_model_provider_predict(prophet_test_config: ProphetModelConfig) -> None:
    model_provider = ModelProviderFactory.create_provider(prophet_test_config)

    forecast = model_provider.generate_forecast()

    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) > 0


def test_model_provider_train_with_regressor(prophet_regressor_test_config: ProphetModelConfig) -> None:
    tariff_data_path = Path(__file__).parent / "resources/mock_datapoints_tariff.json"
    with open(tariff_data_path) as f:
        tariff_data: list[AssetDatapoint] = json.load(f)

    wind_speed_data_path = Path(__file__).parent / "resources/mock_datapoints_windspeed.json"
    with open(wind_speed_data_path) as f:
        wind_speed_data: list[AssetDatapoint] = json.load(f)

    model_provider = ModelProviderFactory.create_provider(prophet_regressor_test_config)

    target_feature_datapoints = FeatureDatapoints(
        attribute_name=prophet_regressor_test_config.target.attribute_name, datapoints=tariff_data
    )

    assert prophet_regressor_test_config.regressors is not None
    assert len(prophet_regressor_test_config.regressors) > 0

    regressor_feature_datapoints = [
        FeatureDatapoints(attribute_name=regressor.attribute_name, datapoints=wind_speed_data)
        for regressor in prophet_regressor_test_config.regressors
    ]

    save_model = model_provider.train_model(
        TrainingFeatureSet(target=target_feature_datapoints, regressors=regressor_feature_datapoints)
    )
    assert save_model is not None
    assert save_model()
