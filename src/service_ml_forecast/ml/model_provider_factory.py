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
from service_ml_forecast.ml.xgboost_model_provider import XGBoostModelProvider
from service_ml_forecast.models.model_config import AssetDatapointFeature, ModelConfig
from service_ml_forecast.models.model_type import ModelTypeEnum


def get_all_covariates(config: ModelConfig) -> list[AssetDatapointFeature]:
    """Extract all covariates from any model configuration.

    Args:
        config: The model configuration (Prophet or XGBoost).

    Returns:
        List of all covariate features from the model configuration.
    """
    all_covariates: list[AssetDatapointFeature] = []

    # Prophet model uses 'regressors'
    if hasattr(config, "regressors") and config.regressors is not None:
        all_covariates.extend(config.regressors)

    # XGBoost model uses 'past_covariates' and 'future_covariates'
    if hasattr(config, "past_covariates") and config.past_covariates is not None:
        all_covariates.extend(config.past_covariates)
    if hasattr(config, "future_covariates") and config.future_covariates is not None:
        all_covariates.extend(config.future_covariates)

    return all_covariates


class ModelProviderFactory:
    """Factory for creating model providers based on the provided model config."""

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
        elif config.type == ModelTypeEnum.XGBOOST:
            try:
                return cast("ModelProvider[Any]", XGBoostModelProvider(config=config))
            except Exception as e:
                raise ValueError(
                    f"Failed to create XGBoost model provider for config {config.id}. "
                    f"Error: {e!s}. Config details: {config.model_dump_json()}"
                ) from e

        raise ValueError(f"Unsupported model type: {config.type}. Supported types: {[t.value for t in ModelTypeEnum]}")
