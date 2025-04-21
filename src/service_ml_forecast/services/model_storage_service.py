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

from service_ml_forecast.common.exceptions import ResourceNotFoundError
from service_ml_forecast.common.fs_util import FsUtil
from service_ml_forecast.config import DIRS

logger = logging.getLogger(__name__)


class ModelStorageService:
    """Manages the persistence of ML models."""

    MODEL_FILE_PREFIX = "model"
    DEFAULT_MODEL_FILE_EXTENSION = "json"

    def save(
        self, model_content: str, model_id: UUID, model_file_extension: str = DEFAULT_MODEL_FILE_EXTENSION
    ) -> None:
        """Save a model file. Will overwrite existing model file.

        Args:
            model_content: The model in serialized format.
            model_id: The ID of the model.
            model_file_extension: The extension of the model file.
        """
        path = self._get_model_file_path(model_id, model_file_extension)

        # Overwrite the existing model file
        FsUtil.create_file(path, model_content, overwrite=True)

    def get(self, model_id: UUID, model_file_extension: str = DEFAULT_MODEL_FILE_EXTENSION) -> str:
        """Get a model file.

        Args:
            model_id: The ID of the model.
            model_file_extension: The extension of the model file.

        Returns:
            The model file content.

        Raises:
            ResourceNotFoundError: Model file was not found.
        """
        path = self._get_model_file_path(model_id, model_file_extension)

        try:
            return FsUtil.read_file(path)
        except FileNotFoundError as e:
            logger.error(f"Cannot get model file: {model_id} - does not exist: {e}")
            raise ResourceNotFoundError(f"Cannot get model file: {model_id} - does not exist") from e

    def delete(self, model_id: UUID, model_file_extension: str = DEFAULT_MODEL_FILE_EXTENSION) -> None:
        """Delete a model file.

        Args:
            model_id: The ID of the model.
            model_file_extension: The extension of the model file.

        Raises:
            ResourceNotFoundError: Model file was not found.
        """
        path = self._get_model_file_path(model_id, model_file_extension)

        try:
            FsUtil.delete_file(path)
        except FileNotFoundError as e:
            logger.error(f"Cannot delete model file: {model_id} - does not exist: {e}")
            raise ResourceNotFoundError(f"Cannot delete model file: {model_id} - does not exist") from e

    def _get_model_file_path(self, model_id: UUID, model_file_extension: str) -> Path:
        return Path(f"{DIRS.ML_MODELS_DIR}/{self.MODEL_FILE_PREFIX}-{model_id}.{model_file_extension}")
