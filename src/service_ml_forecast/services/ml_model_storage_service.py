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

from service_ml_forecast.config import ENV
from service_ml_forecast.util.fs_util import FsUtil

logger = logging.getLogger(__name__)


class MLModelStorageService:
    """Manages the persistence of ML models."""

    MODEL_FILE_PREFIX = "model"

    def save(self, model_content: str, model_id: str, model_file_extension: str) -> bool:
        """Save the serialized ML model.

        Args:
            model_content: The serialized ML model
            model_id: The ID of the ML model
            model_file_extension: The extension of the ML model file

        Returns:
            bool: True if the model was saved successfully, False otherwise
        """

        path = Path(f"{ENV.MODELS_DIR}/{self.MODEL_FILE_PREFIX}-{model_id}{model_file_extension}")

        return FsUtil.save_file(model_content, path)

    def load(self, model_id: str, model_file_extension: str) -> str | None:
        """Load the serialized ML model.

        Args:
            model_id: The ID of the ML model
            model_file_extension: The extension of the ML model file

        Returns:
            str | None: The serialized ML model, or None if the model was not found
        """

        path = Path(f"{ENV.MODELS_DIR}/{self.MODEL_FILE_PREFIX}-{model_id}{model_file_extension}")

        return FsUtil.read_file(path)

    def delete(self, model_id: str, model_file_extension: str) -> bool:
        """Delete a serialized ML model.

        Args:
            model_id: The ID of the ML model
            model_file_extension: The extension of the ML model file

        Returns:
            bool: True if the model was deleted successfully, False otherwise
        """

        path = Path(f"{ENV.MODELS_DIR}/{self.MODEL_FILE_PREFIX}-{model_id}{model_file_extension}")

        return FsUtil.delete_file(path)
