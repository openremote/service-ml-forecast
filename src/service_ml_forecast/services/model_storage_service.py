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

from service_ml_forecast.common.exceptions import ResourceNotFoundError
from service_ml_forecast.common.fs_util import FsUtil
from service_ml_forecast.config import ENV

logger = logging.getLogger(__name__)


class ModelStorageService:
    """Manages the persistence of ML models."""

    MODEL_FILE_PREFIX = "model"

    def save(self, model_content: str, model_id: UUID, model_file_extension: str) -> None:
        """Save a trained model.

        Args:
            model_content: The content of the model to save.
            model_id: The ID of the model to save.
            model_file_extension: The extension of the model file.
        """
        path = self._get_model_file_path(model_id, model_file_extension)

        FsUtil.save_file(model_content, path)

    def load(self, model_id: UUID, model_file_extension: str) -> str:
        """Load a previously saved model.

        Args:
            model_id: The ID of the model to load.
            model_file_extension: The extension of the model file.

        Returns:
            The content of the model file.

        Raises:
            ResourceNotFoundError: If the model file does not exist.
        """
        path = self._get_model_file_path(model_id, model_file_extension)

        if not path.exists():
            logger.error(f"Model not found: {model_id}")
            raise ResourceNotFoundError(f"Model not found: {model_id}")

        return FsUtil.read_file(path)

    def delete(self, model_id: UUID, model_file_extension: str) -> None:
        """Delete a previously saved model.

        Args:
            model_id: The ID of the model to delete.
            model_file_extension: The extension of the model file.

        Raises:
            ResourceNotFoundError: If the model file does not exist.
        """
        path = self._get_model_file_path(model_id, model_file_extension)

        if not path.exists():
            logger.error(f"Model not found: {model_id}")
            raise ResourceNotFoundError(f"Model not found: {model_id}")

        FsUtil.delete_file(path)

    def _get_model_file_path(self, model_id: UUID, model_file_extension: str) -> Path:
        return Path(f"{ENV.ML_MODELS_DIR}/{self.MODEL_FILE_PREFIX}-{model_id}.{model_file_extension}")
