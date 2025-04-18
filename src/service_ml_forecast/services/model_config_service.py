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

import logging
from pathlib import Path
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from service_ml_forecast.common.exceptions import (
    ResourceAlreadyExistsError,
    ResourceDependencyError,
    ResourceNotFoundError,
)
from service_ml_forecast.common.fs_util import FsUtil
from service_ml_forecast.config import DIRS
from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.services.model_storage_service import ModelStorageService
from service_ml_forecast.services.openremote_service import OpenRemoteService

logger = logging.getLogger(__name__)


class ModelConfigService:
    """Manages the persistence of ML model configurations."""

    CONFIG_FILE_PREFIX = "config"
    CONFIG_FILE_EXTENSION = "json"

    def __init__(self, openremote_service: OpenRemoteService):
        self.openremote_service = openremote_service
        self.model_storage_service = ModelStorageService()

    def create(self, config: ModelConfig) -> ModelConfig:
        """Create a new ML model configuration.

        Args:
            config: The model config to create.

        Returns:
            The created model config.

        Raises:
            ResourceAlreadyExistsError: Model config already exists.
            ResourceDependencyError: If asset dependencies are invalid.
        """
        path = self._get_config_file_path(config.id)

        if not self._validate_asset_dependencies(config):
            raise ResourceDependencyError(
                f"Invalid model config: {config.id}! - some of the assets do not exist or are not in the correct realm"
            )

        try:
            FsUtil.create_file(path, config.model_dump_json())
        except FileExistsError as e:
            logger.error(f"Could not create config: {config.id} - already exists: {e}")
            raise ResourceAlreadyExistsError(f"Could not create config: {config.id} - already exists") from e

        return config

    def get_all(self, realm: str | None = None) -> list[ModelConfig]:
        """Get a list of all previously saved ML model configurations.

        Args:
            realm: The realm of the model configs to get.

        Returns:
            A list of all previously saved model configurations.
        """
        existing_config_files = FsUtil.get_files_in_dir(DIRS.ML_CONFIGS_DIR, self.CONFIG_FILE_EXTENSION)

        configs = []

        for file in existing_config_files:
            try:
                file_content = FsUtil.read_file(file)
                config = self._parse(file_content)
                configs.append(config)
            except ValidationError as e:
                logger.error(f"Invalid config file detected: {file}, skipping - details: {e}")
                continue

        # Filter the configs by realm if provided
        return [config for config in configs if realm is None or config.realm == realm]

    def get(self, config_id: UUID) -> ModelConfig:
        """Get the ML model configuration based on the provided ID.

        Args:
            config_id: The ID of the model config to get.

        Returns:
            The model config.

        Raises:
            ResourceNotFoundError: Model config was not found.
        """
        path = self._get_config_file_path(config_id)

        try:
            file_content = FsUtil.read_file(path)
        except FileNotFoundError as e:
            logger.error(f"Cannot get config: {config_id} - does not exist: {e}")
            raise ResourceNotFoundError(f"Cannot get config: {config_id} - does not exist") from e

        return self._parse(file_content)

    def update(self, config_id: UUID, config: ModelConfig) -> ModelConfig:
        """Update the ML model configuration.

        Args:
            config_id: The ID of the model config to update.
            config: The model config to update.

        Returns:
            The updated model config.

        Raises:
            ResourceNotFoundError: Model config was not found.
            ResourceDependencyError: If asset dependencies are invalid.
        """
        path = self._get_config_file_path(config_id)

        if not self._validate_asset_dependencies(config):
            raise ResourceDependencyError(
                f"Invalid model config: {config.id}! - some of the assets do not exist or are not in the correct realm"
            )

        try:
            FsUtil.update_file(path, config.model_dump_json())
        except FileNotFoundError as e:
            logger.error(f"Cannot update config: {config_id} - does not exist: {e}")
            raise ResourceNotFoundError(f"Cannot update config: {config_id} - does not exist") from e

        return config

    def delete(self, config_id: UUID) -> None:
        """Delete the ML model configuration based on the provided ID.

        Args:
            config_id: The ID of the model config to delete.

        Raises:
            ResourceNotFoundError: If the model config does not exist.
        """
        path = self._get_config_file_path(config_id)

        # Delete the config file
        try:
            FsUtil.delete_file(path)
        except FileNotFoundError as e:
            logger.error(f"Cannot delete config: {config_id} - does not exist: {e}")
            raise ResourceNotFoundError(f"Cannot delete config: {config_id} - does not exist") from e

        # Clean up the model file if it exists
        try:
            self.model_storage_service.delete(config_id)
        except ResourceNotFoundError as e:
            logger.info(f"Config did not have a model file to delete: {config_id} - {e}")

    def _parse(self, json: str) -> ModelConfig:
        """Parse the provided ML model config JSON string into the concrete type."""

        model_adapter: TypeAdapter[ModelConfig] = TypeAdapter(ModelConfig)
        return model_adapter.validate_json(json)

    def _validate_asset_dependencies(self, config: ModelConfig) -> bool:
        """Validate the asset dependencies of the model config.

        - Checks whether the target asset and all regressor assets exist
        - Checks whether the target asset and all regressor assets are in the correct realm

        Args:
            config: The model config to validate.

        Returns:
            True if the asset dependencies are valid, False otherwise.
        """
        asset_ids_to_check = []

        # Check target asset
        asset_ids_to_check.append(config.target.asset_id)

        # Check regressor assets if provided
        if config.regressors:
            for regressor in config.regressors:
                asset_ids_to_check.append(regressor.asset_id)

        # Check if all assets exist in the correct realm
        assets = self.openremote_service.get_assets_by_ids(asset_ids_to_check, config.realm)

        if len(assets) != len(asset_ids_to_check):
            logger.error(f"Invalid model config: {config.id} - some assets do not exist in the correct realm")
            return False

        return True

    def _get_config_file_path(self, config_id: UUID) -> Path:
        return Path(f"{DIRS.ML_CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config_id}.{self.CONFIG_FILE_EXTENSION}")
