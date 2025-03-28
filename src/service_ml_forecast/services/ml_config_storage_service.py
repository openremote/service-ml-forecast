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
from service_ml_forecast.util.fs_util import FsUtil

logger = logging.getLogger(__name__)

class MLConfigStorageService:
    """
    Manages the persistence of ML model configurations.
    """

    CONFIG_FILE_PREFIX = "config"

    def save_config(self, config: MLConfig) -> bool:
        """Save an ML model configuration to the file system."""
        config_file_path = f"{env.CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config.id}.json"

        return FsUtil.save_file(config.model_dump_json(), config_file_path)

    def get_all_configs(self) -> list[MLConfig] | None:
        """Get all the ML model configurations from the file system."""
        configs = []

        config_files = FsUtil.get_all_file_names(env.CONFIGS_DIR, ".json")

        for file in config_files:
            config_file_path = f"{env.CONFIGS_DIR}/{file}"
            file_content = FsUtil.read_file(config_file_path)

            if file_content is None:
                logger.error(f"Failed to load config from {config_file_path}")
                continue

            configs.append(MLConfig(**json.loads(file_content)))

        return configs

    def get_config(self, config_id: str) -> MLConfig | None:
        """Get an ML model configuration from the file system."""
        config_file_path = f"{env.CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config_id}.json"
        file_content = FsUtil.read_file(config_file_path)

        if file_content is None:
            logger.error(f"Failed to load config from {config_file_path}")
            return None

        return MLConfig(**json.loads(file_content))

    def update_config(self, config: MLConfig) -> bool:
        """Update an ML model configuration in the file system."""
        if not config.id:
            return False

        config_file_path = f"{env.CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config.id}.json"

        return FsUtil.save_file(config.model_dump_json(), config_file_path)

    def delete_config(self, config_id: str) -> bool:
        """Delete an ML model configuration from the file system."""
        config_file_path = f"{env.CONFIGS_DIR}/{self.CONFIG_FILE_PREFIX}-{config_id}.json"

        return FsUtil.delete_file(config_file_path)
