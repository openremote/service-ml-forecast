"""Regression cases for supported tree settings and bounded training preflight."""

from http import HTTPStatus
from unittest.mock import Mock

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openremote_client import AssetDatapoint
from pydantic import ValidationError

from service_ml_forecast.ml.lightgbm_model_provider import LightGBMModelProvider
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.ml.xgboost_model_provider import XGBoostModelProvider, _convert_darts_forecast_to_datapoints
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, TrainingDataSet
from service_ml_forecast.models.model_config import LightGBMModelConfig, XGBoostModelConfig

CONFIG_CLASSES = [XGBoostModelConfig, LightGBMModelConfig]
BASE = {
    "realm": "master",
    "name": "Tree boundary regression",
    "enabled": False,
    "target": {"asset_id": "t" * 22, "attribute_name": "power"},
    "forecast_interval": "P1D",
    "forecast_periods": 24,
    "forecast_frequency": "1h",
    "lags": 24,
    "n_estimators": 5,
    "max_depth": 2,
}
INVALID = [
    {"forecast_periods": 0},
    {"forecast_periods": -1},
    {"forecast_frequency": "0h"},
    {"forecast_frequency": "-1h"},
    {"forecast_frequency": "ME"},
    {"forecast_frequency": "1us"},
    {"lags": 0},
    {"lags": -1},
    {"lags": []},
    {"lags": [0, 1]},
    {"lags": True},
    {"lags": [-1, False]},
    {"lags": None},
    {"lags_future_covariates": 2},
    {"lags_future_covariates": []},
    {"lags_past_covariates": [0]},
]


@pytest.mark.parametrize("config_class", CONFIG_CLASSES)
@pytest.mark.parametrize("changes", INVALID)
def test_invalid_tree_settings_are_rejected_when_config_is_parsed(
    config_class: type[XGBoostModelConfig] | type[LightGBMModelConfig], changes: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        config_class.model_validate(BASE | changes)


@pytest.mark.parametrize("model_type", ["xgboost", "lightgbm"])
@pytest.mark.parametrize("changes", [{"forecast_periods": 0}, {"lags": []}, {"forecast_frequency": "0h"}])
def test_api_does_not_save_invalid_tree_settings(
    mock_test_client: TestClient, model_type: str, changes: dict[str, object]
) -> None:
    response = mock_test_client.post("/api/master/configs", json=BASE | {"type": model_type} | changes)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert mock_test_client.get("/api/master/configs").json() == []


def dataset(frequency: str, periods: int) -> TrainingDataSet:
    index = pd.date_range("2026-09-01", periods=periods, freq=frequency)
    return TrainingDataSet(
        target=AssetFeatureDatapoints(
            feature_name="power",
            datapoints=[AssetDatapoint(x=t.value // 1_000_000, y=10.0 + i % 24) for i, t in enumerate(index)],
        )
    )


@pytest.mark.parametrize("config_class", CONFIG_CLASSES)
@pytest.mark.parametrize(("frequency", "periods"), [("30min", 48), ("2h", 48)])
def test_tree_training_has_no_minimum_elapsed_period(
    config_class: type[XGBoostModelConfig] | type[LightGBMModelConfig],
    frequency: str,
    periods: int,
) -> None:
    provider = ModelProviderFactory.create_provider(
        config_class.model_validate(BASE | {"forecast_frequency": frequency})
    )
    assert isinstance(provider, XGBoostModelProvider | LightGBMModelProvider)
    model = provider.train_model(dataset(frequency, periods))
    assert model is not None


@pytest.mark.parametrize("config_class", CONFIG_CLASSES)
@pytest.mark.parametrize("changes", [{"lags": 100_000_000}, {"output_chunk_length": 100_000_000}])
def test_impossible_lag_or_chunk_window_is_rejected_before_constructing_darts(
    config_class: type[XGBoostModelConfig] | type[LightGBMModelConfig], changes: dict[str, object]
) -> None:
    provider = ModelProviderFactory.create_provider(config_class.model_validate(BASE | changes))
    assert isinstance(provider, XGBoostModelProvider | LightGBMModelProvider)
    constructor = Mock(side_effect=AssertionError("Darts must not allocate an impossible window"))
    provider.model_class = constructor
    with pytest.raises(ValueError, match="training rows|aligned rows"):
        provider.train_model(dataset("1h", 100))
    constructor.assert_not_called()


def test_tree_output_preserves_whole_millisecond_timestamps() -> None:
    index = pd.date_range("2026-09-01T00:00:00.123", periods=4, freq="250ms")
    result = _convert_darts_forecast_to_datapoints(pd.DataFrame({"value": [1.0] * 4}, index=index))
    assert [point.x for point in result] == [timestamp.value // 1_000_000 for timestamp in index]
