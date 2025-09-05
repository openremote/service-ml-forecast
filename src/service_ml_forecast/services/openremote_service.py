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

from service_ml_forecast.clients.openremote.models import AssetDatapoint, BasicAsset, Realm
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, ForecastDataSet, TrainingDataSet
from service_ml_forecast.models.model_config import ModelConfig

logger = logging.getLogger(__name__)


class OpenRemoteService:
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

    def get_training_dataset(self, config: ModelConfig) -> TrainingDataSet | None:
        """Get the training dataset for a given model configuration.

        Args:
            config: The model configuration

        Returns:
            The training feature set or None if the training feature set could not be retrieved.
        """
        target_feature_datapoints: AssetFeatureDatapoints

        # Get the start timestamp for the target feature
        start_timestamp = TimeUtil.get_period_start_timestamp_ms(config.target.training_data_period)
        end_timestamp = TimeUtil.get_timestamp_ms()

        # Retrieve target feature datapoints from OpenRemote with chunking if needed
        datapoints = self._get_historical_datapoints(
            config.target.asset_id,
            config.target.attribute_name,
            start_timestamp,
            end_timestamp,
        )

        if datapoints is None:
            logger.warning(
                f"Unable to retrieve target datapoints for {config.target.asset_id} "
                f"{config.target.attribute_name} - skipping"
            )
            return None

        target_feature_datapoints = AssetFeatureDatapoints(
            feature_name=config.target.attribute_name,
            datapoints=datapoints,
        )

        regressors: list[AssetFeatureDatapoints] = []

        # Retrieve regressor historical feature datapoints if configured
        if config.regressors is not None:
            for regressor in config.regressors:
                # Get the start timestamp for the regressor historical data
                start_timestamp = TimeUtil.get_period_start_timestamp_ms(regressor.training_data_period)

                regressor_datapoints = self._get_historical_datapoints(
                    regressor.asset_id,
                    regressor.attribute_name,
                    start_timestamp,
                    end_timestamp,
                )

                if regressor_datapoints is None:
                    logger.warning(
                        f"Unable to retrieve regressor datapoints for {regressor.asset_id} "
                        f"{regressor.get_feature_name()} - skipping"
                    )
                    raise ValueError(
                        f"Unable to retrieve regressor datapoints for {regressor.asset_id} "
                        f"{regressor.get_feature_name()}"
                    )

                regressors.append(
                    AssetFeatureDatapoints(
                        feature_name=regressor.get_feature_name(),
                        datapoints=regressor_datapoints,
                    ),
                )

        training_dataset = TrainingDataSet(
            target=target_feature_datapoints,
            regressors=regressors if regressors else None,
        )

        return training_dataset

    def _get_historical_datapoints(
        self, asset_id: str, attribute_name: str, from_timestamp: int, to_timestamp: int
    ) -> list[AssetDatapoint] | None:
        """Wrapper get_historical_datapoints to split up requests into monthly chunks.

        Args:
            asset_id: The ID of the asset.
            attribute_name: The name of the attribute.
            from_timestamp: Epoch timestamp in milliseconds.
            to_timestamp: Epoch timestamp in milliseconds.

        Returns:
            List of historical datapoints or None if failed.
        """
        months_diff = TimeUtil.months_between_timestamps(from_timestamp, to_timestamp)

        # Single requests for sub-monthly periods
        if months_diff <= 1:
            return self.client.get_historical_datapoints(asset_id, attribute_name, from_timestamp, to_timestamp)
        # Split into monthly chunks if more than 1 month to avoid hitting datapoint limits on the OpenRemote side
        else:
            all_datapoints = []
            current_from = from_timestamp

            logger.info(
                f"Chunking datapoint retrieval into {months_diff} monthly chunks for {asset_id} {attribute_name}"
            )

            # Continue until we've processed a chunk that ends at or after to_timestamp
            while current_from < to_timestamp:
                # Calculate the end timestamp for this chunk (1 month from current_from)
                current_to = TimeUtil.add_months_to_timestamp(current_from, 1)

                # Don't exceed the original to_timestamp
                current_to = min(current_to, to_timestamp)

                chunk_datapoints = self.client.get_historical_datapoints(
                    asset_id, attribute_name, current_from, current_to
                )

                if chunk_datapoints is None:
                    logger.error(
                        f"Failed to retrieve historical datapoints for {asset_id} {attribute_name} "
                        f"for chunk ending at {current_to}"
                    )
                    return None

                all_datapoints.extend(chunk_datapoints)

                # Move to the next chunk
                current_from = current_to

            return all_datapoints

    def get_forecast_dataset(self, config: ModelConfig) -> ForecastDataSet | None:
        """Get the forecast dataset for a given model configuration.

        Args:
            config: The model configuration

        Returns:
            The forecast dataset or None if the forecast dataset could not be retrieved.
        """
        regressors: list[AssetFeatureDatapoints] = []

        # Retrieve regressor predicted feature datapoints if configured
        if config.regressors is not None:
            for regressor in config.regressors:
                # Get the start timestamp for the regressor
                start_timestamp = TimeUtil.get_period_start_timestamp_ms(regressor.training_data_period)

                regressor_datapoints = self.client.get_predicted_datapoints(
                    regressor.asset_id,
                    regressor.attribute_name,
                    start_timestamp,
                    TimeUtil.pd_future_timestamp(config.forecast_periods, config.forecast_frequency),
                )

                if regressor_datapoints is None:
                    logger.warning(
                        f"Unable to retrieve predicted datapoints for {regressor.asset_id} "
                        f"{regressor.get_feature_name()} - skipping"
                    )
                    return None  # Return immediately, forecast will fail without regressor future data

                regressors.append(
                    AssetFeatureDatapoints(
                        feature_name=regressor.get_feature_name(),
                        datapoints=regressor_datapoints,
                    ),
                )

        forecast_dataset = ForecastDataSet(
            regressors=regressors,
        )

        return forecast_dataset

    def get_assets_by_ids(self, realm: str, asset_ids: list[str]) -> list[BasicAsset]:
        """Get assets by a comma-separated list of Asset IDs.

        Returns:
            A list of all assets from OpenRemote.
        """
        assets = self.client.get_assets_by_ids(asset_ids, realm)
        if assets is None:
            logger.warning(f"Unable to retrieve assets by ids for realm {realm}")
            return []

        return assets

    def get_accessible_realms(self) -> list[Realm] | None:
        """Get all accessible realms from OpenRemote for the current authenticated user.

        Returns:
            A list of all realms from OpenRemote.
        """
        return self.client.get_accessible_realms()
