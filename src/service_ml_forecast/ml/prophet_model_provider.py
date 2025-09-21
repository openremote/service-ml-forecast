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

import pandas as pd
import numpy as np
from openremote_client import AssetDatapoint
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from prophet.serialize import model_from_json, model_to_json
from sklearn.metrics import r2_score

from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml.data_processing import (
    align_forecast_data,
    align_training_data,
)
from service_ml_forecast.ml.evaluation_metrics import EvaluationMetrics
from service_ml_forecast.ml.model_provider import ModelProvider
from service_ml_forecast.models.feature_data_wrappers import (
    ForecastDataSet,
    ForecastResult,
    TrainingDataSet,
)
from service_ml_forecast.models.model_config import ProphetModelConfig
from service_ml_forecast.services.model_storage_service import ModelStorageService

logger = logging.getLogger(__name__)

# Constants
MIN_DATAPOINTS_FOR_PROPHET = 2
MIN_RECOMMENDED_DATAPOINTS = 50
TIMESTAMP_COLUMN_NAME = "ds"
VALUE_COLUMN_NAME = "y"
FORECAST_COLUMN_NAME = "yhat"


class ProphetModelProvider(ModelProvider[Prophet]):
    """Prophet model provider.
    
    Prophet is an additive regression model, widely used for time series forecasting.
    """

    def __init__(self, config: ProphetModelConfig) -> None:
        self.config = config
        self.model_storage_service = ModelStorageService()

        # Suppress Prophet's verbose logging
        logging.getLogger("cmdstanpy").disabled = True

    def train_model(self, training_dataset: TrainingDataSet) -> Prophet | None:
        if training_dataset.target.datapoints is None or len(training_dataset.target.datapoints) == 0:
            logger.error("No target data provided, cannot train model")
            return None

        logger.info(f"Training model -- {self.config.id} with {len(training_dataset.target.datapoints)} datapoints")

        # Prepare the training dataframe, by resampling, interpolating and merging the target and regressors
        dataframe = align_training_data(
            training_dataset,
            self.config.forecast_frequency,
            timestamp_col=TIMESTAMP_COLUMN_NAME,
            value_col=VALUE_COLUMN_NAME,
        )

        # Check if dataframe is empty or too small after preprocessing
        if dataframe.empty or len(dataframe) < MIN_DATAPOINTS_FOR_PROPHET:
            logger.error(
                f"Training data for model {self.config.id} is insufficient after resampling and cleaning. Cannot train."
            )
            return None
        elif len(dataframe) < MIN_RECOMMENDED_DATAPOINTS:
            logger.warning(
                f"Training dataset for model {self.config.id} has only {len(dataframe)} datapoints "
                f"after resampling (minimum recommended: {MIN_RECOMMENDED_DATAPOINTS})."
            )

        # Construct model and apply hyperparameters from the model config``
        model = Prophet()
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

        # Train/fit the model
        model.fit(dataframe)

        return model

    def load_model(self, model_id: UUID) -> Prophet:
        model_json = self.model_storage_service.get(model_id)
        return model_from_json(model_json)

    def save_model(self, model: Prophet) -> None:
        model_json = model_to_json(model)
        self.model_storage_service.save(model_json, self.config.id)
        logger.info(f"Saved model -- {self.config.id}")

    def generate_forecast(self, forecast_dataset: ForecastDataSet | None = None) -> ForecastResult:
        model = self.load_model(self.config.id)

        # Create the future dataframe (this creates a dataframe starting from the last datapoint in the training set!)
        future_base = model.make_future_dataframe(
            periods=self.config.forecast_periods,
            freq=self.config.forecast_frequency,
            include_history=False,
        )

        # round the future timestamps to the forecast frequency for a clean and consistent forecast
        original_times = future_base[TIMESTAMP_COLUMN_NAME].copy()
        future_base[TIMESTAMP_COLUMN_NAME] = future_base[TIMESTAMP_COLUMN_NAME].dt.round(self.config.forecast_frequency)

        # Log timestamp rounding effects
        time_shift = (future_base[TIMESTAMP_COLUMN_NAME] - original_times).abs().max()
        if time_shift > pd.Timedelta(minutes=1):
            logger.warning(f"Timestamp rounding shifted forecasts by up to {time_shift} for model {self.config.id}")

        # Prepare the future dataframe with regressors if available
        future_prepared = align_forecast_data(
            future_base,
            forecast_dataset,
            self.config.forecast_frequency,
            self.config.id,
            timestamp_col=TIMESTAMP_COLUMN_NAME,
        )

        # Generate the forecast using the prepared future dataframe, doesn't matter if its none or empty
        forecast = model.predict(future_prepared)

        # Validate forecast quality
        self._validate_forecast_quality(forecast)

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
            logger.warning(
                f"Invalid forecast_frequency '{self.config.forecast_frequency}', using 30 days"
            )
            horizon_str = "30 days"

        horizon_td = pd.to_timedelta(horizon_str)

        training_df = model.history
        training_duration = (
            training_df[TIMESTAMP_COLUMN_NAME].max()
            - training_df[TIMESTAMP_COLUMN_NAME].min()
        )

        min_initial = pd.Timedelta(days=30)
        initial_duration = max(horizon_td * 3, min_initial)
        initial_duration = min(initial_duration, training_duration * 0.6)
        initial_str = f"{int(initial_duration.total_seconds())} seconds"

        # Enough data?
        if training_duration < initial_duration + horizon_td:
            logger.warning(
                f"Training data too short for CV (need {initial_duration} + {horizon_td})"
            )
            return None

        remaining_duration = training_duration - initial_duration
        max_folds = 20
        raw_period = remaining_duration / max_folds
        period_duration = max(raw_period, horizon_td)
        period_str = f"{int(period_duration.total_seconds())} seconds"

        # Approximate folds count
        usable = training_duration - initial_duration - horizon_td
        expected_folds = max(1, int(usable / period_duration) + 1)

        if expected_folds > max_folds:
            logger.info(
                f"Capping folds to {max_folds} (dataset would allow ~{expected_folds})"
            )
            expected_folds = max_folds

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

        # -------------------------------------------------------------------------
        # Metrics
        # -------------------------------------------------------------------------
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

    def _validate_forecast_quality(self, forecast: pd.DataFrame) -> None:
        """Validate forecast quality and log warnings for potential issues."""

        # Check for NaN values
        if forecast[FORECAST_COLUMN_NAME].isna().any():
            nan_count = forecast[FORECAST_COLUMN_NAME].isna().sum()
            logger.warning(f"Forecast contains {nan_count} NaN values for model {self.config.id}")

        # Check for extreme outliers (values > 10x the mean) - generic check
        forecast_mean = forecast[FORECAST_COLUMN_NAME].mean()
        if forecast_mean != 0:  # Avoid division by zero
            extreme_threshold = abs(forecast_mean) * 10
            extreme_count = (forecast[FORECAST_COLUMN_NAME].abs() > extreme_threshold).sum()
            if extreme_count > 0:
                logger.warning(
                    f"Forecast contains {extreme_count} extreme outliers (>10x mean) for model {self.config.id}"
                )


def _convert_prophet_forecast_to_datapoints(
    dataframe: pd.DataFrame,
) -> list[AssetDatapoint]:
    datapoints = []
    for _, row in dataframe.iterrows():
        # Convert the timestamp to milliseconds since that is what OpenRemote expects
        millis = TimeUtil.sec_to_ms(int(row[TIMESTAMP_COLUMN_NAME].timestamp()))
        datapoints.append(AssetDatapoint(x=millis, y=row[FORECAST_COLUMN_NAME]))

    return datapoints
