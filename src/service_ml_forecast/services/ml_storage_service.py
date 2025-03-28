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
import os
import tempfile

from service_ml_forecast import find_project_root
from service_ml_forecast.config import env

logger = logging.getLogger(__name__)


class MLStorageService:
    def __init__(self) -> None:
        self.app_root = find_project_root()

    def save(self, model: str, path: str) -> bool:
        """Atomically save a model to a file."""
        file_path = f"{self.app_root}{env.MODELS_DIR}/{path}"
        dir_path = os.path.dirname(file_path)

        try:
            # Create directory if it doesn't exist
            os.makedirs(dir_path, exist_ok=True)

            with tempfile.NamedTemporaryFile(mode="w", dir=dir_path, delete=False) as temp_file:
                temp_file.write(model)
                temp_file.flush()
                os.fsync(temp_file.fileno())

                # Rename the temporary file to the target file
                os.replace(temp_file.name, file_path)

            logger.info(f"Saved model to {file_path}")
            return True
        except OSError:
            logger.error(f"Failed to save model to {file_path}")
            return False

    def load(self, path: str) -> str | None:
        """Load a model from a file."""
        file_path = f"{self.app_root}{env.MODELS_DIR}/{path}"

        try:
            with open(file_path) as file:
                return file.read()
        except FileNotFoundError:
            logger.error(f"Failed to load model from {file_path}")
            return None

    def delete(self, path: str) -> bool:
        """Delete a model from a file."""
        file_path = f"{self.app_root}{env.MODELS_DIR}/{path}"

        try:
            os.remove(file_path)
            logger.info(f"Deleted model from {file_path}")
            return True
        except OSError:
            logger.error(f"Failed to delete model from {file_path}")
            return False
