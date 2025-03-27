import json
from pathlib import Path

import pytest

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.config import env
from service_ml_forecast.ml_models.model_provider_factory import ModelProviderFactory
from service_ml_forecast.ml_models.model_util import FeatureDatapoints, ForecastFeatureSet, TrainingFeatureSet
from service_ml_forecast.schemas.model_config import ProphetModelConfig
from tests.conftest import PROJECT_ROOT


@pytest.fixture
def prophet_basic_config() -> ProphetModelConfig:
    config_path = Path(__file__).parent / "resources/prophet_windspeed_config.json"
    with open(config_path) as f:
        return ProphetModelConfig(**json.load(f))


@pytest.fixture
def prophet_multi_variable_config() -> ProphetModelConfig:
    config_path = Path(__file__).parent / "resources/prophet_tariff_config.json"
    with open(config_path) as f:
        return ProphetModelConfig(**json.load(f))


def test_model_provider_train(prophet_basic_config: ProphetModelConfig) -> None:
    windspeed_data_path = Path(__file__).parent / "resources/mock_datapoints_windspeed.json"
    with open(windspeed_data_path) as f:
        windspeed_data: list[AssetDatapoint] = json.load(f)

    model_provider = ModelProviderFactory.create_provider(prophet_basic_config)

    model = model_provider.train_model(
        TrainingFeatureSet(
            target=FeatureDatapoints(
                attribute_name=prophet_basic_config.target.attribute_name, datapoints=windspeed_data
            )
        )
    )
    assert model is not None
    assert model_provider.save_model(model)

    assert prophet_basic_config.id is not None
    model_file_exists = Path(f"{PROJECT_ROOT}/{env.MODELS_DIR}/{prophet_basic_config.id}.json")
    assert model_file_exists.exists()


def test_model_provider_predict(prophet_basic_config: ProphetModelConfig) -> None:
    model_provider = ModelProviderFactory.create_provider(prophet_basic_config)

    forecast = model_provider.generate_forecast()

    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) > 0


def test_model_provider_train_with_regressor(prophet_multi_variable_config: ProphetModelConfig) -> None:
    wind_speed_data_path = Path(__file__).parent / "resources/mock_datapoints_windspeed.json"
    with open(wind_speed_data_path) as f:
        wind_speed_data: list[AssetDatapoint] = json.load(f)

    tariff_data_path = Path(__file__).parent / "resources/mock_datapoints_tariff.json"
    with open(tariff_data_path) as f:
        tariff_data: list[AssetDatapoint] = json.load(f)

    # Create the model provider for the multi-variable model
    model_provider = ModelProviderFactory.create_provider(prophet_multi_variable_config)

    # Create the target feature datapoints
    target_feature_datapoints = FeatureDatapoints(
        attribute_name=prophet_multi_variable_config.target.attribute_name, datapoints=tariff_data
    )

    # Create the regressor feature datapoints
    assert prophet_multi_variable_config.regressors is not None
    assert len(prophet_multi_variable_config.regressors) > 0

    regressor_feature_datapoints = [
        FeatureDatapoints(attribute_name=regressor.attribute_name, datapoints=wind_speed_data)
        for regressor in prophet_multi_variable_config.regressors
    ]

    # Train the model with the target and regressor feature datapoints
    model = model_provider.train_model(
        TrainingFeatureSet(target=target_feature_datapoints, regressors=regressor_feature_datapoints)
    )
    assert model is not None
    assert model_provider.save_model(model)

    assert prophet_multi_variable_config.id is not None
    model_file_exists = Path(f"{PROJECT_ROOT}/{env.MODELS_DIR}/{prophet_multi_variable_config.id}.json")
    assert model_file_exists.exists()


def test_model_provider_predict_with_regressor_datapoints(
    prophet_multi_variable_config: ProphetModelConfig, prophet_basic_config: ProphetModelConfig
) -> None:
    # Generate a forecast for the regressor
    windspeed_model_provider = ModelProviderFactory.create_provider(prophet_basic_config)
    windspeed_forecast = windspeed_model_provider.generate_forecast()

    # Assert future datapoints are generated
    assert windspeed_forecast is not None
    assert windspeed_forecast.datapoints is not None
    assert len(windspeed_forecast.datapoints) > 0

    windspeed_feature_datapoints = FeatureDatapoints(
        attribute_name=prophet_basic_config.target.attribute_name, datapoints=windspeed_forecast.datapoints
    )
    forecast_featureset = ForecastFeatureSet(regressors=[windspeed_feature_datapoints])

    # Generate a forecast for the target whilst providing the regressor forecast for the future datapoints
    tariff_model_provider = ModelProviderFactory.create_provider(prophet_multi_variable_config)
    tariff_forecast = tariff_model_provider.generate_forecast(forecast_featureset)

    # Assert future datapoints are generated
    assert tariff_forecast is not None
    assert tariff_forecast.datapoints is not None
    assert len(tariff_forecast.datapoints) > 0


def test_model_provider_predict_with_missing_regressor_datapoints(
    prophet_multi_variable_config: ProphetModelConfig,
) -> None:
    model_provider = ModelProviderFactory.create_provider(prophet_multi_variable_config)

    with pytest.raises(ValueError):
        model_provider.generate_forecast()
