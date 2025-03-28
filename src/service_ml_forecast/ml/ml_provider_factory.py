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

from typing import Any

from service_ml_forecast.ml.ml_provider import MLModelProvider
from service_ml_forecast.ml.prophet_ml_provider import ProphetMLProvider
from service_ml_forecast.models.ml_config import MLConfig, MLModelType, ProphetMLConfig


class MLProviderFactory:
    """Factory for creating ML model providers based on the provided model config."""

    @staticmethod
    def create_provider(
        config: MLConfig,
    ) -> MLModelProvider[Any]:
        """Create a model provider instance based on the model config type.

        Args:
            config: The model configuration.
        """
        if config.type == MLModelType.PROPHET:
            try:
                if not isinstance(config, ProphetMLConfig):
                    prophet_config = ProphetMLConfig(**config.model_dump())
                else:
                    prophet_config = config
                return ProphetMLProvider(config=prophet_config)
            except Exception as e:
                raise ValueError(f"Failed to convert config to ProphetMLConfig: {e}")

        raise ValueError(f"Unsupported model type: {config.type}")
