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

from service_ml_forecast.config import ENV
from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.util.fs_util import FsUtil

logger = logging.getLogger(__name__)


class ModelConfigService:
    """Manages the persistence of ML model configurations."""

    CONFIG_FILE_PREFIX = "config"
    CONFIG_FILE_EXTENSION = "json"

    def save(self, config: ModelConfig) -> ModelConfig | None:
        """Saves the ML model configuration.

        Args:
            config: The ML model configuration to save

        Returns:
            ModelConfig | None: The saved ML model configuration, or None if the configuration was not saved
        """

        path = Path(f"{self.dir}/{self.CONFIG_FILE_PREFIX}-{config.id}.json")
        file_saved = FsUtil.save_file(config.model_dump_json(), path)

        if not file_saved:
            logger.error(f"Failed to save config {config.id}")
            return None

        logger.info(f"Saved config {config.id}")
        return config

    def get_all(self, realm: str | None = None) -> list[ModelConfig]:
        """Get all available ML model configurations.

        Returns:
            list[MLModelConfig]: The list of ML model configurations
        """

        configs = []
        config_files = FsUtil.get_all_file_names(self.dir, "json")

        if config_files is None or len(config_files) == 0:
            return []

        for file in config_files:
            path = Path(f"{ENV.ML_CONFIGS_DIR}/{file}")

            file_content = FsUtil.read_file(path)

            if file_content is None:
                logger.error(f"Failed to read config file {path}")
                continue  # Skip the file if it cannot be read

            try:
                config = self.parse(file_content)
                if realm is None or config.realm == realm:
                    configs.append(config)
            except ValidationError as e:
                logger.exception(f"Failed to parse config file {path}: {e}")
                continue  # Skip the file if it cannot be parsed

        return configs

    def get(self, config_id: UUID) -> ModelConfig | None:
        """Get the ML model configuration based on the provided ID.

        Args:
            config_id: The ID of the ML model configuration

        Returns:
            MLModelConfig | None: The ML model configuration, or None if the configuration was not found
        """

        path = Path(f"{self.dir}/{self.CONFIG_FILE_PREFIX}-{config_id}.json")
        file_content = FsUtil.read_file(path)

        if file_content is None:
            logger.error(f"Failed to read config file {path}")
            return None

        try:
            config = self.parse(file_content)
            if config.id == config_id:
                return config
            else:
                logger.exception(f"Config ID mismatch for {config_id} and {config.id}")
                return None
        except ValidationError as e:
            logger.exception(f"Failed to parse config file {path}: {e}")
            return None

    def update(self, config: ModelConfig) -> ModelConfig | None:
        """Update the ML model configuration.

        Args:
            config: The ML model configuration to update

        Returns:
            ModelConfig: The updated ML model configuration
        """

        path = Path(f"{self.dir}/{self.CONFIG_FILE_PREFIX}-{config.id}.json")
        file_saved = FsUtil.save_file(config.model_dump_json(), path)

        if not file_saved:
            logger.error(f"Failed to update config {config.id}")
            return None

        logger.info(f"Updated config {config.id}")
        return config

    def delete(self, config_id: UUID) -> bool:
        """Delete the ML model configuration based on the provided ID."""

        path = Path(f"{self.dir}/{self.CONFIG_FILE_PREFIX}-{config_id}.json")
        file_deleted = FsUtil.delete_file(path)

        if not file_deleted:
            logger.error(f"Failed to delete config {config_id}")
        else:
            logger.info(f"Deleted config {config_id}")

        return file_deleted

    def parse(self, json: str) -> ModelConfig:
        """Parse the provided ML model configuration JSON string into the concrete type."""

        model_adapter: TypeAdapter[ModelConfig] = TypeAdapter(ModelConfig)
        return model_adapter.validate_json(json)

    def _get_config_file_path(self, config_id: UUID) -> Path:
        return Path(f"{ENV.ML_CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config_id}.{self.CONFIG_FILE_EXTENSION}")
