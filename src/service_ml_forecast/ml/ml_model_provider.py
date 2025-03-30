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

from typing import Protocol, TypeVar

from service_ml_forecast.models.ml_data_models import ForecastFeatureSet, ForecastResult, TrainingFeatureSet

# Define a generic type variable for the model
# Enables type checking for different model type implementations
MLModelType = TypeVar("MLModelType")


class MLModelProvider(Protocol[MLModelType]):
    """Base protocol for all ML models.

    This protocol defines the methods that all ML model providers must implement.
    """

    def train_model(self, training_dataset: TrainingFeatureSet) -> MLModelType:
        """Train the model on the training dataset.

        Args:
            training_dataset: The training dataset to train the model on.

        Returns:
            The trained model.
        """

    def generate_forecast(self, forecast_featureset: ForecastFeatureSet | None = None) -> ForecastResult | None:
        """Generate a forecast for the given forecast featureset.

        Args:
            forecast_featureset: The forecast featureset to generate a forecast for.

        Returns:
            The forecast result.
        """

    def save_model(self, model: MLModelType) -> bool:
        """Save the trained model via the model storage service.

        Args:
            model: The trained model to save.

        Returns:
            True if the model was saved successfully, False otherwise.
        """

    def load_model(self, model_config_id: str) -> MLModelType | None:
        """Load the trained model via the model storage service.

        Args:
            model_config_id: The ID of the model config to load the model for.

        Returns:
            The loaded model, or None if the model could not be loaded.
        """
