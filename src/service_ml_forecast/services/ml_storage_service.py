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

from service_ml_forecast.config import env
from service_ml_forecast.util.filesystem_util import FileSystemUtil

logger = logging.getLogger(__name__)

MODEL_FILE_PREFIX = "model"


class MLStorageService:
    """Manages the persistence of ML models."""

    def save_model(self, model_content: str, model_id: str, model_file_extension: str) -> bool:
        """Save the serialized ML model to a file.

        Args:
            model_content: The serialized ML model content to save.
            model_id: The ID of the model
            model_file_extension: The extension of the model file
        Returns:
            True if the model was saved successfully, False otherwise.
        """
        relative_path = f"{env.MODELS_DIR}/{MODEL_FILE_PREFIX}-{model_id}{model_file_extension}"

        return FileSystemUtil.save_file(model_content, relative_path)

    def load_model(self, model_id: str, model_file_extension: str) -> str | None:
        """Load the serialized ML model from a file.

        Args:
            model_id: The ID of the model
            model_file_extension: The extension of the model file

        Returns:
            The model content, or None if the model could not be loaded.
        """
        relative_path = f"{env.MODELS_DIR}/{MODEL_FILE_PREFIX}-{model_id}{model_file_extension}"

        return FileSystemUtil.read_file(relative_path)

    def delete_model(self, model_id: str, model_file_extension: str) -> bool:
        """Delete a serialized ML model file.

        Args:
            model_id: The ID of the model
            model_file_extension: The extension of the model file
        Returns:
            True if the model file was deleted successfully, False otherwise.
        """
        relative_path = f"{env.MODELS_DIR}/{MODEL_FILE_PREFIX}-{model_id}{model_file_extension}"

        return FileSystemUtil.delete_file(relative_path)
