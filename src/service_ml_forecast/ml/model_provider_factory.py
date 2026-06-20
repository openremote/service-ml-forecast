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

from typing import Any, cast

from service_ml_forecast.ml.model_provider import ModelProvider
from service_ml_forecast.ml.prophet_model_provider import ProphetModelProvider
from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.models.model_type import ModelTypeEnum


class ModelProviderFactory:
    """Factory for creating ML model providers based on the provided model config."""

    @staticmethod
    def create_provider(
        config: ModelConfig,
    ) -> ModelProvider[Any]:
        """Create a model provider instance based on the model config type.

        Args:
            config: The model configuration.

        Returns:
            The model provider instance.
        """
        if config.type == ModelTypeEnum.PROPHET:
            try:
                return cast("ModelProvider[Any]", ProphetModelProvider(config=config))
            except Exception as e:
                raise ValueError(
                    f"Failed to create Prophet model provider for config {config.id}. "
                    f"Error: {e!s}. Config details: {config.model_dump_json()}"
                ) from e

        if config.type == ModelTypeEnum.ITRANSFORMER:
            try:
                from service_ml_forecast.ml.itransformer_model_provider import ITransformerModelProvider  # noqa: PLC0415
                return cast("ModelProvider[Any]", ITransformerModelProvider(config=config))
            except ImportError as e:
                raise ImportError(
                    "torch is required for iTransformer. Install the 'itransformer' extra: "
                    "pip install service-ml-forecast[itransformer]"
                ) from e
            except Exception as e:
                raise ValueError(
                    f"Failed to create iTransformer model provider for config {config.id}. "
                    f"Error: {e!s}. Config details: {config.model_dump_json()}"
                ) from e

        if config.type == ModelTypeEnum.NL_ENERGY_FORECASTER:
            try:
                from service_ml_forecast.ml.nl_energy_forecaster_model_provider import NLEnergyForecasterModelProvider  # noqa: PLC0415
                return cast("ModelProvider[Any]", NLEnergyForecasterModelProvider(config=config))
            except ImportError as e:
                raise ImportError(
                    "torch, huggingface_hub, and scikit-learn are required for NL energy forecaster. "
                    "Install the 'nl-energy-forecaster' extra: "
                    "pip install service-ml-forecast[nl-energy-forecaster]"
                ) from e
            except Exception as e:
                raise ValueError(
                    f"Failed to create NL energy forecaster provider for config {config.id}. "
                    f"Error: {e!s}. Config details: {config.model_dump_json()}"
                ) from e

        raise ValueError(f"Unsupported model type: {config.type}. Supported types: {[t.value for t in ModelTypeEnum]}")
