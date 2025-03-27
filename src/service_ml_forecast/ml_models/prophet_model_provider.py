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
from service_ml_forecast.ml_models.model_provider import ModelProvider
from service_ml_forecast.ml_models.model_util import (
    ForecastFeatureSet,
    ForecastResult,
    TrainingFeatureSet,
    load_model,
    save_model,
)
from service_ml_forecast.schemas.model_config import ProphetModelConfig

logger = logging.getLogger(__name__)


def _convert_prophet_forecast_to_datapoints(dataframe: pd.DataFrame) -> list[AssetDatapoint]:
    datapoints = []
    # Convert ds datetime to milliseconds since epoch
    for _, row in dataframe.iterrows():
        datapoints.append(AssetDatapoint(x=int(row["ds"].timestamp() * 1000), y=row["yhat"]))

    return datapoints


def _convert_datapoints_to_dataframe(datapoints: list[AssetDatapoint], rename_y: str | None = None) -> pd.DataFrame:
    dataframe = pd.DataFrame([{"ds": point.x, "y": point.y} for point in datapoints])
    dataframe["ds"] = pd.to_datetime(dataframe["ds"], unit="ms")
    if rename_y is not None:
        dataframe = dataframe.rename(columns={"y": rename_y})

    # Sort dataframe by timestamp
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
                regressor.datapoints, rename_y=regressor.attribute_name
            )

            # Interpolate the regressor values to the target data point timestamps
            dataframe = pd.merge_asof(
                dataframe,
                regressor_dataframe[["ds", regressor.attribute_name]],
                on="ds",
                direction="nearest",
            )

    return dataframe


class ProphetModelProvider(ModelProvider[Prophet]):
    """Prophet model provider."""

    def __init__(
        self,
        config: ProphetModelConfig,
    ) -> None:
        self.config = config

    def __load_model(self) -> Prophet | None:
        model_json = load_model(f"{self.config.id}.json")

        if model_json is None:
            logger.error(f"Failed to load model -- {self.config.id}")
            return None

        model: Prophet = model_from_json(model_json)

        return model

    def train_model(self, training_dataset: TrainingFeatureSet) -> Prophet:
        if training_dataset.target.datapoints is None or len(training_dataset.target.datapoints) == 0:
            logger.error("No target data provided, cannot train Prophet model")
            return None

        dataframe = _prepare_training_dataframe(training_dataset)
        if dataframe is None:
            logger.error("Failed to obtain valid dataframe for training the Prophet model")
            return None

        # Configure the model
        model = Prophet()
        model.weekly_seasonality = self.config.weekly_seasonality
        model.yearly_seasonality = self.config.yearly_seasonality
        model.daily_seasonality = self.config.daily_seasonality

        # Add regressors to the model if provided
        if training_dataset.regressors is not None:
            logger.info(f"Adding {len(training_dataset.regressors)} regressor(s) -- {self.config.id}")
            for regressor in training_dataset.regressors:
                model.add_regressor(regressor.attribute_name)

        # Train the model
        model.fit(dataframe)

        return model

    def save_model(self, model: Prophet) -> bool:
        if not save_model(model_to_json(model), f"{self.config.id}.json"):
            logger.error(f"Failed to save trained model -- {self.config.id}")
            return False

        logger.info(f"Saved trained model -- {self.config.id}")
        return True

    def generate_forecast(self, forecast_feature_set: ForecastFeatureSet | None = None) -> ForecastResult | None:
        model = self.__load_model()
        if model is None:
            logger.error(f"Failed to load model -- {self.config.id}")
            return None

        future = model.make_future_dataframe(periods=96, freq="30min")

        # Add future regressor values to the future dataframe if provided
        if forecast_feature_set is not None:
            logger.info(f"Requested forecast is using regressor(s) -- {self.config.id}")
            for regressor in forecast_feature_set.regressors:
                regressor_dataframe = _convert_datapoints_to_dataframe(
                    regressor.datapoints, rename_y=regressor.attribute_name
                )

                # Interpolate the regressor values to the future data point timestamps
                future = pd.merge_asof(
                    future,
                    regressor_dataframe[["ds", regressor.attribute_name]],
                    on="ds",
                    direction="nearest",
                )

        forecast = model.predict(future)

        # Remove historical data from the forecast dataframe - prophet returns the entire history
        last_train_date = model.history["ds"].max()
        forecast_future = forecast[forecast["ds"] > last_train_date]

        # noinspection PyTypeChecker
        datapoints = _convert_prophet_forecast_to_datapoints(forecast_future)

        logger.info(f"Generated {len(datapoints)} forecasted datapoints")

        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=datapoints,
        )
