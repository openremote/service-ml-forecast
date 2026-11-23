from uuid import uuid4

import numpy as np
import pandas as pd
import pytest
from openremote_client import AssetDatapoint
from pydantic import TypeAdapter, ValidationError

from service_ml_forecast.common.exceptions import ResourceValidationError
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.ml.wea_model_provider import WEAModelProvider
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, ForecastDataSet, TrainingDataSet
from service_ml_forecast.models.model_config import ModelConfig, WEAModelConfig

HOUR = 3_600_000
ISSUE = int(pd.Timestamp("2026-09-01T08:00:00Z").timestamp() * 1000)


def config(**changes: object) -> WEAModelConfig:
    return WEAModelConfig.model_validate(
        {
            "id": uuid4(),
            "realm": "gems",
            "name": "WEA test",
            "enabled": False,
            "type": "wea",
            "target": {"asset_id": "Bed20Oct2026WEATestAAA", "attribute_name": "power"},
            "forecast_interval": "P1D",
            "forecast_periods": 24,
            "forecast_frequency": "1h",
            **changes,
        }
    )


def history(issue: int = ISSUE, missing: int | None = None) -> TrainingDataSet:
    points = []
    for index in range(4, 0, -1):
        if index == missing:
            continue
        for lead in range(25):
            points.append(AssetDatapoint(x=issue - index * 168 * HOUR + lead * HOUR, y=(5 - index) * 10 + lead))
    points.append(AssetDatapoint(x=issue + 10_000, y=999))
    return TrainingDataSet(target=AssetFeatureDatapoints(feature_name="power", datapoints=points))


def test_wea_factory_config_roundtrip_and_persisted_forecast() -> None:
    cfg = config()
    restored: ModelConfig = TypeAdapter(ModelConfig).validate_json(cfg.model_dump_json())
    provider = ModelProviderFactory.create_provider(restored)
    assert isinstance(provider, WEAModelProvider)
    model = provider.train_model(history())
    provider.save_model(model)
    forecast = provider.generate_forecast()
    # Independent hand calculation: (((10*.6+20*.4)*.6+30*.4)*.6+40*.4) = 28.24.
    assert [point.y for point in forecast.datapoints] == pytest.approx([28.24 + n for n in range(1, 25)])
    assert [point.x for point in forecast.datapoints] == [ISSUE + n * HOUR for n in range(1, 25)]
    assert provider.load_model(cfg.id).training_cutoff == pd.Timestamp(ISSUE + 10_000, unit="ms").isoformat()
    assert provider.model_storage_service.get_ready_manifest(cfg)["training_cutoff"] is not None


def test_wea_preserves_raw_floor_sampling_and_does_not_average() -> None:
    provider = WEAModelProvider(config())
    data = history()
    for point in data.target.datapoints:
        if point.x < ISSUE:
            point.x -= 1000
    model = provider.train_model(data)
    # Every requested timestamp uses the latest raw sample, without interpolation.
    assert model.predict()[0].y == pytest.approx(29.24)


@pytest.mark.parametrize("duration", ["P1W", "PT168H", "PT10080M"])
def test_wea_equivalent_iso_periods_produce_identical_forecasts(duration: str) -> None:
    reference = WEAModelProvider(config()).train_model(history()).predict()
    actual = WEAModelProvider(config(past_period=duration)).train_model(history()).predict()
    assert actual == reference


def test_wea_missing_period_rejected_before_artifact_publication() -> None:
    provider = WEAModelProvider(config())
    with pytest.raises(ValueError, match="missing historical sample"):
        provider.train_model(history(missing=3))


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, None])
def test_wea_rejects_non_finite_raw_values(value: float | None) -> None:
    data = history()
    data.target.datapoints[0].y = value
    with pytest.raises(ValueError, match="non-finite"):
        WEAModelProvider(config()).train_model(data)


def test_wea_rejects_conflicting_duplicates_but_accepts_identical_duplicates() -> None:
    data = history()
    data.target.datapoints.append(data.target.datapoints[0].model_copy())
    WEAModelProvider(config()).train_model(data)
    data.target.datapoints.append(data.target.datapoints[0].model_copy(update={"y": -1}))
    with pytest.raises(ValueError, match="conflicting duplicate"):
        WEAModelProvider(config()).train_model(data)


def test_wea_rejects_future_observations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("service_ml_forecast.ml.wea_model_provider.TimeUtil.get_timestamp_ms", lambda: ISSUE)
    with pytest.raises(ValueError, match="future observations"):
        WEAModelProvider(config()).train_model(history())


@pytest.mark.parametrize(
    "changes",
    [
        {"past_period": "P1M"},
        {"past_period": "P0D"},
        {"past_count": 0},
        {"past_count": 101},
        {"forecast_periods": 169},
        {"forecast_periods": 0},
        {"forecast_frequency": "1ME"},
        {"calendar_timezone": "Europe/Amsterdam"},
    ],
)
def test_wea_rejects_unsupported_configuration(changes: dict[str, object]) -> None:
    with pytest.raises((ValidationError, ValueError)):
        config(**changes)


def test_wea_rejects_changed_configuration_on_load() -> None:
    cfg = config()
    provider = WEAModelProvider(cfg)
    provider.save_model(provider.train_model(history()))
    changed = WEAModelProvider(cfg.model_copy(update={"past_count": 3}))
    with pytest.raises(ResourceValidationError, match="does not match"):
        changed.generate_forecast()


def test_wea_rejects_covariates() -> None:
    provider = WEAModelProvider(config())
    provider.save_model(provider.train_model(history()))
    covariate = AssetFeatureDatapoints(feature_name="temperature", datapoints=[])
    with pytest.raises(ValueError, match="target history only"):
        provider.train_model(history().model_copy(update={"covariates": [covariate]}))
    with pytest.raises(ValueError, match="does not accept"):
        provider.generate_forecast(ForecastDataSet(covariates=[covariate]))


def test_wea_clock_change_uses_distinct_utc_timestamps() -> None:
    issue = int(pd.Timestamp("2025-10-26T00:00:00Z").timestamp() * 1000)
    model = WEAModelProvider(config()).train_model(history(issue=issue))
    times = pd.to_datetime([p.x for p in model.predict()], unit="ms", utc=True)
    assert times.is_unique and (np.diff(times.astype("int64").to_numpy()) == HOUR * 1_000_000).all()


def test_wea_shared_endpoint_belongs_to_older_bucket() -> None:
    cfg = config(past_period="P1D", past_count=2)
    data = TrainingDataSet(
        target=AssetFeatureDatapoints(
            feature_name="power",
            datapoints=[
                AssetDatapoint(x=ISSUE - 48 * HOUR, y=10),
                AssetDatapoint(x=ISSUE - 24 * HOUR, y=20),
                AssetDatapoint(x=ISSUE - 24 * HOUR + 1, y=30),
                AssetDatapoint(x=ISSUE, y=40),
            ],
        )
    )
    forecast = WEAModelProvider(cfg).train_model(data).predict()
    assert forecast[-1].y == pytest.approx(40 * (2 / 3) + 20 * (1 / 3))
