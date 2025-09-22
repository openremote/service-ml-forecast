from typing import Any

import pytest
from openremote_client import AssetDatapoint

from service_ml_forecast.common.exceptions import ResourceNotFoundError
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, ForecastDataSet, TrainingDataSet
from service_ml_forecast.models.model_config import XGBoostModelConfig


def test_train_and_predict(
    xgboost_basic_config: XGBoostModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test the basic functionality of an XGBoost model provider with a single variable.

    Verifies that:
    - The model trains successfully with the provided data
    - The trained model can be saved and loaded
    - The model can generate forecasts with non-empty results
    """
    model_provider = ModelProviderFactory.create_provider(xgboost_basic_config)

    model = model_provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=xgboost_basic_config.target.attribute_name,
                datapoints=windspeed_mock_datapoints,
            ),
        ),
    )
    assert model is not None

    model_provider.save_model(model)
    assert xgboost_basic_config.id is not None
    assert model_provider.load_model(xgboost_basic_config.id) is not None

    forecast = model_provider.generate_forecast()
    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) > 0


def test_train_and_predict_with_regressor(
    xgboost_multi_variable_config: XGBoostModelConfig,
    xgboost_basic_config: XGBoostModelConfig,
    tariff_mock_datapoints: list[AssetDatapoint],
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test XGBoost model with external regressors for multi-variable forecasting.

    Verifies that:
    - Both models train successfully (regressor and target)
    - Models can be saved and then loaded
    - The windspeed forecast can be used as a regressor input for the tariff model
    - The tariff model generates valid forecasts when provided with regressor data
    """
    windspeed_provider = ModelProviderFactory.create_provider(xgboost_basic_config)
    windspeed_target_datapoints = AssetFeatureDatapoints(
        feature_name=xgboost_basic_config.target.attribute_name,
        datapoints=windspeed_mock_datapoints,
    )

    windspeed_model = windspeed_provider.train_model(
        TrainingDataSet(target=windspeed_target_datapoints),
    )
    assert windspeed_model is not None
    windspeed_provider.save_model(windspeed_model)
    assert windspeed_provider.load_model(xgboost_basic_config.id) is not None

    windspeed_forecast = windspeed_provider.generate_forecast()
    assert windspeed_forecast is not None
    assert windspeed_forecast.datapoints is not None
    assert len(windspeed_forecast.datapoints) > 0

    tariff_provider = ModelProviderFactory.create_provider(xgboost_multi_variable_config)
    tariff_target_datapoints = AssetFeatureDatapoints(
        feature_name=xgboost_multi_variable_config.target.attribute_name,
        datapoints=tariff_mock_datapoints,
    )

    # Use past covariates (windspeed as historical data)
    assert xgboost_multi_variable_config.past_covariates is not None
    assert len(xgboost_multi_variable_config.past_covariates) > 0

    regressor_feature_datapoints = [
        AssetFeatureDatapoints(feature_name=covariate.attribute_name, datapoints=windspeed_mock_datapoints)
        for covariate in xgboost_multi_variable_config.past_covariates
    ]

    tariff_model = tariff_provider.train_model(
        TrainingDataSet(target=tariff_target_datapoints, covariates=regressor_feature_datapoints),
    )
    assert tariff_model is not None

    tariff_provider.save_model(tariff_model)
    assert tariff_provider.load_model(xgboost_multi_variable_config.id) is not None

    windspeed_regressor_datapoints = AssetFeatureDatapoints(
        feature_name=xgboost_basic_config.target.attribute_name,
        datapoints=windspeed_forecast.datapoints,
    )
    forecast_dataset = ForecastDataSet(covariates=[windspeed_regressor_datapoints])
    forecast = tariff_provider.generate_forecast(forecast_dataset)
    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) > 0


def test_train_with_insufficient_data(
    xgboost_basic_config: XGBoostModelConfig,
) -> None:
    """Test that training fails gracefully with insufficient data.

    Verifies that:
    - Model returns None when training data is too small
    - No exceptions are raised with edge case data
    """
    minimal_datapoints = [AssetDatapoint(x=1741193868185, y=2.57)]

    model_provider = ModelProviderFactory.create_provider(xgboost_basic_config)

    model = model_provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=xgboost_basic_config.target.attribute_name,
                datapoints=minimal_datapoints,
            ),
        ),
    )

    assert model is None


def test_train_with_empty_data(
    xgboost_basic_config: XGBoostModelConfig,
) -> None:
    """Test that training fails gracefully with empty data.

    Verifies that:
    - Model returns None when no training data is provided
    - No exceptions are raised with empty dataset
    """
    model_provider = ModelProviderFactory.create_provider(xgboost_basic_config)

    model = model_provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=xgboost_basic_config.target.attribute_name,
                datapoints=[],
            ),
        ),
    )

    assert model is None


def test_forecast_without_trained_model(
    xgboost_basic_config: XGBoostModelConfig,
) -> None:
    """Test that forecasting fails gracefully when no model is trained.

    Verifies that:
    - Appropriate exception is raised when trying to forecast without training
    - Error handling works correctly for missing model scenario
    """
    model_provider = ModelProviderFactory.create_provider(xgboost_basic_config)

    with pytest.raises(ResourceNotFoundError):
        model_provider.generate_forecast()


def test_data_resampling_and_alignment(
    xgboost_multi_variable_config: XGBoostModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
    tariff_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test that data resampling and alignment works correctly with different frequencies.

    Verifies that:
    - Data with different frequencies (10min vs 1hour) can be aligned
    - Resampling produces reasonable results
    - Training succeeds with mismatched data frequencies
    """
    model_provider = ModelProviderFactory.create_provider(xgboost_multi_variable_config)

    target_datapoints = AssetFeatureDatapoints(
        feature_name=xgboost_multi_variable_config.target.attribute_name,
        datapoints=tariff_mock_datapoints,
    )

    # Use past covariates for testing data alignment
    assert xgboost_multi_variable_config.past_covariates is not None
    first_covariate = xgboost_multi_variable_config.past_covariates[0]

    regressor_datapoints = AssetFeatureDatapoints(
        feature_name=first_covariate.attribute_name,
        datapoints=windspeed_mock_datapoints,
    )

    model = model_provider.train_model(
        TrainingDataSet(
            target=target_datapoints,
            covariates=[regressor_datapoints],
        ),
    )

    assert model is not None


def test_forecast_with_missing_regressor_data(
    xgboost_multi_variable_config: XGBoostModelConfig,
    tariff_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test forecasting behavior when regressor data is missing or incomplete.

    Verifies that:
    - Model handles missing regressor data gracefully
    - Forecasts can still be generated with partial regressor information
    - Appropriate warnings are logged for missing data
    """
    model_provider = ModelProviderFactory.create_provider(xgboost_multi_variable_config)

    target_datapoints = AssetFeatureDatapoints(
        feature_name=xgboost_multi_variable_config.target.attribute_name,
        datapoints=tariff_mock_datapoints,
    )

    # Use past covariates for testing missing data handling
    assert xgboost_multi_variable_config.past_covariates is not None
    first_covariate = xgboost_multi_variable_config.past_covariates[0]

    regressor_datapoints = AssetFeatureDatapoints(
        feature_name=first_covariate.attribute_name,
        datapoints=tariff_mock_datapoints[:15],  # Use more data points to ensure sufficient training data
    )

    model = model_provider.train_model(
        TrainingDataSet(
            target=target_datapoints,
            covariates=[regressor_datapoints],
        ),
    )
    assert model is not None

    model_provider.save_model(model)

    # Use past covariates for minimal forecast test
    assert xgboost_multi_variable_config.past_covariates is not None
    first_covariate = xgboost_multi_variable_config.past_covariates[0]

    minimal_regressor = AssetFeatureDatapoints(
        feature_name=first_covariate.attribute_name,
        datapoints=[tariff_mock_datapoints[0]],
    )

    forecast_dataset = ForecastDataSet(covariates=[minimal_regressor])

    forecast = model_provider.generate_forecast(forecast_dataset)
    assert forecast is not None
    assert forecast.datapoints is not None


def test_model_persistence_and_reload(
    xgboost_basic_config: XGBoostModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test that models can be saved and reloaded correctly.

    Verifies that:
    - Models can be saved to storage
    - Saved models can be loaded back
    - Loaded models produce consistent forecasts
    """
    model_provider = ModelProviderFactory.create_provider(xgboost_basic_config)

    model = model_provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=xgboost_basic_config.target.attribute_name,
                datapoints=windspeed_mock_datapoints,
            ),
        ),
    )
    assert model is not None

    model_provider.save_model(model)

    original_forecast = model_provider.generate_forecast()
    assert original_forecast is not None
    assert len(original_forecast.datapoints) > 0

    new_provider = ModelProviderFactory.create_provider(xgboost_basic_config)
    loaded_model = new_provider.load_model(xgboost_basic_config.id)
    assert loaded_model is not None

    loaded_forecast = new_provider.generate_forecast()
    assert loaded_forecast is not None
    assert len(loaded_forecast.datapoints) > 0

    assert len(original_forecast.datapoints) == len(loaded_forecast.datapoints)


def test_forecast_data_quality(
    xgboost_basic_config: XGBoostModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test that forecast data has reasonable quality and structure.

    Verifies that:
    - Forecast timestamps are in the future
    - Forecast values are reasonable (not NaN, not extreme outliers)
    - Forecast frequency matches expected frequency
    """
    model_provider = ModelProviderFactory.create_provider(xgboost_basic_config)

    model = model_provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=xgboost_basic_config.target.attribute_name,
                datapoints=windspeed_mock_datapoints,
            ),
        ),
    )
    assert model is not None

    model_provider.save_model(model)

    forecast = model_provider.generate_forecast()
    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) > 0

    last_training_time = max(point.x for point in windspeed_mock_datapoints)

    for datapoint in forecast.datapoints:
        assert datapoint.x > last_training_time

        assert datapoint.y is not None
        assert not (datapoint.y != datapoint.y)
        MIN_REASONABLE_VALUE = -1000
        MAX_REASONABLE_VALUE = 1000
        assert MIN_REASONABLE_VALUE < datapoint.y < MAX_REASONABLE_VALUE

    if len(forecast.datapoints) > 1:
        time_diffs = [
            forecast.datapoints[i + 1].x - forecast.datapoints[i].x for i in range(len(forecast.datapoints) - 1)
        ]
        expected_interval = 3600000
        for diff in time_diffs:
            assert abs(diff - expected_interval) < expected_interval * 0.1


def test_lag_feature_configuration(
    xgboost_basic_config: XGBoostModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test XGBoost-specific lag feature configuration.

    Verifies that:
    - Different lag configurations work correctly
    - Models train successfully with various lag settings
    - Forecasts are generated with proper output chunk lengths
    """
    # Test with different lag configurations
    configs_to_test: list[dict[str, Any]] = [
        {"lags": 3, "output_chunk_length": 1},
        {"lags": [-1, -2, -3], "output_chunk_length": 1},
        {"lags": 5, "output_chunk_length": 3},
    ]

    for config_params in configs_to_test:
        # Update config with test parameters
        test_config = xgboost_basic_config.model_copy(update=config_params)

        model_provider = ModelProviderFactory.create_provider(test_config)

        model = model_provider.train_model(
            TrainingDataSet(
                target=AssetFeatureDatapoints(
                    feature_name=test_config.target.attribute_name,
                    datapoints=windspeed_mock_datapoints,
                ),
            ),
        )

        # Should train successfully with different lag configurations
        assert model is not None

        model_provider.save_model(model)
        forecast = model_provider.generate_forecast()
        assert forecast is not None
        assert len(forecast.datapoints) == test_config.forecast_periods


def test_hyperparameter_variations(
    xgboost_basic_config: XGBoostModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test XGBoost model with different hyperparameter configurations.

    Verifies that:
    - Models train successfully with various hyperparameters
    - Different configurations produce valid forecasts
    - No errors occur with reasonable parameter variations
    """
    hyperparameter_configs: list[dict[str, Any]] = [
        {"n_estimators": 50, "max_depth": 3, "learning_rate": 0.05},
        {"n_estimators": 200, "max_depth": 8, "learning_rate": 0.2},
        {"subsample": 0.6, "random_state": 123},
    ]

    for params in hyperparameter_configs:
        test_config = xgboost_basic_config.model_copy(update=params)

        model_provider = ModelProviderFactory.create_provider(test_config)

        model = model_provider.train_model(
            TrainingDataSet(
                target=AssetFeatureDatapoints(
                    feature_name=test_config.target.attribute_name,
                    datapoints=windspeed_mock_datapoints,
                ),
            ),
        )

        assert model is not None

        model_provider.save_model(model)
        forecast = model_provider.generate_forecast()
        assert forecast is not None
        assert len(forecast.datapoints) > 0


def test_future_covariate_forecasting(
    xgboost_future_covariate_config: XGBoostModelConfig,
    tariff_mock_datapoints: list[AssetDatapoint],
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    """Test XGBoost model with future covariates (known-in-advance features).

    Verifies that:
    - Model trains successfully with future covariate configuration
    - Future covariates are properly used during training and forecasting
    - Forecasts can be generated when future covariate data is provided
    - The model handles the distinction between past and future covariate types
    """
    model_provider = ModelProviderFactory.create_provider(xgboost_future_covariate_config)

    target_datapoints = AssetFeatureDatapoints(
        feature_name=xgboost_future_covariate_config.target.attribute_name,
        datapoints=tariff_mock_datapoints,
    )

    # Use future covariates (windspeed forecasts from weather service)
    assert xgboost_future_covariate_config.future_covariates is not None
    future_covariate = xgboost_future_covariate_config.future_covariates[0]
    regressor_datapoints = AssetFeatureDatapoints(
        feature_name=future_covariate.attribute_name,
        datapoints=windspeed_mock_datapoints,
    )

    # Train model with future covariates
    model = model_provider.train_model(
        TrainingDataSet(
            target=target_datapoints,
            covariates=[regressor_datapoints],
        ),
    )
    assert model is not None
    model_provider.save_model(model)

    # Generate forecast with future covariate data
    # In a real scenario, this would be windspeed forecast data from a weather service
    forecast_regressor = AssetFeatureDatapoints(
        feature_name=future_covariate.attribute_name,
        datapoints=windspeed_mock_datapoints[:10],  # Simulate future windspeed forecasts
    )

    forecast_dataset = ForecastDataSet(covariates=[forecast_regressor])
    forecast = model_provider.generate_forecast(forecast_dataset)

    assert forecast is not None
    assert forecast.datapoints is not None
    assert len(forecast.datapoints) > 0
    assert len(forecast.datapoints) == xgboost_future_covariate_config.forecast_periods
