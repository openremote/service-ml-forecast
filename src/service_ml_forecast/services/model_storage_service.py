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
from typing import Union, Any, Type
from darts.models.forecasting.forecasting_model import ForecastingModel

from service_ml_forecast.common.exceptions import ResourceNotFoundError
from service_ml_forecast.common.fs_util import FsUtil
from service_ml_forecast.config import DIRS

logger = logging.getLogger(__name__)


class ModelStorageService:
    """Manages the persistence of models."""

    MODEL_FILE_PREFIX = "model"
    DEFAULT_MODEL_FILE_EXTENSION = "pkl"  # Changed default to pkl for Darts models

    def save(self, model: ForecastingModel, model_id: UUID) -> None:
        """Save a Darts model using its native save method.
        
        Args:
            model: The Darts model to save.
            model_id: The ID of the model.
        """
        path = self._get_model_file_path(model_id, self.DEFAULT_MODEL_FILE_EXTENSION)
        
        # Ensure the directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use Darts native save method
        model.save(path)
        logger.info(f"Saved Darts model to {path} -- {model_id}")

    def load(self, model_class: Type[ForecastingModel], model_id: UUID) -> ForecastingModel:
        """Load a Darts model using its native load method.
        
        Args:
            model_class: The Darts model class (e.g., DartsProphet).
            model_id: The ID of the model.
            
        Returns:
            The loaded Darts model.
            
        Raises:
            ResourceNotFoundError: Model file was not found.
        """
        path = self._get_model_file_path(model_id, self.DEFAULT_MODEL_FILE_EXTENSION)
        
        if not path.exists():
            logger.error(f"Cannot get model file: {model_id} - does not exist")
            raise ResourceNotFoundError(f"Cannot get model file: {model_id} - does not exist")
        
        # Use Darts native load method
        model = model_class.load(path)
        logger.info(f"Loaded Darts model from {path} -- {model_id}")
        return model

    def delete(self, model_id: UUID) -> None:
        """Delete a Darts model file.

        Args:
            model_id: The ID of the model.

        Raises:
            ResourceNotFoundError: Model file was not found.
        """
        path = self._get_model_file_path(model_id, self.DEFAULT_MODEL_FILE_EXTENSION)

        try:
            path.unlink()
            logger.info(f"Deleted model file: {path}")
        except FileNotFoundError as e:
            logger.error(f"Cannot delete model file: {model_id} - does not exist: {e}")
            raise ResourceNotFoundError(f"Cannot delete model file: {model_id} - does not exist") from e

    def _get_model_file_path(self, model_id: UUID, model_file_extension: str) -> Path:
        return Path(f"{DIRS.ML_MODELS_DATA_DIR}/{self.MODEL_FILE_PREFIX}-{model_id}.{model_file_extension}")
