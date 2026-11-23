"""All supported models consume the same calendar and weather forecast inputs."""

import math

import pandas as pd
import pytest
from openremote_client import AssetDatapoint

from service_ml_forecast.ml.calendar_regressors import CALENDAR_COLUMNS, add_calendar_regressors
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, ForecastDataSet, TrainingDataSet
from service_ml_forecast.models.model_config import LightGBMModelConfig, ProphetModelConfig, XGBoostModelConfig

FORECAST_PERIODS = 4


def _points(start: pd.Timestamp, values: list[float]) -> list[AssetDatapoint]:
    return [
        AssetDatapoint(x=int((start + pd.Timedelta(hours=i)).timestamp() * 1000), y=value)
        for i, value in enumerate(values)
    ]


def test_calendar_uses_local_hour_across_dst() -> None:
    frame = pd.DataFrame(
        {"timestamp": pd.to_datetime(["2026-03-29T00:00:00Z", "2026-03-29T01:00:00Z"]).tz_localize(None)}
    )
    result = add_calendar_regressors(frame, "timestamp", "Europe/Amsterdam")
    assert list(result.columns[1:]) == CALENDAR_COLUMNS
    assert result["calendar_hour_sin"].iloc[0] == pytest.approx(math.sin(2 * math.pi / 24))
    assert result["calendar_hour_sin"].iloc[1] == pytest.approx(math.sin(2 * math.pi * 3 / 24))


def test_invalid_calendar_timezone_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown calendar timezone"):
        XGBoostModelConfig.model_validate(
            {
                "type": "xgboost",
                "realm": "gems",
                "name": "invalid timezone",
                "target": {"asset_id": "44ORIhkDVAlT97dYGUD9n5", "attribute_name": "power"},
                "forecast_interval": "PT1H",
                "forecast_periods": FORECAST_PERIODS,
                "forecast_frequency": "1h",
                "calendar_timezone": "not/a-real-timezone",
            }
        )


@pytest.mark.parametrize("model_type", ["xgboost", "lightgbm", "prophet"])
def test_model_trains_and_forecasts_with_calendar_temperature_and_wind(model_type: str) -> None:
    config_types: dict[str, type[XGBoostModelConfig] | type[LightGBMModelConfig] | type[ProphetModelConfig]] = {
        "xgboost": XGBoostModelConfig,
        "lightgbm": LightGBMModelConfig,
        "prophet": ProphetModelConfig,
    }
    config_data = {
        "type": model_type,
        "realm": "gems",
        "name": f"{model_type} covariates",
        "target": {"asset_id": "44ORIhkDVAlT97dYGUD9n5", "attribute_name": "power", "training_data_period": "P30D"},
        "forecast_interval": "PT1H",
        "forecast_periods": FORECAST_PERIODS,
        "forecast_frequency": "1h",
        "calendar_timezone": "Europe/Amsterdam",
    }
    if model_type == "prophet":
        config_data.update(yearly_seasonality=False)
    else:
        config_data.update(lags=24, lags_future_covariates=[0], n_estimators=10)
    config = config_types[model_type].model_validate(config_data)
    provider = ModelProviderFactory.create_provider(config)
    start = pd.Timestamp("2026-10-01T00:00:00Z")
    hours = list(range(240))
    dataset = TrainingDataSet(
        target=AssetFeatureDatapoints(
            feature_name="power", datapoints=_points(start, [100 + 10 * math.sin(i / 24) for i in hours])
        ),
        covariates=[
            AssetFeatureDatapoints(
                feature_name="temperature", datapoints=_points(start, [15 + math.sin(i / 12) for i in hours])
            ),
            AssetFeatureDatapoints(
                feature_name="windSpeed", datapoints=_points(start, [5 + math.cos(i / 8) for i in hours])
            ),
        ],
    )
    model = provider.train_model(dataset)
    assert model is not None
    provider.save_model(model)
    future_start = start + pd.Timedelta(hours=len(hours))
    future = ForecastDataSet(
        covariates=[
            AssetFeatureDatapoints(
                feature_name="temperature", datapoints=_points(future_start, [16.0] * FORECAST_PERIODS)
            ),
            AssetFeatureDatapoints(
                feature_name="windSpeed", datapoints=_points(future_start, [4.0] * FORECAST_PERIODS)
            ),
        ]
    )
    result = provider.generate_forecast(future)
    assert len(result.datapoints) == FORECAST_PERIODS
    assert all(math.isfinite(float(point.y)) for point in result.datapoints)
