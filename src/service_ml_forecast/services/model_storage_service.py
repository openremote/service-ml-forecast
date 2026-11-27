# Copyright 2025, OpenRemote Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Store Darts models with a checked, versioned publication manifest."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import logging
import os
import platform
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, Protocol, Self, TypeVar
from uuid import UUID, uuid4

from service_ml_forecast.common.exceptions import ResourceNotFoundError, ResourceValidationError
from service_ml_forecast.common.model_lock import model_operation_lock
from service_ml_forecast.config import DIRS
from service_ml_forecast.models.model_config import BaseModelConfig

logger = logging.getLogger(__name__)


class StoredForecastModel(Protocol):
    """Persistence contract shared by Darts models and target-only baselines."""

    def save(self, path: Path) -> None: ...

    @classmethod
    def load(cls, path: Path) -> Self: ...


StoredModel = TypeVar("StoredModel", bound=StoredForecastModel)
PINNED_MANIFESTS: ContextVar[dict[str, dict[str, Any]] | None] = ContextVar("pinned_model_manifests", default=None)


class ModelStorageService:
    """Publish a model file first, then atomically point a manifest at it."""

    MODEL_FILE_PREFIX = "model"
    DEFAULT_MODEL_FILE_EXTENSION = "pkl"
    FINGERPRINT_EXCLUDED: ClassVar[set[str]] = {
        "name",
        "enabled",
        "forecast_interval",
        "training_interval",
    }

    @staticmethod
    def fingerprint(config: BaseModelConfig) -> str:
        material = config.model_dump(mode="json", exclude=ModelStorageService.FINGERPRINT_EXCLUDED)
        normalized = json.dumps(material, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def package_versions() -> dict[str, str]:
        versions = {"python": platform.python_version()}
        for name in ("u8darts", "xgboost", "lightgbm", "prophet"):
            try:
                versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                versions[name] = "unavailable"
        return versions

    def mark_training_pending(self, config: BaseModelConfig) -> None:
        with model_operation_lock(config.id, "publish"):
            self._atomic_json(
                self._pending_path(config.id),
                {
                    "config_id": str(config.id),
                    "config_fingerprint": self.fingerprint(config),
                    "started_at_utc": datetime.now(UTC).isoformat(),
                },
            )

    def save(self, model: StoredForecastModel, model_id: UUID, config: BaseModelConfig | None = None) -> None:
        """Validate a new artifact before publishing its manifest."""
        with model_operation_lock(model_id, "publish"):
            self._save(model, model_id, config)

    def _save(self, model: StoredForecastModel, model_id: UUID, config: BaseModelConfig | None) -> None:
        if config is None:
            path = self._get_model_file_path(model_id, self.DEFAULT_MODEL_FILE_EXTENSION)
            path.parent.mkdir(parents=True, exist_ok=True)
            model.save(path)
            return
        if config.id != model_id:
            raise ResourceValidationError("Model ID does not match its configuration")
        directory = DIRS.ML_MODELS_DATA_DIR
        directory.mkdir(parents=True, exist_ok=True)
        revision = uuid4().hex
        artifact = directory / f"model-{model_id}-{revision}.pkl"
        temporary = directory / f".model-{model_id}-{revision}.tmp.pkl"
        try:
            model.save(temporary)
            type(model).load(temporary)
            digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
            training_series = getattr(model, "training_series", None)
            cutoff = (
                training_series.end_time().isoformat()
                if training_series is not None
                else getattr(model, "training_cutoff", None)
            )
            self._check_publication_order(config, cutoff)
            os.replace(temporary, artifact)
            manifest: dict[str, Any] = {
                "schema_version": 1,
                "config_id": str(model_id),
                "config_fingerprint": self.fingerprint(config),
                "model_type": config.type.value,
                "target": config.target.model_dump(mode="json"),
                "revision": revision,
                "artifact": artifact.name,
                "artifact_sha256": digest,
                "trained_at_utc": datetime.now(UTC).isoformat(),
                "training_cutoff": cutoff,
                "package_versions": self.package_versions(),
            }
            self._atomic_json(self._manifest_path(model_id), manifest)
            self._pending_path(model_id).unlink(missing_ok=True)
            logger.info("Published model revision %s for %s", revision, model_id)
        finally:
            temporary.unlink(missing_ok=True)

    def _check_publication_order(self, config: BaseModelConfig, cutoff: str | None) -> None:
        pending = self._pending_path(config.id)
        if pending.exists():
            marker = json.loads(pending.read_text(encoding="utf-8"))
            if marker.get("config_fingerprint") != self.fingerprint(config):
                raise ResourceValidationError("Training was superseded by a changed configuration")
        path = self._manifest_path(config.id)
        if not path.exists():
            return
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return  # A valid retraining may repair an invalid old manifest.
        if previous.get("config_fingerprint") != self.fingerprint(config) or previous.get("training_cutoff") is None:
            return

        def instant(value: str) -> datetime:
            result = datetime.fromisoformat(value)
            return result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)

        if cutoff is None or instant(cutoff) < instant(previous["training_cutoff"]):
            raise ResourceValidationError("Cannot publish an older training result over a newer model")

    @contextmanager
    def pin_forecast(self, config: BaseModelConfig) -> Iterator[dict[str, Any]]:
        """Make provider loads use the exact immutable artifact captured here."""
        manifest = self.get_ready_manifest(config)
        token = PINNED_MANIFESTS.set({**(PINNED_MANIFESTS.get() or {}), str(config.id): manifest})
        try:
            yield manifest
        finally:
            PINNED_MANIFESTS.reset(token)

    def get_ready_manifest(self, config: BaseModelConfig) -> dict[str, Any]:
        """Reject pending, missing, mismatched, or damaged model artifacts."""
        if self._pending_path(config.id).exists():
            raise ResourceValidationError(f"Model training is pending for {config.id}")
        path = self._manifest_path(config.id)
        if not path.exists():
            raise ResourceNotFoundError(f"No published model manifest for {config.id}")
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ResourceValidationError(f"Invalid model manifest for {config.id}") from exc
        return self._validate_manifest(config, manifest)

    def _validate_manifest(self, config: BaseModelConfig, manifest: dict[str, Any]) -> dict[str, Any]:
        if (
            manifest.get("schema_version") != 1
            or manifest.get("config_id") != str(config.id)
            or manifest.get("model_type") != config.type.value
            or manifest.get("config_fingerprint") != self.fingerprint(config)
            or manifest.get("target") != config.target.model_dump(mode="json")
            or manifest.get("package_versions") != self.package_versions()

        ):
            raise ResourceValidationError(f"Model artifact does not match config {config.id}")
        artifact_name = manifest.get("artifact")
        if not isinstance(artifact_name, str) or Path(artifact_name).name != artifact_name:
            raise ResourceValidationError(f"Invalid model artifact path for {config.id}")
        artifact = DIRS.ML_MODELS_DATA_DIR / artifact_name
        if not artifact.is_file():
            raise ResourceNotFoundError(f"Model artifact is missing for {config.id}")
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest.get("artifact_sha256"):
            raise ResourceValidationError(f"Model artifact checksum mismatch for {config.id}")
        return manifest

    def load(
        self,
        model_class: type[StoredModel],
        model_id: UUID,
        config: BaseModelConfig | None = None,
    ) -> StoredModel:
        if config is not None:
            if config.id != model_id:
                raise ResourceValidationError("Model ID does not match its configuration")
            manifest = (PINNED_MANIFESTS.get() or {}).get(str(model_id))
            if manifest is None:
                manifest = self.get_ready_manifest(config)
            else:
                self._validate_manifest(config, manifest)
            path = DIRS.ML_MODELS_DATA_DIR / manifest["artifact"]
        else:
            manifest_path = self._manifest_path(model_id)
            if manifest_path.exists():
                fallback_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                path = DIRS.ML_MODELS_DATA_DIR / fallback_manifest["artifact"]
            else:
                path = self._get_model_file_path(model_id, self.DEFAULT_MODEL_FILE_EXTENSION)
        if not path.is_file():
            raise ResourceNotFoundError(f"Cannot get model file: {model_id} - does not exist")
        model = model_class.load(path)
        logger.info("Loaded forecast model from %s -- %s", path, model_id)
        return model

    def delete(self, model_id: UUID) -> None:
        with model_operation_lock(model_id, "publish"):
            self._delete(model_id)

    def _delete(self, model_id: UUID) -> None:
        paths = [self._manifest_path(model_id), self._pending_path(model_id)]
        paths.extend(DIRS.ML_MODELS_DATA_DIR.glob(f"model-{model_id}*.pkl"))
        existing = [path for path in paths if path.exists()]
        if not existing:
            raise ResourceNotFoundError(f"Cannot delete model file: {model_id} - does not exist")
        for path in existing:
            path.unlink()

    def record_forecast(
        self,
        config: BaseModelConfig,
        first_ms: int,
        last_ms: int,
        count: int,
        *,
        manifest: dict[str, Any],
    ) -> None:
        """Keep local provenance for Manager rows, whose table has no model revision."""
        self._validate_manifest(config, manifest)
        entry = {
            "written_at_utc": datetime.now(UTC).isoformat(),
            "config_id": str(config.id),
            "revision": manifest["revision"],
            "config_fingerprint": manifest["config_fingerprint"],
            "artifact_sha256": manifest["artifact_sha256"],
            "asset_id": config.target.asset_id,
            "attribute_name": config.target.attribute_name,
            "first_timestamp_ms": first_ms,
            "last_timestamp_ms": last_ms,
            "count": count,
        }
        path = DIRS.ML_MODELS_DATA_DIR / "forecast-audit.jsonl"
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, sort_keys=True) + "\n")

    @staticmethod
    def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _manifest_path(model_id: UUID) -> Path:
        return DIRS.ML_MODELS_DATA_DIR / f"model-{model_id}.json"

    @staticmethod
    def _pending_path(model_id: UUID) -> Path:
        return DIRS.ML_MODELS_DATA_DIR / f"model-{model_id}.pending.json"

    def _get_model_file_path(self, model_id: UUID, model_file_extension: str) -> Path:
        return DIRS.ML_MODELS_DATA_DIR / f"{self.MODEL_FILE_PREFIX}-{model_id}.{model_file_extension}"
