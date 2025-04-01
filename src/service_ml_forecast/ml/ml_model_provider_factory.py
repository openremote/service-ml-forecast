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

from typing import Any, cast

from service_ml_forecast.ml.ml_model_provider import MLModelProvider
from service_ml_forecast.ml.prophet_model_provider import ProphetModelProvider
from service_ml_forecast.models.ml_model_config import MLModelConfig
from service_ml_forecast.models.ml_model_type import MLModelTypeEnum


class MLModelProviderFactory:
    """Factory for creating ML model providers based on the provided model config."""

    @staticmethod
    def create_provider(
        config: MLModelConfig,
    ) -> MLModelProvider[Any]:
        """Create a model provider instance based on the model config type.

        Args:
            config: The model configuration.

        Returns:
            The model provider instance.
        """
        if config.type == MLModelTypeEnum.PROPHET:
            try:
                return cast("MLModelProvider[Any]", ProphetModelProvider(config=config))
            except Exception as e:
                raise ValueError(f"Failed to convert config to ProphetMLConfig: {e}") from e

        raise ValueError(f"Unsupported model type: {config.type}")
