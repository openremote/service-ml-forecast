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

from service_ml_forecast.config import ENV
from service_ml_forecast.models.ml_model_config import MLModelConfig
from service_ml_forecast.util.fs_util import FsUtil

logger = logging.getLogger(__name__)


class MLConfigStorageService:
    """
    Manages the persistence of ML model configurations.

    Uses the file system to store and retrieve ML model configurations.
    """

    CONFIG_FILE_PREFIX = "config"

    def save_config(self, config: MLModelConfig) -> bool:
        """Save ML model configuration."""
        config_file_path = f"{ENV.CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config.id}.json"

        file_saved = FsUtil.save_file(config.model_dump_json(), config_file_path)

        if not file_saved:
            logger.error(f"Failed to save config {config.id}")

        return file_saved

    def get_all_configs(self) -> list[MLModelConfig] | None:
        """Get all ML model configurations."""
        configs = []
        config_files = FsUtil.get_all_file_names(ENV.CONFIGS_DIR, ".json")

        if config_files is None:
            logger.error("No config files found in {ENV.CONFIGS_DIR}")
            return None

        for file in config_files:
            config_file_path = f"{ENV.CONFIGS_DIR}/{file}"

            file_content = FsUtil.read_file(config_file_path)

            if file_content is None:
                logger.error(f"Failed to read config file {config_file_path}")
                continue
            configs.append(MLModelConfig(**json.loads(file_content)))

        return configs

    def get_config(self, config_id: str) -> MLModelConfig | None:
        """Get ML model configuration."""
        config_file_path = f"{ENV.CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config_id}.json"

        file_content = FsUtil.read_file(config_file_path)

        if file_content is None:
            logger.error(f"Failed to read config file {config_file_path}")
            return None

        return MLModelConfig(**json.loads(file_content))

    def update_config(self, config: MLModelConfig) -> bool:
        """Update ML model configuration."""
        config_file_path = f"{ENV.CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config.id}.json"

        file_saved = FsUtil.save_file(config.model_dump_json(), config_file_path)

        if not file_saved:
            logger.error(f"Failed to update config {config.id}")

        return file_saved

    def delete_config(self, config_id: str) -> bool:
        """Delete ML model configuration."""
        config_file_path = f"{ENV.CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config_id}.json"

        file_deleted = FsUtil.delete_file(config_file_path)

        if not file_deleted:
            logger.error(f"Failed to delete config {config_id}")

        return file_deleted
