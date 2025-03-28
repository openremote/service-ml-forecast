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


import json
import logging

from service_ml_forecast.config import env
from service_ml_forecast.models.ml_config import MLConfig
from service_ml_forecast.util.filesystem_util import FileSystemUtil

logger = logging.getLogger(__name__)

CONFIG_FILE_PREFIX = "config"


class MLConfigStorageService:
    """
    Manages the persistence of ML model configurations.
    """

    def save_config(self, config: MLConfig) -> bool:
        """Atomically save a ML config to the file system.

        Args:
            config: The ML model configuration to save.

        Returns:
            True if the config was saved successfully, False otherwise.
        """
        config_file_path = f"{env.CONFIGS_DIR}/{CONFIG_FILE_PREFIX}-{config.id}.json"

        return FileSystemUtil.save_file(config.model_dump_json(), config_file_path)

    def get_all_configs(self) -> list[MLConfig] | None:
        """Get all the ML model configurations from the file system.

        Returns:
            A list of all the ML model configurations, or None if the configs could not be loaded.
        """
        configs = []

        config_files = FileSystemUtil.get_all_file_names(env.CONFIGS_DIR, ".json")

        for file in config_files:
            config_file_path = f"{env.CONFIGS_DIR}/{file}"
            file_content = FileSystemUtil.read_file(config_file_path)

            if file_content is None:
                logger.error(f"Failed to load config from {config_file_path}")
                continue

            configs.append(MLConfig(**json.loads(file_content)))

        return configs

    def get_config(self, id: str) -> MLConfig | None:
        """Get a ML model configuration from the file system.

        Args:
            id: The id of the ML model configuration to get.

        Returns:
            The ML model configuration, or None if the config could not be loaded.
        """
        config_file_path = f"{env.CONFIGS_DIR}/{CONFIG_FILE_PREFIX}-{id}.json"
        file_content = FileSystemUtil.read_file(config_file_path)

        if file_content is None:
            logger.error(f"Failed to load config from {config_file_path}")
            return None

        return MLConfig(**json.loads(file_content))

    def update_config(self, config: MLConfig) -> bool:
        """Update a ML model configuration in the file system.

        Args:
            config: The ML model configuration to update.

        Returns:
            True if the config was updated successfully, False otherwise.
        """
        if not config.id:
            return False

        config_file_path = f"{env.CONFIGS_DIR}/{CONFIG_FILE_PREFIX}-{config.id}.json"

        return FileSystemUtil.save_file(config.model_dump_json(), config_file_path)

    def delete_config(self, id: str) -> bool:
        """Delete a ML model configuration from the file system.

        Args:
            id: The id of the ML model configuration to delete.

        Returns:
            True if the config was deleted successfully, False otherwise.
        """
        config_file_path = f"{env.CONFIGS_DIR}/{CONFIG_FILE_PREFIX}-{id}.json"

        return FileSystemUtil.delete_file(config_file_path)
