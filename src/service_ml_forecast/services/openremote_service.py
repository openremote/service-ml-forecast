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
import math

from openremote_client import AssetDatapoint, BasicAsset, OpenRemoteClient, Realm

from service_ml_forecast.common.datapoint_time import require_unambiguous_window
from service_ml_forecast.common.exceptions import ResourceValidationError
from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.config import ENV
from service_ml_forecast.ml.model_provider_factory import get_all_covariates
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, ForecastDataSet, TrainingDataSet
from service_ml_forecast.models.model_config import (
    AssetDatapointFeature,
    FutureAssetDatapointFeature,
    ModelConfig,
    PastAssetDatapointFeature,
)

logger = logging.getLogger(__name__)


class OpenRemoteService:
    """Service for interacting with the OpenRemote Manager API."""

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
        if not asset_datapoints:
            raise ResourceValidationError("Cannot publish an empty forecast")
        first = min(point.x for point in asset_datapoints)
        last = max(point.x for point in asset_datapoints)
        require_unambiguous_window(first, last, ENV.ML_OR_DATAPOINT_TIMEZONE)
        if not self.client.assets.write_predicted_datapoints(
            config.target.asset_id,
            config.target.attribute_name,
            asset_datapoints,
        ):
            return False
        stored = self.client.assets.get_predicted_datapoints(
            config.target.asset_id, config.target.attribute_name, first, last
        )
        if stored is None:
            raise ResourceValidationError("Forecast write could not be verified by readback")
        self._check_returned_bounds(stored, first, last)
        actual: dict[int, float | None] = {}
        for point in stored:
            if point.x in actual and actual[point.x] != point.y:
                raise ResourceValidationError("Forecast readback contains conflicting duplicate timestamps")
            actual[point.x] = point.y
        for point in asset_datapoints:
            value = actual.get(point.x)
            if value is None or point.y is None or not math.isclose(value, point.y, rel_tol=1e-12, abs_tol=1e-9):
                raise ResourceValidationError("Forecast write readback has missing or changed datapoints")
        return True

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

        covariates: list[AssetFeatureDatapoints] = []
        config_covariates: list[AssetDatapointFeature] = get_all_covariates(config)

        # Retrieve covariate historical feature datapoints if configured
        if config_covariates is not None:
            for covariate in config_covariates:
                covariate_datapoints: list[AssetDatapoint] | None
                # Get the start timestamp for the covariate historical data
                start_timestamp = TimeUtil.get_period_start_timestamp_ms(covariate.training_data_period)


                covariate_datapoints = self._get_historical_datapoints(
                    covariate.asset_id,
                    covariate.attribute_name,
                    start_timestamp,
                    end_timestamp,
                )

                if covariate_datapoints is None:
                    logger.warning(
                        f"Unable to retrieve covariate datapoints for {covariate.asset_id} "
                        f"{covariate.get_feature_name()} - skipping"
                    )
                    raise ValueError(
                        f"Unable to retrieve covariate datapoints for {covariate.asset_id} "
                        f"{covariate.get_feature_name()}"
                    )

                covariates.append(
                    AssetFeatureDatapoints(
                        feature_name=covariate.get_feature_name(),
                        datapoints=covariate_datapoints,
                    ),
                )

        training_dataset = TrainingDataSet(
            target=target_feature_datapoints,
            covariates=covariates if covariates else None,
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
        require_unambiguous_window(from_timestamp, to_timestamp, ENV.ML_OR_DATAPOINT_TIMEZONE)
        for exclusion in ENV.ML_OR_HISTORY_EXCLUSIONS:
            if (
                asset_id == exclusion.asset_id
                and attribute_name == exclusion.attribute_name
                and from_timestamp <= exclusion.last_ms
                and to_timestamp >= exclusion.first_ms
            ):
                raise ResourceValidationError(
                    f"Historical input overlaps excluded source history: {exclusion.reason} "
                    f"({exclusion.first_ms}..{exclusion.last_ms} UTC ms)"
                )
        months_diff = TimeUtil.months_between_timestamps(from_timestamp, to_timestamp)

        # Single requests for sub-monthly periods
        if months_diff <= 1:
            points = self.client.assets.get_historical_datapoints(
                asset_id, attribute_name, from_timestamp, to_timestamp
            )
            self._check_returned_bounds(points, from_timestamp, to_timestamp)
            return points
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

                chunk_datapoints = self.client.assets.get_historical_datapoints(
                    asset_id, attribute_name, current_from, current_to
                )

                if chunk_datapoints is None:
                    logger.error(
                        f"Failed to retrieve historical datapoints for {asset_id} {attribute_name} "
                        f"for chunk ending at {current_to}"
                    )
                    return None

                self._check_returned_bounds(chunk_datapoints, current_from, current_to)
                all_datapoints.extend(chunk_datapoints)

                # Move to the next chunk
                current_from = current_to

            return all_datapoints

    @staticmethod
    def _check_returned_bounds(points: list[AssetDatapoint] | None, first: int, last: int) -> None:
        if points is not None and any(not first <= point.x <= last for point in points):
            raise ResourceValidationError("Manager returned datapoints outside the requested UTC window")

    def _get_predicted_datapoints(
        self, asset_id: str, attribute_name: str, first: int, last: int
    ) -> list[AssetDatapoint] | None:
        require_unambiguous_window(first, last, ENV.ML_OR_DATAPOINT_TIMEZONE)
        points = self.client.assets.get_predicted_datapoints(asset_id, attribute_name, first, last)
        self._check_returned_bounds(points, first, last)
        return points

    def get_forecast_dataset(self, config: ModelConfig) -> ForecastDataSet | None:
        """Get the forecast dataset for a given model configuration.

        Args:
            config: The model configuration

        Returns:
            The forecast dataset or None if the forecast dataset could not be retrieved.
        """
        covariates: list[AssetFeatureDatapoints] = []

        config_covariates: list[AssetDatapointFeature] = get_all_covariates(config)

        config_past_covariates: list[PastAssetDatapointFeature] = [
            x for x in config_covariates if isinstance(x, PastAssetDatapointFeature)
        ]
        config_future_covariates: list[FutureAssetDatapointFeature] = [
            x for x in config_covariates if isinstance(x, FutureAssetDatapointFeature)
        ]
        future_lags = getattr(config, "lags_future_covariates", None)
        extra_future_steps = max([0, *future_lags]) if isinstance(future_lags, list) else 0

        # Retrieve covariate predicted/future feature datapoints if configured
        if config_future_covariates is not None:
            for future_covariate in config_future_covariates:
                # Get the start timestamp for the regressor
                start_timestamp = TimeUtil.get_period_start_timestamp_ms(future_covariate.training_data_period)

                future_covariate_datapoints = self._get_predicted_datapoints(
                    future_covariate.asset_id,
                    future_covariate.attribute_name,
                    start_timestamp,
                    TimeUtil.pd_future_timestamp(
                        config.forecast_periods + extra_future_steps, config.forecast_frequency
                    ),
                )

                if future_covariate_datapoints is None:
                    logger.warning(
                        f"Unable to retrieve predicted datapoints for {future_covariate.asset_id} "
                        f"{future_covariate.get_feature_name()} - skipping"
                    )
                    return None  # Return immediately, forecast will fail without future covariate data

                covariates.append(
                    AssetFeatureDatapoints(
                        feature_name=future_covariate.get_feature_name(),
                        datapoints=future_covariate_datapoints,
                    ),
                )

        # Retrieve past covariate historical feature datapoints if configured
        if config_past_covariates is not None:
            for past_covariate in config_past_covariates:
                # Get the start timestamp for the past covariate
                start_timestamp = TimeUtil.get_period_start_timestamp_ms(past_covariate.training_data_period)

                past_covariate_datapoints = self._get_historical_datapoints(
                    past_covariate.asset_id,
                    past_covariate.attribute_name,
                    start_timestamp,
                    TimeUtil.get_timestamp_ms(),
                )

                if past_covariate_datapoints is None:
                    logger.warning(
                        f"Unable to retrieve historical datapoints for {past_covariate.asset_id} "
                        f"{past_covariate.get_feature_name()} - skipping"
                    )
                    return None  # Return immediately, forecast will fail without past covariate data

                covariates.append(
                    AssetFeatureDatapoints(
                        feature_name=past_covariate.get_feature_name(),
                        datapoints=past_covariate_datapoints,
                    ),
                )

        forecast_dataset = ForecastDataSet(
            covariates=covariates,
        )

        return forecast_dataset

    def get_assets_by_ids(self, realm: str, asset_ids: list[str]) -> list[BasicAsset]:
        """Get assets by a comma-separated list of Asset IDs.

        Returns:
            A list of all assets from OpenRemote.
        """
        assets = self.client.assets.get_by_ids(asset_ids, realm)
        if assets is None:
            logger.warning(f"Unable to retrieve assets by ids for realm {realm}")
            return []

        return assets

    def get_accessible_realms(self) -> list[Realm] | None:
        """Get all accessible realms from OpenRemote for the current authenticated user.

        Returns:
            A list of all accessible realms from OpenRemote.
        """
        return self.client.realms.get_accessible()
