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
from darts import TimeSeries
from darts.models import XGBModel
from openremote_client import AssetDatapoint

from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml.backtesting import calculate_backtest_parameters, run_darts_backtest
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
from service_ml_forecast.models.model_config import AssetDatapointFeature, XGBoostModelConfig
from service_ml_forecast.services.model_storage_service import ModelStorageService

logger = logging.getLogger(__name__)

# Constants
MIN_DATAPOINTS_FOR_XGBOOST = 10
MIN_RECOMMENDED_DATAPOINTS = 100
TIMESTAMP_COLUMN_NAME = "timestamp"
VALUE_COLUMN_NAME = "value"


class XGBoostModelProvider(ModelProvider[XGBModel]):
    """XGBoost model provider using Darts."""

    def __init__(self, config: XGBoostModelConfig) -> None:
        self.config = config
        self.model_storage_service = ModelStorageService()

    def train_model(self, training_dataset: TrainingDataSet) -> XGBModel | None:
        """Train XGBoost model on the provided dataset.

        Args:
            training_dataset: Dataset containing target and optional regressor data

        Returns:
            Trained XGBModel or None if training fails
        """
        if training_dataset.target.datapoints is None or len(training_dataset.target.datapoints) == 0:
            logger.error("No target data provided, cannot train model")
            return None

        logger.info(f"Training model {self.config.id} with {len(training_dataset.target.datapoints)} datapoints")

        dataframe = align_training_data(
            training_dataset,
            self.config.forecast_frequency,
            timestamp_col=TIMESTAMP_COLUMN_NAME,
            value_col=VALUE_COLUMN_NAME,
        )

        if dataframe.empty or len(dataframe) < MIN_DATAPOINTS_FOR_XGBOOST:
            logger.error(f"Insufficient training data for model {self.config.id}")
            return None
        elif len(dataframe) < MIN_RECOMMENDED_DATAPOINTS:
            logger.warning(
                f"Limited training data: {len(dataframe)} points (recommended: {MIN_RECOMMENDED_DATAPOINTS})"
            )

        target_series = TimeSeries.from_dataframe(
            dataframe, time_col=TIMESTAMP_COLUMN_NAME, value_cols=[VALUE_COLUMN_NAME]
        )

        # Prepare covariates based on model configuration
        past_covariates = None
        future_covariates = None

        # Combine all covariates from both past and future covariate configs
        all_covariate_features: list[AssetDatapointFeature] = []
        if self.config.past_covariates:
            all_covariate_features.extend(self.config.past_covariates)
        if self.config.future_covariates:
            all_covariate_features.extend(self.config.future_covariates)

        if training_dataset.covariates and len(training_dataset.covariates) > 0:
            logger.info(f"Training with {len(training_dataset.covariates)} covariates")
            covariate_cols = [r.feature_name for r in training_dataset.covariates]
            available_cols = [col for col in covariate_cols if col in dataframe.columns]
            if available_cols:
                covariates_ts = TimeSeries.from_dataframe(
                    dataframe, time_col=TIMESTAMP_COLUMN_NAME, value_cols=available_cols
                )
                # Assign covariates based on configuration
                if self.config.lags_past_covariates is not None:
                    past_covariates = covariates_ts
                if self.config.lags_future_covariates is not None:
                    future_covariates = covariates_ts

        # Build model kwargs, only including covariate lags if they're configured
        model_kwargs = {
            "lags": self.config.lags,
            "output_chunk_length": self.config.output_chunk_length,
            "n_estimators": self.config.n_estimators,
            "max_depth": self.config.max_depth,
            "learning_rate": self.config.learning_rate,
            "subsample": self.config.subsample,
            "random_state": self.config.random_state,
        }

        if self.config.lags_future_covariates is not None:
            model_kwargs["lags_future_covariates"] = self.config.lags_future_covariates

        if self.config.lags_past_covariates is not None:
            model_kwargs["lags_past_covariates"] = self.config.lags_past_covariates

        model = XGBModel(**model_kwargs)

        # Fit model with appropriate covariates
        fit_kwargs = {"series": target_series}
        if future_covariates is not None:
            fit_kwargs["future_covariates"] = future_covariates
        if past_covariates is not None:
            fit_kwargs["past_covariates"] = past_covariates

        model.fit(**fit_kwargs)

        return model

    def load_model(self, model_id: UUID) -> XGBModel:
        """Load trained XGBoost model from storage.

        Args:
            model_id: UUID of the model to load

        Returns:
            Loaded XGBModel instance
        """
        return self.model_storage_service.load(XGBModel, model_id)

    def save_model(self, model: XGBModel) -> None:
        """Save trained XGBoost model to storage.

        Args:
            model: Trained XGBModel to save
        """
        self.model_storage_service.save(model, self.config.id)

    def generate_forecast(self, forecast_dataset: ForecastDataSet | None = None) -> ForecastResult:
        """Generate forecast using trained XGBoost model.

        Args:
            forecast_dataset: Optional dataset containing regressor data for forecasting

        Returns:
            ForecastResult containing predicted datapoints
        """
        model = self.load_model(self.config.id)

        future_covariates = None
        past_covariates = None
        if forecast_dataset and forecast_dataset.covariates:
            logger.info(f"Generating forecast with {len(forecast_dataset.covariates)} regressors")

            if model.training_series is not None:
                start_time = model.training_series.end_time() + pd.Timedelta(self.config.forecast_frequency)
            else:
                start_time = pd.Timestamp.now().round(self.config.forecast_frequency)
                logger.warning("No training data available, using current time")

            # Calculate time range extensions based on covariate lag requirements
            extended_start = start_time
            total_periods = self.config.forecast_periods

            # For past covariates, extend backward (negative lags)
            if self.config.lags_past_covariates is not None:
                past_lags = (
                    self.config.lags_past_covariates
                    if isinstance(self.config.lags_past_covariates, list)
                    else [self.config.lags_past_covariates]
                )
                min_past_lag = min(past_lags)  # This will be negative, e.g. -3
                historical_periods = abs(min_past_lag)
                extended_start = start_time + pd.Timedelta(self.config.forecast_frequency) * min_past_lag
                total_periods += historical_periods

            # For future covariates, extend forward (non-negative lags)
            if self.config.lags_future_covariates is not None:
                future_lags = (
                    self.config.lags_future_covariates
                    if isinstance(self.config.lags_future_covariates, list)
                    else [self.config.lags_future_covariates]
                )
                max_future_lag = max(future_lags)  # This will be non-negative, e.g. 2
                total_periods += max_future_lag

            future_base = pd.DataFrame(
                {
                    TIMESTAMP_COLUMN_NAME: pd.date_range(
                        start=extended_start, periods=total_periods, freq=self.config.forecast_frequency
                    )
                }
            )

            future_prepared = align_forecast_data(
                future_base,
                forecast_dataset,
                self.config.forecast_frequency,
                self.config.id,
                timestamp_col=TIMESTAMP_COLUMN_NAME,
            )

            covariate_cols = [r.feature_name for r in forecast_dataset.covariates]
            available_cols = [col for col in covariate_cols if col in future_prepared.columns]
            if available_cols:
                covariates_ts = TimeSeries.from_dataframe(
                    future_prepared, time_col=TIMESTAMP_COLUMN_NAME, value_cols=available_cols
                )
                # Assign covariates based on configuration
                if self.config.lags_future_covariates is not None:
                    future_covariates = covariates_ts
                if self.config.lags_past_covariates is not None:
                    past_covariates = covariates_ts

        # Generate forecast with appropriate covariates
        predict_kwargs = {"n": self.config.forecast_periods}
        if future_covariates is not None:
            predict_kwargs["future_covariates"] = future_covariates
        if past_covariates is not None:
            predict_kwargs["past_covariates"] = past_covariates

        forecast_series = model.predict(**predict_kwargs)
        datapoints = _convert_darts_forecast_to_datapoints(forecast_series.to_dataframe())

        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=datapoints,
        )

    def evaluate_model(self, model: XGBModel) -> EvaluationMetrics | None:
        """Evaluate XGBoost model using Darts backtesting.

        Args:
            model: Trained XGBModel to evaluate

        Returns:
            EvaluationMetrics or None if evaluation fails
        """
        try:
            if model.training_series is None:
                logger.warning("No training data available for evaluation")
                return None

            backtest_config = calculate_backtest_parameters(
                series_length=len(model.training_series),
                forecast_periods=self.config.forecast_periods,
            )
            if not backtest_config:
                return None

            return run_darts_backtest(model=model, backtest_config=backtest_config)

        except Exception as e:
            logger.error(f"Error during model evaluation: {e}")
            return None


def _convert_darts_forecast_to_datapoints(dataframe: pd.DataFrame) -> list[AssetDatapoint]:
    """Convert Darts TimeSeries DataFrame to OpenRemote AssetDatapoints.

    Args:
        dataframe: Darts TimeSeries DataFrame to convert

    Returns:
        List of AssetDatapoints
    """
    df_reset = dataframe.reset_index()
    timestamp_col = df_reset.columns[0]
    value_col = df_reset.columns[1]

    datapoints = []
    for _, row in df_reset.iterrows():
        millis = TimeUtil.sec_to_ms(int(row[timestamp_col].timestamp()))
        datapoints.append(AssetDatapoint(x=millis, y=row[value_col]))

    return datapoints
