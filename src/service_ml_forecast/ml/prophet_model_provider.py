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
    """Prophet model provider."""

    def __init__(self, config: ProphetModelConfig) -> None:
        self.config = config
        self.model_storage_service = ModelStorageService()

        # Suppress Prophet's verbose logging
        logging.getLogger("cmdstanpy").disabled = True

    def train_model(self, training_dataset: TrainingDataSet) -> Prophet | None:
        if training_dataset.target.datapoints is None or len(training_dataset.target.datapoints) == 0:
            logger.error("No target data provided, cannot train Prophet model")
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

        # Train the model
        model.fit(dataframe)

        # Perform quick evaluation of the model using cross-validation
        try:
            self.evaluate_model(model)
        except Exception as e:
            logger.error(f"Failed to evaluate model {self.config.id} using cross-validation: {e}", exc_info=True)

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
        """Evaluate the model using Prophet's cross-validation."""
        # Calculate horizon from config
        try:
            horizon_delta = pd.Timedelta(self.config.forecast_frequency) * self.config.forecast_periods
            secs = int(horizon_delta.total_seconds())
            horizon_str = f"{secs} seconds"
        except ValueError:
            logger.warning(f"Invalid forecast_frequency '{self.config.forecast_frequency}', using 30 days")
            horizon_str = "30 days"

        # Get training data info
        training_df = model.history
        training_duration = training_df[TIMESTAMP_COLUMN_NAME].max() - training_df[TIMESTAMP_COLUMN_NAME].min()

        # Set initial training period (min 30 days, max 60% of data)
        min_initial = pd.Timedelta(days=30)
        initial_duration = max(pd.Timedelta(horizon_str) * 3, min_initial)
        initial_duration = min(initial_duration, training_duration * 0.6)
        initial_str = f"{int(initial_duration.total_seconds())} seconds"

        # Check if we have enough data
        if training_duration < pd.Timedelta(initial_str) + pd.Timedelta(horizon_str):
            logger.warning(f"Training data too short for CV (need {initial_str} + {horizon_str})")
            return None

        # Calculate period between folds (limit to 20 folds max)
        remaining_duration = training_duration - pd.Timedelta(initial_str)
        max_folds = 20
        period_duration = remaining_duration / max_folds
        period_str = f"{int(period_duration.total_seconds())} seconds"

        expected_folds = min(max_folds, max(1, int(remaining_duration / period_duration)))
        logger.info(
            f"Running CV with {expected_folds} folds "
            f"(initial={initial_str}, period={period_str}, horizon={horizon_str})"
        )

        # Run cross-validation
        df_cv = cross_validation(
            model, initial=initial_str, period=period_str, horizon=horizon_str, parallel="processes", disable_tqdm=True
        )

        # Calculate and return metrics
        df_p = performance_metrics(df_cv, rolling_window=0.1)

        # Calculate R2 using sklearn, prophet does not provide R2
        y_true = df_cv["y"].to_numpy()
        y_pred = df_cv["yhat"].to_numpy()
        r2 = r2_score(y_true, y_pred)

        metrics = EvaluationMetrics(
            rmse=df_p["rmse"].iloc[-1],
            mae=df_p["mae"].iloc[-1],
            mape=df_p["mape"].iloc[-1],
            mdape=df_p["mdape"].iloc[-1],
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
