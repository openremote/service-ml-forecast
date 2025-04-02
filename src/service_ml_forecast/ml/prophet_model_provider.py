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

import logging

import pandas as pd
from prophet import Prophet
from prophet.serialize import model_from_json, model_to_json

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.ml.ml_model_provider import MLModelProvider
from service_ml_forecast.models.ml_data_wrappers import ForecastFeatureSet, ForecastResult, TrainingFeatureSet
from service_ml_forecast.models.ml_model_config import ProphetModelConfig
from service_ml_forecast.services.ml_model_storage_service import MLModelStorageService
from service_ml_forecast.util.time_util import TimeUtil

logger = logging.getLogger(__name__)


class ProphetModelProvider(MLModelProvider[Prophet]):
    """Prophet model provider."""

    def __init__(
        self,
        config: ProphetModelConfig,
    ) -> None:
        self.config = config
        self.model_storage_service = MLModelStorageService()

    def train_model(self, training_dataset: TrainingFeatureSet) -> Prophet | None:
        if training_dataset.target.datapoints is None or len(training_dataset.target.datapoints) == 0:
            logger.error("No target data provided, cannot train Prophet model")
            return None

        dataframe = _prepare_training_dataframe(training_dataset)
        if dataframe is None:
            logger.error("Failed to obtain valid dataframe for training the Prophet model")
            return None

        # Construct the model
        model = Prophet()

        # Apply model configuration
        model.weekly_seasonality = self.config.weekly_seasonality
        model.yearly_seasonality = self.config.yearly_seasonality
        model.daily_seasonality = self.config.daily_seasonality
        model.seasonality_mode = self.config.seasonality_mode
        model.changepoint_prior_scale = self.config.changepoint_prior_scale
        model.changepoint_range = self.config.changepoint_range

        # Add regressors to the model if provided
        if training_dataset.regressors is not None:
            logger.info(f"Adding {len(training_dataset.regressors)} regressor(s) -- {self.config.id}")
            for regressor in training_dataset.regressors:
                model.add_regressor(regressor.attribute_name)

        # Train the model
        model.fit(dataframe)

        return model

    def load_model(self, model_id: str) -> Prophet | None:
        model_json = self.model_storage_service.load(model_id, ".json")
        if model_json is None:
            logger.error(f"Failed to load model -- {model_id}")
            return None

        return model_from_json(model_json)

    def save_model(self, model: Prophet) -> bool:
        try:
            model_json = model_to_json(model)
            if not self.model_storage_service.save(model_json, self.config.id, ".json"):
                logger.error(f"Failed to save trained model -- {self.config.id}")
                return False

            logger.info(f"Saved trained model -- {self.config.id}")
            return True
        except Exception as e:
            logger.exception(f"Failed to save trained model -- {self.config.id}: {e}")
            return False

    def generate_forecast(self, forecast_feature_set: ForecastFeatureSet | None = None) -> ForecastResult | None:
        model = self.load_model(self.config.id)
        if model is None:
            logger.error(f"Failed to load model -- {self.config.id}")
            return None

        future = model.make_future_dataframe(
            periods=self.config.forecast_periods,
            freq=self.config.forecast_frequency,
            include_history=False,
        )

        # round the future timestamps to the forecast frequency
        future["ds"] = future["ds"].dt.round(self.config.forecast_frequency)

        # Add future regressor values to the future dataframe if provided
        if forecast_feature_set is not None:
            logger.info(f"Requested forecast is using regressor(s) -- {self.config.id}")
            for regressor in forecast_feature_set.regressors:
                regressor_dataframe = _convert_datapoints_to_dataframe(
                    regressor.datapoints,
                    rename_y=regressor.attribute_name,
                )

                # Interpolate the regressor values to the future data point timestamps
                future = pd.merge_asof(
                    future,
                    regressor_dataframe[["ds", regressor.attribute_name]],
                    on="ds",
                    direction="nearest",
                )

        forecast = model.predict(future)

        # noinspection PyTypeChecker
        datapoints = _convert_prophet_forecast_to_datapoints(forecast)

        if datapoints is None or len(datapoints) == 0:
            logger.error(f"Failed to generate forecast -- {self.config.id}")
            return None

        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=datapoints,
        )


def _convert_prophet_forecast_to_datapoints(dataframe: pd.DataFrame) -> list[AssetDatapoint]:
    datapoints = []
    for _, row in dataframe.iterrows():
        # Convert the `ds` timestamp to milliseconds since that is what OpenRemote expects
        millis = TimeUtil.sec_to_ms(int(row["ds"].timestamp()))
        datapoints.append(AssetDatapoint(x=millis, y=row["yhat"]))

    return datapoints


def _convert_datapoints_to_dataframe(datapoints: list[AssetDatapoint], rename_y: str | None = None) -> pd.DataFrame:
    dataframe = pd.DataFrame([{"ds": point.x, "y": point.y} for point in datapoints])

    # Convert the millis timestamp to seconds for Prophet
    dataframe["ds"] = pd.to_datetime(dataframe["ds"], unit="ms")
    if rename_y is not None:
        dataframe = dataframe.rename(columns={"y": rename_y})

    # Sort the dataframe by timestamp
    dataframe = dataframe.sort_values("ds")

    return dataframe


def _prepare_training_dataframe(training_dataset: TrainingFeatureSet) -> pd.DataFrame | None:
    target = training_dataset.target
    regressors = training_dataset.regressors

    # Convert the datapoints to a dataframe - prophet expects the target data to be 'ds' and 'y' structure
    dataframe = _convert_datapoints_to_dataframe(target.datapoints)

    # Add regressors if they are provided
    if regressors is not None:
        for regressor in regressors:
            regressor_dataframe = _convert_datapoints_to_dataframe(
                regressor.datapoints,
                rename_y=regressor.attribute_name,
            )

            # Interpolate the regressor values to the target data point timestamps
            dataframe = pd.merge_asof(
                dataframe,
                regressor_dataframe[["ds", regressor.attribute_name]],
                on="ds",
                direction="nearest",
            )

    return dataframe
