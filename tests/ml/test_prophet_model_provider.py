from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, ForecastDataSet, TrainingDataSet
from service_ml_forecast.models.model_config import ProphetModelConfig


def test_train_and_predict(
    prophet_basic_config: ProphetModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test the basic functionality of a Prophet model provider with a single variable.

    Verifies that:
    - The model trains successfully with the provided data
    - The trained model can be saved and loaded
    - The model can generate forecasts with non-empty results
    """
    model_provider = ModelProviderFactory.create_provider(prophet_basic_config)

    # Train the model
    model = model_provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=prophet_basic_config.target.attribute_name,
                datapoints=windspeed_mock_datapoints,
            ),
        ),
    )
    assert model is not None

    # Save the model
    model_provider.save_model(model)
    assert prophet_basic_config.id is not None
    assert model_provider.load_model(prophet_basic_config.id) is not None

    # Generate the forecast
    forecast = model_provider.generate_forecast()
    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) > 0


def test_train_and_predict_with_regressor(
    prophet_multi_variable_config: ProphetModelConfig,
    prophet_basic_config: ProphetModelConfig,
    tariff_mock_datapoints: list[AssetDatapoint],
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test Prophet model with external regressors for multi-variable forecasting.

    Verifies that:
    - Both models train successfully (regressor and target)
    - Models can be saved and then loaded
    - The windspeed forecast can be used as a regressor input for the tariff model
    - The tariff model generates valid forecasts when provided with regressor data
    """
    # Create the windspeed model
    windspeed_provider = ModelProviderFactory.create_provider(prophet_basic_config)
    windspeed_target_datapoints = AssetFeatureDatapoints(
        feature_name=prophet_basic_config.target.attribute_name,
        datapoints=windspeed_mock_datapoints,
    )

    # Train the windspeed model
    windspeed_model = windspeed_provider.train_model(
        TrainingDataSet(target=windspeed_target_datapoints),
    )
    assert windspeed_model is not None
    # Save the windspeed model
    windspeed_provider.save_model(windspeed_model)
    assert windspeed_provider.load_model(prophet_basic_config.id) is not None

    # Generate the forecast
    windspeed_forecast = windspeed_provider.generate_forecast()
    assert windspeed_forecast is not None
    assert windspeed_forecast.datapoints is not None
    assert len(windspeed_forecast.datapoints) > 0

    # Create the tariff model
    tarrif_provider = ModelProviderFactory.create_provider(prophet_multi_variable_config)
    tariff_target_datapoints = AssetFeatureDatapoints(
        feature_name=prophet_multi_variable_config.target.attribute_name,
        datapoints=tariff_mock_datapoints,
    )

    # Ensure tariff model has regressors configured
    assert prophet_multi_variable_config.regressors is not None
    assert len(prophet_multi_variable_config.regressors) > 0

    # Train the tariff model
    regressor_feature_datapoints = [
        AssetFeatureDatapoints(feature_name=regressor.attribute_name, datapoints=windspeed_mock_datapoints)
        for regressor in prophet_multi_variable_config.regressors
    ]

    tariff_model = tarrif_provider.train_model(
        TrainingDataSet(target=tariff_target_datapoints, regressors=regressor_feature_datapoints),
    )
    assert tariff_model is not None

    # Save the tariff model
    tarrif_provider.save_model(tariff_model)
    assert tarrif_provider.load_model(prophet_multi_variable_config.id) is not None

    # Generate the forecast including the regressor forecast datapoints
    windspeed_regressor_datapoints = AssetFeatureDatapoints(
        feature_name=prophet_basic_config.target.attribute_name,
        datapoints=windspeed_forecast.datapoints,
    )
    forecast_dataset = ForecastDataSet(regressors=[windspeed_regressor_datapoints])
    forecast = tarrif_provider.generate_forecast(forecast_dataset)
    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) > 0
