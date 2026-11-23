"""Regression cases for publication races found in the real WEA campaign."""

import json
import subprocess
import sys
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from service_ml_forecast.common.exceptions import ResourceValidationError
from service_ml_forecast.common.model_lock import model_operation_lock
from service_ml_forecast.config import DIRS
from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.feature_data_wrappers import ForecastDataSet, ForecastResult, TrainingDataSet
from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.services import model_scheduler as scheduler
from service_ml_forecast.services.model_storage_service import ModelStorageService
from tests.services.test_model_artifact_lifecycle import FakeModel
from tests.services.test_publication_robustness import PublicationCase

pytest_plugins = ["tests.services.test_publication_robustness"]

REAL_RECORD_FORECAST = ModelStorageService.record_forecast


def replacement(current: ModelConfig, cutoff: str | None, payload: bytes = b"new revision") -> None:
    model = FakeModel(payload)
    model.training_cutoff = cutoff
    ModelStorageService().save(model, current.id, current)


def test_new_revision_during_prediction_blocks_old_values(publication_case: PublicationCase) -> None:
    current, service, provider, _, audit, result = publication_case
    storage = ModelStorageService()
    original = storage.get_ready_manifest(current)

    def generate(_: ForecastDataSet | None) -> ForecastResult:
        replacement(current, original["training_cutoff"])
        return result

    provider.generate_forecast.side_effect = generate
    with pytest.raises(ResourceValidationError, match="revision"):
        scheduler._model_forecast_job(current, service)
    service.write_predicted_datapoints.assert_not_called()
    audit.assert_not_called()


def test_revision_published_during_write_does_not_relabel_audit(
    publication_case: PublicationCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    current, service, _, _, _, _ = publication_case
    storage = ModelStorageService()
    original = storage.get_ready_manifest(current)
    monkeypatch.setattr(ModelStorageService, "record_forecast", REAL_RECORD_FORECAST)

    def write(*_: object) -> bool:
        replacement(current, original["training_cutoff"])
        return True

    service.write_predicted_datapoints.side_effect = write
    scheduler._model_forecast_job(current, service)
    entry = json.loads((DIRS.ML_MODELS_DATA_DIR / "forecast-audit.jsonl").read_text())
    assert storage.get_ready_manifest(current)["revision"] != original["revision"]
    assert entry["revision"] == original["revision"]


def test_older_result_cannot_replace_newer_manifest(publication_case: PublicationCase) -> None:
    current, _, _, _, _, _ = publication_case
    storage = ModelStorageService()
    original = storage.get_ready_manifest(current)
    older = (pd.Timestamp(original["training_cutoff"]) - pd.Timedelta(hours=1)).isoformat()
    with pytest.raises(ResourceValidationError, match="older"):
        replacement(current, older)
    assert storage.get_ready_manifest(current)["revision"] == original["revision"]


def test_pinned_load_keeps_original_artifact_then_resets(publication_case: PublicationCase) -> None:
    current, _, _, _, _, _ = publication_case
    storage = ModelStorageService()
    original = storage.get_ready_manifest(current)
    with storage.pin_forecast(current):
        replacement(current, original["training_cutoff"], b"new payload")
        assert storage.load(FakeModel, current.id, current).payload == b"trained model"
    assert storage.load(FakeModel, current.id, current).payload == b"new payload"


def test_second_training_job_is_rejected_before_touching_pending_state(
    publication_case: PublicationCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    current, service, _, _, _, result = publication_case
    storage = ModelStorageService()
    original = storage.get_ready_manifest(current)
    entered = Event()
    release = Event()
    errors = []
    service.get_training_dataset = Mock(
        return_value=SimpleNamespace(target=SimpleNamespace(datapoints=result.datapoints))
    )
    model = FakeModel(b"retrained")
    model.training_cutoff = original["training_cutoff"]

    def train(_: TrainingDataSet) -> FakeModel:
        entered.set()
        if not release.wait(10):
            raise TimeoutError("coordination timeout")
        return model

    provider = SimpleNamespace(train_model=train, save_model=lambda m: storage.save(m, current.id, current))
    monkeypatch.setattr(ModelProviderFactory, "create_provider", lambda _: provider)

    def first() -> None:
        try:
            scheduler._model_training_job(current, service)
        except Exception as exc:
            errors.append(exc)

    thread = Thread(target=first)
    thread.start()
    try:
        assert entered.wait(10)
        pending_before = storage._pending_path(current.id).read_bytes()
        with pytest.raises(ResourceValidationError, match="already in progress"):
            scheduler._model_training_job(current, service)
        assert storage._pending_path(current.id).read_bytes() == pending_before
    finally:
        release.set()
        thread.join(10)
    assert not thread.is_alive() and not errors
    assert storage.get_ready_manifest(current)["training_cutoff"] == original["training_cutoff"]


def test_os_lock_blocks_other_process_and_releases_after_process_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(DIRS, "ML_MODELS_DATA_DIR", tmp_path)
    script = """
from pathlib import Path
import sys,os
from service_ml_forecast.config import DIRS
from service_ml_forecast.common.model_lock import model_operation_lock
from service_ml_forecast.common.exceptions import ResourceValidationError
DIRS.ML_MODELS_DATA_DIR=Path(sys.argv[1])
try:
    with model_operation_lock('test-process','training'):
        os._exit(17)
except ResourceValidationError:
    sys.exit(0)
"""
    with model_operation_lock("test-process", "training"):
        blocked = subprocess.run(
            [sys.executable, "-c", script, str(tmp_path)], capture_output=True, text=True, timeout=20, check=False
        )
    assert blocked.returncode == 0, blocked.stderr
    crashed = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)], capture_output=True, text=True, timeout=20, check=False
    )
    crash_exit_code = 17
    assert crashed.returncode == crash_exit_code, crashed.stderr
    with model_operation_lock("test-process", "training"):
        pass  # os._exit must not leave a stale lock preventing recovery.
