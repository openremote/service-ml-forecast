"""Failure-path checks for model revision publication and forecast gating."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from service_ml_forecast.common.exceptions import ResourceNotFoundError, ResourceValidationError
from service_ml_forecast.config import DIRS
from service_ml_forecast.models.model_config import (
    LightGBMModelConfig,
    ModelConfig,
    ProphetModelConfig,
    TargetAssetDatapointsFeature,
    WEAModelConfig,
    XGBoostModelConfig,
)
from service_ml_forecast.services.model_storage_service import ModelStorageService


class FakeModel:
    training_series: None = None
    training_cutoff: str | None = None

    def __init__(self, payload: bytes = b"trained model") -> None:
        self.payload = payload

    def save(self, path: Path) -> None:
        path.write_bytes(self.payload)

    @classmethod
    def load(cls, path: Path) -> FakeModel:
        payload = path.read_bytes()
        if not payload:
            raise ValueError("Empty artifact")
        return cls(payload)


def config(model_type: str, model_id: UUID | None = None) -> ModelConfig:
    common = {
        "id": model_id or uuid4(),
        "realm": "gems",
        "name": "Lifecycle test",
        "enabled": True,
        "target": TargetAssetDatapointsFeature(
            asset_id="4naJ3T4B7l7K6XP41dQNdx", attribute_name="power", training_data_period="P1M"
        ),
        "forecast_interval": "P1D",
        "forecast_periods": 24,
        "forecast_frequency": "1h",
    }
    config_types: dict[
        str, type[ProphetModelConfig] | type[XGBoostModelConfig] | type[LightGBMModelConfig] | type[WEAModelConfig]
    ] = {
        "prophet": ProphetModelConfig,
        "xgboost": XGBoostModelConfig,
        "lightgbm": LightGBMModelConfig,
        "wea": WEAModelConfig,
    }
    return config_types[model_type].model_validate(common)


@pytest.fixture
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModelStorageService:
    monkeypatch.setattr(DIRS, "ML_MODELS_DATA_DIR", tmp_path)
    return ModelStorageService()


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("prophet", "xgboost"),
        ("prophet", "lightgbm"),
        ("xgboost", "prophet"),
        ("xgboost", "lightgbm"),
        ("lightgbm", "prophet"),
        ("lightgbm", "xgboost"),
    ],
)
def test_all_model_type_changes_reject_prior_artifact(storage: ModelStorageService, before: str, after: str) -> None:
    first = config(before)
    second = config(after, first.id)
    storage.save(FakeModel(), first.id, first)
    assert storage.get_ready_manifest(first)["model_type"] == before
    with pytest.raises(ResourceValidationError, match="does not match"):
        storage.get_ready_manifest(second)


def test_parameter_change_rejects_prior_artifact(storage: ModelStorageService) -> None:
    first = config("xgboost")
    assert isinstance(first, XGBoostModelConfig)
    storage.save(FakeModel(), first.id, first)
    changed = first.model_copy(update={"n_estimators": first.n_estimators + 1})
    with pytest.raises(ResourceValidationError, match="does not match"):
        storage.get_ready_manifest(changed)
    renamed = first.model_copy(update={"name": "Renamed", "forecast_interval": "PT12H"})
    assert storage.get_ready_manifest(renamed)["config_id"] == str(first.id)


def test_failed_retraining_and_restart_keep_forecasts_blocked(storage: ModelStorageService) -> None:
    current = config("lightgbm")
    storage.save(FakeModel(), current.id, current)
    storage.mark_training_pending(current)
    with pytest.raises(ResourceValidationError, match="pending"):
        storage.get_ready_manifest(current)
    restarted = ModelStorageService()
    with pytest.raises(ResourceValidationError, match="pending"):
        restarted.load(FakeModel, current.id, current)
    storage.save(FakeModel(b"new model"), current.id, current)
    assert restarted.load(FakeModel, current.id, current).payload == b"new model"


def test_interrupted_manifest_publication_keeps_prior_artifact_blocked(
    storage: ModelStorageService, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = config("prophet")
    storage.save(FakeModel(), current.id, current)
    storage.mark_training_pending(current)
    original = storage._atomic_json

    def interrupt(path: Path, payload: dict[str, object]) -> None:
        if path.name.endswith(".pending.json"):
            return original(path, payload)
        raise OSError("interrupted publication")

    monkeypatch.setattr(storage, "_atomic_json", interrupt)
    with pytest.raises(OSError, match="interrupted"):
        storage.save(FakeModel(b"new model"), current.id, current)
    with pytest.raises(ResourceValidationError, match="pending"):
        storage.get_ready_manifest(current)


def test_missing_or_tampered_artifact_never_loads(storage: ModelStorageService) -> None:
    current = config("xgboost")
    with pytest.raises(ResourceNotFoundError, match="manifest"):
        storage.load(FakeModel, current.id, current)
    storage.save(FakeModel(), current.id, current)
    manifest = storage.get_ready_manifest(current)
    (DIRS.ML_MODELS_DATA_DIR / manifest["artifact"]).write_bytes(b"tampered")
    with pytest.raises(ResourceValidationError, match="checksum"):
        storage.load(FakeModel, current.id, current)
