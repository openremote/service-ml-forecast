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

import json
import logging
from uuid import UUID

import numpy as np
import pandas as pd
from darts import TimeSeries
from darts.models import Prophet as DartsProphet
from openremote_client import AssetDatapoint
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml.data_processing import (
    align_forecast_data,
    align_training_data,
)
from service_ml_forecast.ml.backtesting import calculate_backtest_parameters, run_darts_backtest
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


class ProphetModelProvider(ModelProvider[DartsProphet]):
    """Prophet model provider.
    
    Prophet is an additive regression model, widely used for time series forecasting.
    """

    def __init__(self, config: ProphetModelConfig) -> None:
        self.config = config
        self.model_storage_service = ModelStorageService()

        # All training data and covariates are stored in the Darts model itself

        # Suppress Prophet's verbose logging
        logging.getLogger("cmdstanpy").disabled = True

    def train_model(self, training_dataset: TrainingDataSet) -> DartsProphet | None:
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

        # Convert to Darts TimeSeries format
        target_series = TimeSeries.from_dataframe(
            dataframe, 
            time_col=TIMESTAMP_COLUMN_NAME, 
            value_cols=[VALUE_COLUMN_NAME]
        )
        
        # Prepare covariates if available
        covariates = None
        if training_dataset.regressors is not None and len(training_dataset.regressors) > 0:
            logger.info(f"Training with {len(training_dataset.regressors)} regressor(s) -- {self.config.id}")
            covariate_cols = [regressor.feature_name for regressor in training_dataset.regressors]
            # Check if regressor columns exist in dataframe
            available_cols = [col for col in covariate_cols if col in dataframe.columns]
            if available_cols:
                covariates = TimeSeries.from_dataframe(
                    dataframe,
                    time_col=TIMESTAMP_COLUMN_NAME,
                    value_cols=available_cols
                )

        # Construct Darts Prophet model with hyperparameters from config
        model = DartsProphet(
            weekly_seasonality=self.config.weekly_seasonality,
            yearly_seasonality=self.config.yearly_seasonality,
            daily_seasonality=self.config.daily_seasonality,
            seasonality_mode=self.config.seasonality_mode,
            changepoint_prior_scale=self.config.changepoint_prior_scale,
            changepoint_range=self.config.changepoint_range,
        )

        # Train the model (Darts will store training data and covariates automatically)
        model.fit(target_series, future_covariates=covariates)
        
        return model

    def load_model(self, model_id: UUID) -> DartsProphet:
        # Use the storage service's Darts-native load method
        return self.model_storage_service.load(DartsProphet, model_id)

    def save_model(self, model: DartsProphet) -> None:
        # Use the storage service's Darts-native save method
        self.model_storage_service.save(model, self.config.id)

    def generate_forecast(self, forecast_dataset: ForecastDataSet | None = None) -> ForecastResult:
        model = self.load_model(self.config.id)

        # Prepare future covariates if available
        future_covariates = None
        if forecast_dataset is not None and forecast_dataset.regressors:
            logger.info(f"Generating forecast with {len(forecast_dataset.regressors)} regressor(s) -- {self.config.id}")
            
            # Create a base future dataframe starting after the training data ends
            if model.training_series is not None:
                last_training_time = model.training_series.end_time()
                start_time = last_training_time + pd.Timedelta(self.config.forecast_frequency)
            else:
                start_time = pd.Timestamp.now().round(self.config.forecast_frequency)
                logger.warning(f"No training data available in model, using current time for future covariates -- {self.config.id}")

            future_base = pd.DataFrame({
                TIMESTAMP_COLUMN_NAME: pd.date_range(
                    start=start_time,
                    periods=self.config.forecast_periods,
                    freq=self.config.forecast_frequency
                )
            })
            
            # Prepare the future dataframe with regressors
            future_prepared = align_forecast_data(
                future_base,
                forecast_dataset,
                self.config.forecast_frequency,
                self.config.id,
                timestamp_col=TIMESTAMP_COLUMN_NAME,
            )
            
            # Convert to Darts TimeSeries for covariates
            covariate_cols = [regressor.feature_name for regressor in forecast_dataset.regressors]
            available_cols = [col for col in covariate_cols if col in future_prepared.columns]
            if available_cols:
                future_covariates = TimeSeries.from_dataframe(
                    future_prepared,
                    time_col=TIMESTAMP_COLUMN_NAME,
                    value_cols=available_cols
                )

        # Generate forecast using Darts
        forecast_series = model.predict(
            n=self.config.forecast_periods,
            future_covariates=future_covariates
        )

        # Convert to datapoints
        datapoints = _convert_darts_forecast_to_datapoints(forecast_series.to_dataframe())

        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=datapoints,
        )

    def evaluate_model(self, model: DartsProphet) -> EvaluationMetrics | None:
        """Evaluate the model using Darts backtesting"""

        try:
            # Calculate backtesting parameters using model's training data
            if model.training_series is None:
                logger.warning("No training data available for evaluation")
                return None
                
            backtest_config = calculate_backtest_parameters(
                series_length=len(model.training_series),
                forecast_periods=self.config.forecast_periods,
            )
            if not backtest_config:
                return None
                
            # Run comprehensive evaluation using Darts backtesting (model handles its own data)
            return run_darts_backtest(
                model=model,
                backtest_config=backtest_config,
            )
            
        except Exception as e:
            logger.error(f"Error during model evaluation: {e}")
            return None

def _convert_darts_forecast_to_datapoints(
    dataframe: pd.DataFrame,
) -> list[AssetDatapoint]:
    """Convert Darts TimeSeries DataFrame to OpenRemote AssetDatapoints.
    
    Darts TimeSeries.to_dataframe() returns a DataFrame with:
    - DatetimeIndex as the index
    - Column name(s) for the series values
    """
    datapoints = []
    
    # Reset index to get timestamp as a column
    df_reset = dataframe.reset_index()
    timestamp_col = df_reset.columns[0]
    value_col = df_reset.columns[1]
    
    for _, row in df_reset.iterrows():
        # Convert the timestamp to milliseconds since that is what OpenRemote expects
        millis = TimeUtil.sec_to_ms(int(row[timestamp_col].timestamp()))
        datapoints.append(AssetDatapoint(x=millis, y=row[value_col]))

    return datapoints
