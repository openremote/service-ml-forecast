import pytest

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.ml.ml_model_provider_factory import MLModelProviderFactory
from service_ml_forecast.models.ml_data_models import FeatureDatapoints, ForecastFeatureSet, TrainingFeatureSet
from service_ml_forecast.models.ml_model_config import ProphetMLModelConfig


def test_model_provider_train(
    prophet_basic_config: ProphetMLModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    model_provider = MLModelProviderFactory.create_provider(prophet_basic_config)

    model = model_provider.train_model(
        TrainingFeatureSet(
            target=FeatureDatapoints(
                attribute_name=prophet_basic_config.target.attribute_name, datapoints=windspeed_mock_datapoints
            )
        )
    )
    assert model is not None

    # Save the model
    assert model_provider.save_model(model)

    # Assert the model file exists
    assert prophet_basic_config.id is not None
    assert model_provider.load_model(prophet_basic_config.id) is not None


def test_model_provider_predict(prophet_basic_config: ProphetMLModelConfig) -> None:
    model_provider = MLModelProviderFactory.create_provider(prophet_basic_config)

    forecast = model_provider.generate_forecast()

    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) > 0


def test_model_provider_train_with_regressor(
    prophet_multi_variable_config: ProphetMLModelConfig,
    tariff_mock_datapoints: list[AssetDatapoint],
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    # Create the model provider for the multi-variable model
    model_provider = MLModelProviderFactory.create_provider(prophet_multi_variable_config)

    # Create the target feature datapoints
    target_feature_datapoints = FeatureDatapoints(
        attribute_name=prophet_multi_variable_config.target.attribute_name, datapoints=tariff_mock_datapoints
    )

    # Create the regressor feature datapoints
    assert prophet_multi_variable_config.regressors is not None
    assert len(prophet_multi_variable_config.regressors) > 0

    regressor_feature_datapoints = [
        FeatureDatapoints(attribute_name=regressor.attribute_name, datapoints=windspeed_mock_datapoints)
        for regressor in prophet_multi_variable_config.regressors
    ]

    # Train the model with the target and regressor feature datapoints
    model = model_provider.train_model(
        TrainingFeatureSet(target=target_feature_datapoints, regressors=regressor_feature_datapoints)
    )
    assert model is not None

    # Save the model
    assert model_provider.save_model(model)

    # Assert whether we can load the model now
    assert model_provider.load_model(prophet_multi_variable_config.id) is not None


def test_model_provider_predict_with_regressor_datapoints(
    prophet_multi_variable_config: ProphetMLModelConfig, prophet_basic_config: ProphetMLModelConfig
) -> None:
    # Generate a forecast for the regressor
    windspeed_model_provider = MLModelProviderFactory.create_provider(prophet_basic_config)
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
    tariff_model_provider = MLModelProviderFactory.create_provider(prophet_multi_variable_config)
    tariff_forecast = tariff_model_provider.generate_forecast(forecast_featureset)

    # Assert future datapoints are generated
    assert tariff_forecast is not None
    assert tariff_forecast.datapoints is not None
    assert len(tariff_forecast.datapoints) > 0


def test_model_provider_predict_with_missing_regressor_datapoints(
    prophet_multi_variable_config: ProphetMLModelConfig,
) -> None:
    model_provider = MLModelProviderFactory.create_provider(prophet_multi_variable_config)

    with pytest.raises(ValueError):
        model_provider.generate_forecast()
