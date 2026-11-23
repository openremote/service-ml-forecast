import pandas as pd
from darts.models import LightGBMModel
from openremote_client import AssetDatapoint

from service_ml_forecast.ml.lightgbm_model_provider import LightGBMModelProvider
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, ForecastDataSet, TrainingDataSet
from service_ml_forecast.models.model_config import LightGBMModelConfig, XGBoostModelConfig

FORECAST_PERIODS = 96
OUTPUT_CHUNK_LENGTH = 24
TRAINING_PERIODS = 72
MILLISECONDS_PER_HOUR = 3_600_000


def test_factory_creates_lightgbm_provider(lightgbm_basic_config: LightGBMModelConfig) -> None:
    provider = ModelProviderFactory.create_provider(lightgbm_basic_config)

    assert isinstance(provider, LightGBMModelProvider)


def test_train_persist_and_forecast(
    lightgbm_basic_config: LightGBMModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
) -> None:
    provider = ModelProviderFactory.create_provider(lightgbm_basic_config)
    training_data = TrainingDataSet(
        target=AssetFeatureDatapoints(
            feature_name=lightgbm_basic_config.target.attribute_name,
            datapoints=windspeed_mock_datapoints,
        )
    )

    model = provider.train_model(training_data)

    assert isinstance(model, LightGBMModel)
    provider.save_model(model)
    assert isinstance(provider.load_model(lightgbm_basic_config.id), LightGBMModel)

    forecast = provider.generate_forecast()
    assert len(forecast.datapoints) == lightgbm_basic_config.forecast_periods


def test_train_and_forecast_with_regressor(
    lightgbm_basic_config: LightGBMModelConfig,
    xgboost_multi_variable_config: XGBoostModelConfig,
    windspeed_mock_datapoints: list[AssetDatapoint],
    tariff_mock_datapoints: list[AssetDatapoint],
) -> None:
    config = lightgbm_basic_config.model_copy(
        update={
            "target": xgboost_multi_variable_config.target,
            "past_covariates": xgboost_multi_variable_config.past_covariates,
            "lags_past_covariates": xgboost_multi_variable_config.lags_past_covariates,
        }
    )
    provider = ModelProviderFactory.create_provider(config)
    model = provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=config.target.attribute_name,
                datapoints=tariff_mock_datapoints,
            ),
            covariates=[
                AssetFeatureDatapoints(
                    feature_name="windSpeed",
                    datapoints=windspeed_mock_datapoints,
                )
            ],
        )
    )

    assert isinstance(model, LightGBMModel)
    provider.save_model(model)

    assert model.training_series is not None
    first_hour = model.training_series.end_time() - pd.Timedelta(hours=2)
    complete_windspeed_forecast = [
        AssetDatapoint(x=int(timestamp.timestamp() * 1000), y=2.0)
        for timestamp in pd.date_range(
            start=first_hour,
            periods=config.forecast_periods + 3,
            freq=config.forecast_frequency,
            tz="UTC",
        )
    ]

    forecast = provider.generate_forecast(
        ForecastDataSet(
            covariates=[
                AssetFeatureDatapoints(
                    feature_name="windSpeed",
                    datapoints=complete_windspeed_forecast,
                )
            ]
        )
    )
    assert len(forecast.datapoints) == config.forecast_periods


def test_chunk_24_configuration_is_supported(
    lightgbm_basic_config: LightGBMModelConfig,
) -> None:
    config = lightgbm_basic_config.model_copy(
        update={
            "forecast_periods": FORECAST_PERIODS,
            "output_chunk_length": OUTPUT_CHUNK_LENGTH,
        }
    )
    provider = ModelProviderFactory.create_provider(config)
    hourly_datapoints = [
        AssetDatapoint(
            x=1_741_190_400_000 + period * MILLISECONDS_PER_HOUR,
            y=2.0 + (period % OUTPUT_CHUNK_LENGTH) / 10,
        )
        for period in range(TRAINING_PERIODS)
    ]
    model = provider.train_model(
        TrainingDataSet(
            target=AssetFeatureDatapoints(
                feature_name=config.target.attribute_name,
                datapoints=hourly_datapoints,
            )
        )
    )

    assert model is not None
    provider.save_model(model)
    assert len(provider.generate_forecast().datapoints) == FORECAST_PERIODS
