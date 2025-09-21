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
from uuid import UUID

import numpy as np
import pandas as pd
from openremote_client import AssetDatapoint
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from prophet.serialize import model_from_json, model_to_json
from sklearn.metrics import r2_score

from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml.evaluation_metrics import EvaluationMetrics
from service_ml_forecast.ml.model_provider import ModelProvider
from service_ml_forecast.models.feature_data_wrappers import ForecastDataSet, ForecastResult, TrainingDataSet
from service_ml_forecast.models.model_config import ProphetModelConfig
from service_ml_forecast.services.model_storage_service import ModelStorageService

logger = logging.getLogger(__name__)


MIN_DATAPOINTS_FOR_PROPHET = 2
MIN_RECOMMENDED_DATAPOINTS = 50
TIMESTAMP_COLUMN_NAME = "ds"
VALUE_COLUMN_NAME = "y"
FORECAST_COLUMN_NAME = "yhat"


class ProphetModelProvider(ModelProvider[Prophet]):
    """Prophet model provider."""

    def __init__(
        self,
        config: ProphetModelConfig,
    ) -> None:
        self.config = config
        self.model_storage_service = ModelStorageService()

    def train_model(self, training_dataset: TrainingDataSet) -> Prophet | None:
        if training_dataset.target.datapoints is None or len(training_dataset.target.datapoints) == 0:
            logger.error("No target data provided, cannot train Prophet model")
            return None

        logger.info(f"Training model -- {self.config.id} with {len(training_dataset.target.datapoints)} datapoints")

        # Add a warning if the dataset is very small
        min_required_datapoints = 50
        num_datapoints = len(training_dataset.target.datapoints)
        if num_datapoints < min_required_datapoints:
            logger.warning(
                f"Training dataset for model {self.config.id} has only {num_datapoints} datapoints "
                f"(minimum recommended: {min_required_datapoints}). The resulting model may be unreliable."
            )

        dataframe = _prepare_training_dataframe(training_dataset)

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
            logger.info(f"Training with {len(training_dataset.regressors)} regressor(s) -- {self.config.id}")
            for regressor in training_dataset.regressors:
                model.add_regressor(regressor.feature_name)

        # Train the model
        model.fit(dataframe)

        return model

    def load_model(self, model_id: UUID) -> Prophet:
        model_json = self.model_storage_service.get(model_id)
        return model_from_json(model_json)

    def save_model(self, model: Prophet) -> None:
        model_json = model_to_json(model)
        self.model_storage_service.save(model_json, self.config.id)
        logger.info(f"Saved trained model -- {self.config.id}")

    def generate_forecast(self, forecast_dataset: ForecastDataSet | None = None) -> ForecastResult:
        model = self.load_model(self.config.id)

        future = model.make_future_dataframe(
            periods=self.config.forecast_periods,
            freq=self.config.forecast_frequency,
            include_history=False,
        )

        # round the future timestamps to the forecast frequency
        future["ds"] = future["ds"].dt.round(self.config.forecast_frequency)

        if forecast_dataset is not None:
            logger.info(f"Forecasting with {len(forecast_dataset.regressors)} regressor(s) -- {self.config.id}")
            for regressor in forecast_dataset.regressors:
                regressor_dataframe = _convert_datapoints_to_dataframe(
                    regressor.datapoints,
                    rename_y=regressor.feature_name,
                )

                future = pd.merge_asof(
                    future,
                    regressor_dataframe[["ds", regressor.feature_name]],
                    on="ds",
                    direction="nearest",
                )

        forecast = model.predict(future)

        # noinspection PyTypeChecker
        datapoints = _convert_prophet_forecast_to_datapoints(forecast)

        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=datapoints,
        )

    def evaluate_model(self, model: Prophet) -> EvaluationMetrics | None:
        """Evaluate the model using Prophet's cross-validation (RMSE, MAE, MAPE, MdAPE, R²)."""

        try:
            horizon_delta = pd.Timedelta(self.config.forecast_frequency) * self.config.forecast_periods
            secs = int(horizon_delta.total_seconds())
            horizon_str = f"{secs} seconds"
        except Exception:
            logger.warning(f"Invalid forecast_frequency '{self.config.forecast_frequency}', using 30 days")
            horizon_str = "30 days"

        horizon_td = pd.to_timedelta(horizon_str)

        training_df = model.history
        training_duration = training_df[TIMESTAMP_COLUMN_NAME].max() - training_df[TIMESTAMP_COLUMN_NAME].min()

        min_initial = pd.Timedelta(days=30)
        initial_duration = max(horizon_td * 3, min_initial)
        initial_duration = min(initial_duration, training_duration * 0.6)
        initial_str = f"{int(initial_duration.total_seconds())} seconds"

        # Enough data?
        if training_duration < initial_duration + horizon_td:
            logger.warning(f"Training data too short for CV (need {initial_duration} + {horizon_td})")
            return None

        remaining_duration = training_duration - initial_duration
        max_folds = 20
        raw_period = remaining_duration / max_folds
        period_duration = max(raw_period, horizon_td)
        period_str = f"{int(period_duration.total_seconds())} seconds"

        # Approximate folds count
        usable = training_duration - initial_duration - horizon_td
        expected_folds = max(1, int(usable / period_duration) + 1)

        logger.info(
            f"Running CV with ~{expected_folds} folds "
            f"(initial={initial_duration}, period={period_duration}, horizon={horizon_td})"
        )

        try:
            df_cv = cross_validation(
                model,
                initial=initial_str,
                period=period_str,
                horizon=horizon_str,
                parallel="processes",
                disable_tqdm=True,
            )
        except Exception as e:
            logger.warning(f"Cross-validation failed: {e}")
            return None

        if df_cv.empty:
            logger.warning("Cross-validation returned no rows")
            return None

        df_p = performance_metrics(df_cv, rolling_window=0.1)

        # R² (extra check for finite values)
        y_true = df_cv["y"].to_numpy()
        y_pred = df_cv["yhat"].to_numpy()
        if y_true.size == 0 or np.allclose(y_true.var(), 0):
            r2 = float("nan")
        else:
            r2 = r2_score(y_true, y_pred)

        metrics = EvaluationMetrics(
            rmse=float(df_p["rmse"].iloc[-1]),
            mae=float(df_p["mae"].iloc[-1]),
            mape=float(df_p["mape"].iloc[-1]),
            mdape=float(df_p["mdape"].iloc[-1]),
            r2=r2,
        )

        logger.info(
            f"RMSE: {metrics.rmse:.4f}, MAE: {metrics.mae:.4f}, "
            f"MAPE: {metrics.mape:.4f}, MdAPE: {metrics.mdape:.4f}, R²: {metrics.r2:.4f}"
        )
        return metrics


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


def _prepare_training_dataframe(training_dataset: TrainingDataSet) -> pd.DataFrame:
    target = training_dataset.target
    regressors = training_dataset.regressors

    # Convert the datapoints to a dataframe - prophet expects the target data to be 'ds' and 'y' structure
    dataframe = _convert_datapoints_to_dataframe(target.datapoints)

    # Add regressors if they are provided
    if regressors is not None:
        for regressor in regressors:
            regressor_dataframe = _convert_datapoints_to_dataframe(
                regressor.datapoints,
                rename_y=regressor.feature_name,
            )

            # Interpolate the regressor values to the target data point timestamps
            dataframe = pd.merge_asof(
                dataframe,
                regressor_dataframe[["ds", regressor.feature_name]],
                on="ds",
                direction="nearest",
            )

    return dataframe
