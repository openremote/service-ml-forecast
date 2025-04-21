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

from service_ml_forecast.clients.openremote.models import Asset, AssetDatapoint, RealmConfig
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

        # Retrieve target feature datapoints from OpenRemote
        datapoints = self.client.retrieve_historical_datapoints(
            config.target.asset_id,
            config.target.attribute_name,
            config.target.cutoff_timestamp,
            TimeUtil.get_timestamp_ms(),
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
                regressor_datapoints = self.client.retrieve_historical_datapoints(
                    regressor.asset_id,
                    regressor.attribute_name,
                    regressor.cutoff_timestamp,
                    TimeUtil.get_timestamp_ms(),
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
                regressor_datapoints = self.client.retrieve_predicted_datapoints(
                    regressor.asset_id,
                    regressor.attribute_name,
                    regressor.cutoff_timestamp,
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

    def get_assets_with_historical_datapoints(self, realm: str) -> list[Asset]:
        """Get all assets from OpenRemote with historical datapoints.

        Returns:
            A list of all assets from OpenRemote with historical datapoints.
        """
        assets = self.client.retrieve_assets_with_historical_datapoints(realm)
        if assets is None:
            logger.warning(f"Unable to retrieve assets with storeDataPoints for realm {realm}")
            return []

        return assets

    def get_assets_by_ids(self, asset_ids: list[str], realm: str) -> list[Asset]:
        """Get all assets from OpenRemote.

        Returns:
            A list of all assets from OpenRemote.
        """
        logger.info(f"Retrieving assets by ids: {asset_ids} for realm {realm}")
        assets = self.client.retrieve_assets_by_ids(asset_ids, realm)
        if assets is None:
            logger.warning(f"Unable to retrieve assets by ids for realm {realm}")
            return []

        return assets

    def get_realm_config(self, realm: str) -> RealmConfig | None:
        """Get the realm configuration for a given realm.

        Returns:
            The realm configuration or None if the realm configuration could not be retrieved.
        """
        config = self.client.retrieve_manager_config()

        if config is None:
            logger.warning("Unable to retrieve manager config")
            return None

        if realm not in config.realms:
            logger.warning(f"Realm {realm} not found in manager config")
            return None

        return config.realms[realm]
