"""Check the training gap policy and complete future-input requirement."""

from __future__ import annotations

from uuid import uuid4

import pandas as pd
import pytest
from openremote_client import AssetDatapoint

from service_ml_forecast.config import ENV
from service_ml_forecast.ml.data_processing import align_forecast_data, align_training_data
from service_ml_forecast.ml.prophet_model_provider import ProphetModelProvider
from service_ml_forecast.ml.xgboost_model_provider import XGBoostModelProvider
from service_ml_forecast.models.feature_data_wrappers import (
    AssetFeatureDatapoints,
    ForecastDataSet,
    TrainingDataSet,
)
from service_ml_forecast.models.model_config import ProphetModelConfig, XGBoostModelConfig

FULL_HOURS = 10
SUFFIX_HOURS = 4


def points(hours: list[int]) -> list[AssetDatapoint]:
    start = int(pd.Timestamp("2026-10-01 00:00:00", tz="UTC").timestamp() * 1000)
    return [AssetDatapoint(x=start + hour * 3_600_000, y=float(hour)) for hour in hours]


def training(hours: list[int]) -> TrainingDataSet:
    return TrainingDataSet(target=AssetFeatureDatapoints(feature_name="power", datapoints=points(hours)))


def test_two_hour_internal_gap_is_bounded_and_filled() -> None:
    frame = align_training_data(training([0, 1, 2, 5, 6, 7, 8, 9]), "1h")
    assert len(frame) == FULL_HOURS
    assert frame["value"].notna().all()


def test_long_gap_uses_only_clean_contiguous_suffix() -> None:
    frame = align_training_data(training([0, 1, 2, 6, 7, 8, 9]), "1h")
    assert len(frame) == SUFFIX_HOURS
    assert frame["timestamp"].iloc[0] == pd.Timestamp("2026-10-01 06:00:00")


def test_missing_future_hour_is_rejected() -> None:
    start = pd.Timestamp("2026-10-01 00:00:00")
    future = pd.DataFrame({"timestamp": pd.date_range(start, periods=4, freq="1h")})
    dataset = ForecastDataSet(
        covariates=[AssetFeatureDatapoints(feature_name="temperature", datapoints=points([0, 1, 3]))]
    )
    with pytest.raises(ValueError, match="full forecast window"):
        align_forecast_data(future, dataset, "1h", uuid4())


def test_default_minimum_history_rejects_short_training(
    xgboost_basic_config: XGBoostModelConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ENV, "ML_MIN_TRAINING_DAYS", 28)
    provider = XGBoostModelProvider(xgboost_basic_config)
    assert provider.train_model(training(list(range(30)))) is None


@pytest.mark.parametrize(("frequency", "rows", "accepted"), [("30min", 24, False), ("2h", 12, True)])
def test_prophet_minimum_history_respects_sampling_frequency(
    prophet_basic_config: ProphetModelConfig,
    monkeypatch: pytest.MonkeyPatch,
    frequency: str,
    rows: int,
    accepted: bool,
) -> None:
    monkeypatch.setattr(ENV, "ML_MIN_TRAINING_DAYS", 1)
    prophet_basic_config.forecast_frequency = frequency
    times = pd.date_range("2026-10-01", periods=rows, freq=frequency)
    dataset = TrainingDataSet(
        target=AssetFeatureDatapoints(
            feature_name="power",
            datapoints=[AssetDatapoint(x=int(stamp.value // 1_000_000), y=float(i)) for i, stamp in enumerate(times)],
        )
    )
    model = ProphetModelProvider(prophet_basic_config).train_model(dataset)
    assert (model is not None) == accepted


@pytest.mark.parametrize("invalid_value", [float("inf"), float("-inf")])
@pytest.mark.parametrize("feature", ["target", "regressor"])
def test_infinite_training_inputs_are_rejected_before_gap_filling(invalid_value: float, feature: str) -> None:
    dataset = training(list(range(FULL_HOURS)))
    dataset.covariates = [
        AssetFeatureDatapoints(feature_name="temperature", datapoints=points(list(range(FULL_HOURS))))
    ]
    series = dataset.target if feature == "target" else dataset.covariates[0]
    series.datapoints[4].y = invalid_value
    with pytest.raises(ValueError, match="infinite"):
        align_training_data(dataset, "1h")


@pytest.mark.parametrize("invalid_value", [float("inf"), float("-inf")])
def test_infinite_future_input_is_rejected_even_with_duplicate_timestamp(invalid_value: float) -> None:
    future = pd.DataFrame({"timestamp": pd.date_range("2026-10-01", periods=4, freq="1h")})
    weather = points([0, 1, 2, 3])
    weather.append(AssetDatapoint(x=weather[1].x, y=invalid_value))
    dataset = ForecastDataSet(covariates=[AssetFeatureDatapoints(feature_name="temperature", datapoints=weather)])
    with pytest.raises(ValueError, match="infinite"):
        align_forecast_data(future, dataset, "1h", uuid4())
