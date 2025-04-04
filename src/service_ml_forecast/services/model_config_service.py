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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from pathlib import Path
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from service_ml_forecast.common.exceptions import ResourceAlreadyExistsError, ResourceNotFoundError
from service_ml_forecast.common.fs_util import FsUtil
from service_ml_forecast.config import ENV
from service_ml_forecast.models.model_config import ModelConfig

logger = logging.getLogger(__name__)


class ModelConfigService:
    """Manages the persistence of ML model configurations."""

    CONFIG_FILE_PREFIX = "config"
    CONFIG_FILE_EXTENSION = "json"

    def save(self, config: ModelConfig) -> ModelConfig:
        """Save the ML model configuration.

        Args:
            config: The model config to save.

        Returns:
            The saved model config.

        Raises:
            ResourceAlreadyExistsError: If the model config already exists.
        """
        path = self._get_config_file_path(config.id)

        if FsUtil.file_exists(path):
            logger.error(f"Config already exists: {config.id}")
            raise ResourceAlreadyExistsError(f"Config already exists: {config.id}")

        FsUtil.save_file(config.model_dump_json(), path)
        return config

    def get_all(self, realm: str | None = None) -> list[ModelConfig]:
        """Get all available ML model configurations.

        Args:
            realm: The realm of the model configs to get.

        Returns:
            The list of model configs.
        """
        configs = []
        config_files = FsUtil.get_all_file_names(ENV.ML_CONFIGS_DIR, "json")

        if config_files is None or len(config_files) == 0:
            return []

        for file in config_files:
            path = Path(f"{ENV.ML_CONFIGS_DIR}/{file}")

            if not FsUtil.file_exists(path):
                logger.error(f"Config not found: {file}")
                continue

            file_content = FsUtil.read_file(path)

            try:
                config = self.parse(file_content)
                if realm is None or config.realm == realm:
                    configs.append(config)
            except ValidationError as e:
                logger.exception(f"Failed to parse config file {path}: {e}")
                continue  # Skip the file if it cannot be parsed

        return configs

    def get(self, config_id: UUID) -> ModelConfig:
        """Get the ML model configuration based on the provided ID.

        Args:
            config_id: The ID of the model config to get.

        Returns:
            The model config.

        Raises:
            ResourceNotFoundError: If the model config does not exist.
        """
        path = self._get_config_file_path(config_id)

        if not FsUtil.file_exists(path):
            logger.error(f"Config not found: {config_id}")
            raise ResourceNotFoundError(f"Config not found: {config_id}")

        file_content = FsUtil.read_file(path)

        return self.parse(file_content)

    def update(self, config: ModelConfig) -> ModelConfig:
        """Update the ML model configuration.

        Args:
            config: The model config to update.

        Returns:
            The updated model config.

        Raises:
            ResourceNotFoundError: If the model config does not exist.
        """
        path = self._get_config_file_path(config.id)

        if not FsUtil.file_exists(path):
            logger.error(f"Config not found: {config.id}")
            raise ResourceNotFoundError(f"Config not found: {config.id}")

        FsUtil.save_file(config.model_dump_json(), path)
        return config

    def delete(self, config_id: UUID) -> None:
        """Delete the ML model configuration based on the provided ID.

        Args:
            config_id: The ID of the model config to delete.

        Raises:
            ResourceNotFoundError: If the model config does not exist.
        """
        path = self._get_config_file_path(config_id)

        if not FsUtil.file_exists(path):
            logger.error(f"Config not found: {config_id}")
            raise ResourceNotFoundError(f"Config not found: {config_id}")

        FsUtil.delete_file(path)

    def parse(self, json: str) -> ModelConfig:
        """Parse the provided ML model config JSON string into the concrete type.

        Args:
            json: The JSON string to parse.

        Returns:
            The concrete model config instance.
        """
        model_adapter: TypeAdapter[ModelConfig] = TypeAdapter(ModelConfig)
        return model_adapter.validate_json(json)

    def _get_config_file_path(self, config_id: UUID) -> Path:
        return Path(f"{ENV.ML_CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config_id}.{self.CONFIG_FILE_EXTENSION}")
