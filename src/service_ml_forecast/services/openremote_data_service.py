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

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.models.feature_data_wrappers import FeatureDatapoints, ForecastFeatureSet, TrainingFeatureSet
from service_ml_forecast.models.model_config import ModelConfig

logger = logging.getLogger(__name__)


class OpenRemoteDataService:
    """Service for interacting with the OpenRemote Manager API.

    Provides a wrapper around the OpenRemoteClient to provide a more convenient interface for the ML Forecast service.
    """

    def __init__(self, client: OpenRemoteClient):
        self.client = client

    def write_predicted_datapoints(self, config: ModelConfig, asset_datapoints: list[AssetDatapoint]) -> bool:
        """Write the predicted datapoints to OpenRemote.

        Args:
            config: The model configuration
            asset_datapoints: The predicted datapoints

        Returns:
            True if the datapoints were written successfully, False otherwise.
        """
        return self.client.write_predicted_datapoints(
            config.target.asset_id,
            config.target.attribute_name,
            asset_datapoints,
        )

    def get_training_feature_set(self, config: ModelConfig) -> TrainingFeatureSet | None:
        """Get the training feature set for a given model configuration.

        Args:
            config: The model configuration

        Returns:
            The training feature set or None if the training feature set could not be retrieved.
        """
        target_feature_datapoints: FeatureDatapoints

        # Retrieve target feature datapoints from OpenRemote
        datapoints = self.client.retrieve_historical_datapoints(
            config.target.asset_id,
            config.target.attribute_name,
            config.target.cutoff_timestamp,
            TimeUtil.get_timestamp_ms(),
        )

        if datapoints is None:
            logger.error(
                f"Failed to retrieve target datapoints for {config.target.asset_id} "
                f"{config.target.attribute_name} - skipping"
            )
            return None

        target_feature_datapoints = FeatureDatapoints(
            attribute_name=config.target.attribute_name,
            datapoints=datapoints,
        )

        regressors: list[FeatureDatapoints] = []

        # Retrieve regressor historical feature datapoints if configured
        if config.regressors is not None:
            for regressor in config.regressors:
                regressor_datapoints = self.client.retrieve_historical_datapoints(
                    regressor.asset_id,
                    regressor.attribute_name,
                    regressor.cutoff_timestamp,
                    TimeUtil.get_timestamp_ms(),
                )

                if regressor_datapoints is None:
                    logger.error(
                        f"Failed to retrieve regressor datapoints for {regressor.asset_id} "
                        f"{regressor.attribute_name} - skipping"
                    )
                    continue

                regressors.append(
                    FeatureDatapoints(
                        attribute_name=regressor.attribute_name,
                        datapoints=regressor_datapoints,
                    ),
                )

        training_feature_set = TrainingFeatureSet(
            target=target_feature_datapoints,
            regressors=regressors if regressors else None,
        )

        return training_feature_set

    def get_forecast_feature_set(self, config: ModelConfig) -> ForecastFeatureSet | None:
        """Get the forecast feature set for a given model configuration.

        Args:
            config: The model configuration

        Returns:
            The forecast feature set or None if the forecast feature set could not be retrieved.
        """
        regressors: list[FeatureDatapoints] = []

        # Retrieve regressor predicted feature datapoints if configured
        if config.regressors is not None:
            for regressor in config.regressors:
                regressor_datapoints = self.client.retrieve_predicted_datapoints(
                    regressor.asset_id,
                    regressor.attribute_name,
                    regressor.cutoff_timestamp,
                    TimeUtil.pd_future_timestamp(config.forecast_periods, config.forecast_frequency),
                )

                if regressor_datapoints is None:
                    logger.error(
                        f"No predicted datapoints found for {regressor.asset_id} {regressor.attribute_name} - skipping"
                    )
                    continue

                regressors.append(
                    FeatureDatapoints(
                        attribute_name=regressor.attribute_name,
                        datapoints=regressor_datapoints,
                    ),
                )

        forecast_feature_set = ForecastFeatureSet(
            regressors=regressors,
        )

        return forecast_feature_set
