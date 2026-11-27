"""Real-provider checks for input roles, lag coverage, ordering and DST."""

import math

import pandas as pd
import pytest
from openremote_client import AssetDatapoint

from service_ml_forecast.ml.calendar_regressors import CALENDAR_COLUMNS
from service_ml_forecast.ml.lightgbm_model_provider import LightGBMModelProvider
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.ml.xgboost_model_provider import XGBoostModelProvider
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, ForecastDataSet, TrainingDataSet
from service_ml_forecast.models.model_config import LightGBMModelConfig, XGBoostModelConfig

PERIODS = 6
HOURS = 240


def setup_case(
    model_type: str, *, past: bool = True, future: bool = True
) -> tuple[XGBoostModelConfig | LightGBMModelConfig, TrainingDataSet, ForecastDataSet]:
    fields = {
        "type": model_type,
        "name": "Covariate robustness",
        "realm": "gems",
        "target": {"asset_id": "t" * 22, "attribute_name": "power"},
        "forecast_interval": "P1D",
        "forecast_frequency": "1h",
        "forecast_periods": PERIODS,
        "calendar_timezone": "Europe/Amsterdam",
        "lags": 24,
        "n_estimators": 10,
    }
    if past:
        fields.update(
            past_covariates=[{"asset_id": "p" * 22, "attribute_name": "power"}], lags_past_covariates=[-PERIODS]
        )
    if future:
        fields.update(
            future_covariates=[{"asset_id": "f" * 22, "attribute_name": "temperature"}], lags_future_covariates=[0]
        )
    config_types: dict[str, type[XGBoostModelConfig] | type[LightGBMModelConfig]] = {
        "xgboost": XGBoostModelConfig,
        "lightgbm": LightGBMModelConfig,
    }
    config = config_types[model_type].model_validate(fields)
    cutoff = pd.Timestamp("2026-10-24T22:00:00Z")
    start = cutoff - pd.Timedelta(hours=HOURS - 1)

    def points(first: pd.Timestamp, count: int, offset: float) -> list[AssetDatapoint]:
        return [
            AssetDatapoint(x=int((first + pd.Timedelta(hours=i)).timestamp() * 1000), y=offset + math.sin(i / 6))
            for i in range(count)
        ]

    history, inputs = [], []
    if past:
        assert config.past_covariates is not None
        name = config.past_covariates[0].get_feature_name()
        history.append(AssetFeatureDatapoints(feature_name=name, datapoints=points(start, HOURS, 20)))
        inputs.append(AssetFeatureDatapoints(feature_name=name, datapoints=history[-1].datapoints[-PERIODS:]))
    if future:
        assert config.future_covariates is not None
        name = config.future_covariates[0].get_feature_name()
        history.append(AssetFeatureDatapoints(feature_name=name, datapoints=points(start, HOURS, 10)))
        inputs.append(
            AssetFeatureDatapoints(feature_name=name, datapoints=points(cutoff + pd.Timedelta(hours=1), PERIODS, 10))
        )
    training = TrainingDataSet(
        target=AssetFeatureDatapoints(feature_name="power", datapoints=points(start, HOURS, 50)), covariates=history
    )
    return config, training, ForecastDataSet(covariates=inputs)


@pytest.mark.parametrize("model_type", ["xgboost", "lightgbm"])
def test_mixed_inputs_keep_past_future_and_calendar_roles_separate(model_type: str) -> None:
    config, training, future = setup_case(model_type)
    provider = ModelProviderFactory.create_provider(config)
    assert isinstance(provider, XGBoostModelProvider | LightGBMModelProvider)
    model = provider.train_model(training)
    assert model is not None
    assert config.past_covariates is not None
    assert config.future_covariates is not None
    assert list(model.past_covariate_series.components) == [config.past_covariates[0].get_feature_name()]
    assert list(model.future_covariate_series.components) == [
        config.future_covariates[0].get_feature_name(),
        *CALENDAR_COLUMNS,
    ]
    provider.save_model(model)
    # The historical input ends at training cutoff. It needs no invented future observations.
    result = provider.generate_forecast(future)
    assert len(result.datapoints) == PERIODS
    assert all(math.isfinite(p.y) for p in result.datapoints)
    timestamps = pd.to_datetime([p.x for p in result.datapoints], unit="ms", utc=True)
    assert timestamps.is_unique
    assert list(timestamps.tz_convert("Europe/Amsterdam").hour) == [1, 2, 2, 3, 4, 5]


@pytest.mark.parametrize("model_type", ["xgboost", "lightgbm"])
def test_historical_input_is_not_accidentally_used_as_future_calendar_input(model_type: str) -> None:
    config, training, future = setup_case(model_type, future=False)
    provider = ModelProviderFactory.create_provider(config)
    assert isinstance(provider, XGBoostModelProvider | LightGBMModelProvider)
    model = provider.train_model(training)
    assert model is not None
    assert list(model.future_covariate_series.components) == CALENDAR_COLUMNS
    provider.save_model(model)
    assert len(provider.generate_forecast(future).datapoints) == PERIODS


@pytest.mark.parametrize("model_type", ["xgboost", "lightgbm"])
def test_input_order_does_not_change_forecast(model_type: str) -> None:
    config, training, future = setup_case(model_type)
    provider = ModelProviderFactory.create_provider(config)
    assert isinstance(provider, XGBoostModelProvider | LightGBMModelProvider)
    model = provider.train_model(training)
    assert model is not None
    provider.save_model(model)
    first = provider.generate_forecast(future)
    reversed_inputs = future.model_copy(deep=True)
    reversed_inputs.covariates.reverse()
    second = provider.generate_forecast(reversed_inputs)
    assert [p.y for p in first.datapoints] == [p.y for p in second.datapoints]


@pytest.mark.parametrize("model_type", ["xgboost", "lightgbm"])
def test_missing_required_historical_input_is_rejected(model_type: str) -> None:
    config, training, future = setup_case(model_type)
    provider = ModelProviderFactory.create_provider(config)
    assert isinstance(provider, XGBoostModelProvider | LightGBMModelProvider)
    model = provider.train_model(training)
    assert model is not None
    provider.save_model(model)
    future.covariates = future.covariates[1:]
    with pytest.raises(ValueError, match="[Mm]issing.*input|[Mm]issing.*covariate"):
        provider.generate_forecast(future)


@pytest.mark.parametrize("model_type", ["xgboost", "lightgbm"])
def test_positive_future_lag_requires_extra_forecast_coverage(model_type: str) -> None:
    config, training, future = setup_case(model_type, past=False)
    config.lags_future_covariates = [0, 2]
    provider = ModelProviderFactory.create_provider(config)
    assert isinstance(provider, XGBoostModelProvider | LightGBMModelProvider)
    model = provider.train_model(training)
    assert model is not None
    provider.save_model(model)
    with pytest.raises(ValueError, match="full forecast window"):
        provider.generate_forecast(future)
    last = future.covariates[0].datapoints[-1]
    future.covariates[0].datapoints.extend([AssetDatapoint(x=last.x + i * 3_600_000, y=last.y) for i in [1, 2]])
    assert len(provider.generate_forecast(future).datapoints) == PERIODS
