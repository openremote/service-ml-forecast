"""Fault injection at the scheduler/Manager boundary; no real network writes."""

from unittest.mock import Mock

import pandas as pd
import pytest
from openremote_client import AssetDatapoint

from service_ml_forecast.common.exceptions import ResourceNotFoundError, ResourceValidationError
from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.feature_data_wrappers import ForecastResult
from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.services import model_scheduler as scheduler
from service_ml_forecast.services.model_storage_service import ModelStorageService
from tests.services.test_model_artifact_lifecycle import FakeModel, config

type PublicationCase = tuple[ModelConfig, Mock, Mock, Mock, Mock, ForecastResult]


@pytest.fixture(params=["prophet", "xgboost", "lightgbm", "wea"])
def publication_case(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> PublicationCase:
    current = config(request.param)
    storage = ModelStorageService()
    points = [AssetDatapoint(x=1_800_000_000_000 + i * 3_600_000, y=20.0 + i) for i in range(24)]
    model = FakeModel()
    model.training_cutoff = pd.Timestamp(points[0].x - 3_600_000, unit="ms").isoformat()
    storage.save(model, current.id, current)
    result = ForecastResult(
        asset_id=current.target.asset_id, attribute_name=current.target.attribute_name, datapoints=points
    )
    provider = Mock(generate_forecast=Mock(return_value=result))
    configs = Mock(get=Mock(return_value=current))
    service = Mock(get_forecast_dataset=Mock(return_value=None), write_predicted_datapoints=Mock(return_value=True))
    audit = Mock()
    monkeypatch.setattr(scheduler, "ModelConfigService", lambda *_: configs)
    monkeypatch.setattr(ModelProviderFactory, "create_provider", lambda *_: provider)
    monkeypatch.setattr(TimeUtil, "get_timestamp_ms", lambda: points[0].x - 1)
    monkeypatch.setattr(ModelStorageService, "record_forecast", audit)
    return current, service, provider, configs, audit, result


def test_successful_write_records_one_audit_entry(publication_case: PublicationCase) -> None:
    current, service, _, _, audit, _ = publication_case
    scheduler._model_forecast_job(current, service)
    service.write_predicted_datapoints.assert_called_once()
    audit.assert_called_once()


@pytest.mark.parametrize("failure", ["false", "timeout"])
def test_manager_write_failure_does_not_record_success(publication_case: PublicationCase, failure: str) -> None:
    current, service, _, _, audit, _ = publication_case
    if failure == "false":
        service.write_predicted_datapoints.return_value = False
        scheduler._model_forecast_job(current, service)
    else:
        service.write_predicted_datapoints.side_effect = TimeoutError("simulated Manager timeout")
        with pytest.raises(TimeoutError):
            scheduler._model_forecast_job(current, service)
    service.write_predicted_datapoints.assert_called_once()
    audit.assert_not_called()


@pytest.mark.parametrize("fault", ["asset", "attribute", "short", "nan", "duplicate", "reversed", "stale"])
def test_invalid_provider_output_cannot_reach_writer(
    publication_case: PublicationCase, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    current, service, _, _, audit, result = publication_case
    if fault == "asset":
        result.asset_id = "wrong" * 4 + "xx"
    elif fault == "attribute":
        result.attribute_name = "anotherAttribute"
    elif fault == "short":
        result.datapoints.pop()
    elif fault == "nan":
        result.datapoints[3].y = float("nan")
    elif fault == "duplicate":
        result.datapoints[3].x = result.datapoints[2].x
    elif fault == "reversed":
        result.datapoints.reverse()
    else:
        monkeypatch.setattr(TimeUtil, "get_timestamp_ms", lambda: result.datapoints[0].x)
    with pytest.raises(ResourceValidationError):
        scheduler._model_forecast_job(current, service)
    service.write_predicted_datapoints.assert_not_called()
    audit.assert_not_called()


@pytest.mark.parametrize("change", ["disabled", "parameters", "deleted"])
def test_configuration_change_during_prediction_blocks_publication(
    publication_case: PublicationCase, change: str
) -> None:
    current, service, _, configs, audit, _ = publication_case
    error: type[Exception]
    if change == "deleted":
        configs.get.side_effect = [current, ResourceNotFoundError("configuration deleted")]
        error = ResourceNotFoundError
    else:
        changed = current.model_copy(deep=True)
        if change == "disabled":
            changed.enabled = False
        else:
            changed.forecast_periods += 1
        configs.get.side_effect = [current, changed]
        error = ResourceValidationError
    with pytest.raises(error):
        scheduler._model_forecast_job(current, service)
    service.write_predicted_datapoints.assert_not_called()
    audit.assert_not_called()


def test_history_timeout_keeps_previous_artifact_blocked(publication_case: PublicationCase) -> None:
    current, service, _, _, audit, _ = publication_case
    service.get_training_dataset = Mock(side_effect=TimeoutError("simulated history timeout"))
    with pytest.raises(TimeoutError):
        scheduler._model_training_job(current, service)
    with pytest.raises(ResourceValidationError, match="pending"):
        scheduler._model_forecast_job(current, service)
    service.write_predicted_datapoints.assert_not_called()
    audit.assert_not_called()


@pytest.mark.parametrize("shift_ms", [3_600_000, 17 * 60_000])
def test_shifted_complete_forecast_cannot_reach_writer(publication_case: PublicationCase, shift_ms: int) -> None:
    current, service, _, _, audit, result = publication_case
    for point in result.datapoints:
        point.x += shift_ms
    with pytest.raises(ResourceValidationError, match="training cutoff"):
        scheduler._model_forecast_job(current, service)
    service.write_predicted_datapoints.assert_not_called()
    audit.assert_not_called()


@pytest.mark.parametrize("cutoff", [None, "not-a-timestamp", "NaT"])
def test_invalid_manifest_cutoff_cannot_reach_writer(publication_case: PublicationCase, cutoff: str | None) -> None:
    current, service, _, _, audit, _ = publication_case
    storage = ModelStorageService()
    manifest = storage.get_ready_manifest(current)
    manifest["training_cutoff"] = cutoff
    storage._atomic_json(storage._manifest_path(current.id), manifest)
    with pytest.raises(ResourceValidationError, match="training cutoff"):
        scheduler._model_forecast_job(current, service)
    service.write_predicted_datapoints.assert_not_called()
    audit.assert_not_called()


def test_timezone_aware_manifest_cutoff_uses_utc(publication_case: PublicationCase) -> None:
    current, service, _, _, audit, _ = publication_case
    storage = ModelStorageService()
    manifest = storage.get_ready_manifest(current)
    manifest["training_cutoff"] = (
        pd.Timestamp(manifest["training_cutoff"]).tz_localize("UTC").tz_convert("Europe/Amsterdam").isoformat()
    )
    storage._atomic_json(storage._manifest_path(current.id), manifest)
    scheduler._model_forecast_job(current, service)
    service.write_predicted_datapoints.assert_called_once()
    audit.assert_called_once()


def test_wea_raw_partial_hour_cutoff_keeps_next_hour_boundary(publication_case: PublicationCase) -> None:
    current, service, _, _, audit, _ = publication_case
    if current.type.value != "wea":
        pytest.skip("Raw timestamp anchoring applies to WEA")
    storage = ModelStorageService()
    manifest = storage.get_ready_manifest(current)
    manifest["training_cutoff"] = (pd.Timestamp(manifest["training_cutoff"]) + pd.Timedelta(minutes=47)).isoformat()
    storage._atomic_json(storage._manifest_path(current.id), manifest)
    scheduler._model_forecast_job(current, service)
    service.write_predicted_datapoints.assert_called_once()
    audit.assert_called_once()
