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
from typing import cast
from uuid import UUID

import pandas as pd
from pandas import DataFrame
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from prophet.serialize import model_from_json, model_to_json

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.common.time_util import TimeUtil
from service_ml_forecast.ml.model_provider import (
    ModelProvider,
    resample_and_interpolate,
)
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

    def train_model(self, training_dataset: TrainingDataSet) -> Prophet | None:
        if training_dataset.target.datapoints is None or len(training_dataset.target.datapoints) == 0:
            logger.error("No target data provided, cannot train Prophet model")
            return None

        logger.info(f"Training model -- {self.config.id} with {len(training_dataset.target.datapoints)} datapoints")

        # Prepare the training dataframe, by resampling, interpolating and merging the target and regressors
        dataframe = _prepare_training_dataframe(training_dataset, self.config.forecast_frequency)

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
            self._evaluate_model(model, dataframe)
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
        future_base[TIMESTAMP_COLUMN_NAME] = future_base[TIMESTAMP_COLUMN_NAME].dt.round(self.config.forecast_frequency)

        # Prepare the future dataframe with regressors if available
        future_prepared = _prepare_forecast_dataframe(
            future_base,
            forecast_dataset,
            self.config.forecast_frequency,
            self.config.id,
        )

        # Generate the forecast using the prepared future dataframe, doesn't matter if its none or empty
        forecast = model.predict(future_prepared)

        # noinspection PyTypeChecker
        datapoints = _convert_prophet_forecast_to_datapoints(forecast)

        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=datapoints,
        )

    def _evaluate_model(self, model: Prophet, training_df: pd.DataFrame) -> None:
        """Evaluate the model using Prophet's cross-validation."""

        try:
            forecast_freq_delta = pd.Timedelta(self.config.forecast_frequency)
            horizon_seconds = self.config.forecast_periods * forecast_freq_delta.total_seconds()
            horizon_str = f"{horizon_seconds} s"
        except ValueError:
            logger.warning(
                f"Could not parse forecast_frequency '{self.config.forecast_frequency}'. "
                "Using default horizon '30 days' for CV."
            )
            horizon_str = "30 days"  # Default fallback horizon

        # Initial training period
        training_duration = training_df[TIMESTAMP_COLUMN_NAME].max() - training_df[TIMESTAMP_COLUMN_NAME].min()
        initial_duration = max(pd.Timedelta(horizon_str) * 3, pd.Timedelta(horizon_str))  # Ensure initial >= horizon
        initial_duration = min(initial_duration, training_duration * 0.5)  # Don't use more than 50% for initial
        initial_str = f"{initial_duration.total_seconds()} s"

        # Period for folds
        period_duration = pd.Timedelta(horizon_str) * 0.5
        period_str = f"{period_duration.total_seconds()} s"

        # Check if data is sufficient for the chosen CV parameters
        if training_duration < pd.Timedelta(initial_str) + pd.Timedelta(horizon_str):
            logger.warning(
                f"Training data duration ({training_duration}) is too short for cross-validation "
                f"with initial='{initial_str}' and horizon='{horizon_str}'. Skipping evaluation."
            )
            return
        if training_duration < pd.Timedelta(initial_str) + pd.Timedelta(period_str):
            logger.warning(
                f"Training data duration ({training_duration}) is too short for cross-validation "
                f"with initial='{initial_str}' and period='{period_str}'. Adjusting period to be smaller."
            )
            # Adjust period to something feasible
            period_duration = (training_duration - pd.Timedelta(initial_str)) * 0.1
            period_str = f"{period_duration.total_seconds()} s"

        # Run cross-validation
        df_cv = cross_validation(
            model,
            initial=initial_str,
            period=period_str,
            horizon=horizon_str,
            parallel="processes",
            disable_tqdm=True,
        )

        # Calculate performance metrics
        df_p = performance_metrics(df_cv, rolling_window=0.1)

        # Log metrics
        rmse = df_p["rmse"].iloc[-1]
        mae = df_p["mae"].iloc[-1]
        mape = df_p["mape"].iloc[-1]
        mdape = df_p["mdape"].iloc[-1]

        logger.info(f"RMSE: {rmse:.4f}, MAE: {mae:.4f}, MAPE: {mape:.4f}, MdAPE: {mdape:.4f}")


def _convert_prophet_forecast_to_datapoints(
    dataframe: pd.DataFrame,
) -> list[AssetDatapoint]:
    datapoints = []
    for _, row in dataframe.iterrows():
        # Convert the timestamp to milliseconds since that is what OpenRemote expects
        millis = TimeUtil.sec_to_ms(int(row[TIMESTAMP_COLUMN_NAME].timestamp()))
        datapoints.append(AssetDatapoint(x=millis, y=row[FORECAST_COLUMN_NAME]))

    return datapoints


def _prepare_training_dataframe(training_dataset: TrainingDataSet, frequency: str) -> DataFrame:
    """Prepare training dataframe with aligned timestamps for target and optional regressors."""
    target = training_dataset.target
    regressors = training_dataset.regressors

    dataframes = []

    # Resample and interpolate target data
    target_df = resample_and_interpolate(
        target.datapoints,
        frequency,
        time_col_name=TIMESTAMP_COLUMN_NAME,
        value_col_name=VALUE_COLUMN_NAME,
    )
    if target_df is None:
        logger.error("Cannot prepare training data: Target data resampling resulted in None.")
        return DataFrame(columns=[TIMESTAMP_COLUMN_NAME, VALUE_COLUMN_NAME])

    dataframes.append(target_df)
    target_len = len(target_df)
    logger.info(f"Target data resampled to {frequency} frequency, resulting in {target_len} datapoints.")

    # Resample and interpolate regressor data if they are provided
    if regressors is not None:
        for regressor in regressors:
            regressor_df = resample_and_interpolate(
                regressor.datapoints,
                frequency,
                time_col_name=TIMESTAMP_COLUMN_NAME,
                value_col_name=regressor.feature_name,
            )
            if regressor_df is not None and not regressor_df.empty:
                regressor_len = len(regressor_df)
                logger.info(f"Regressor '{regressor.feature_name}' resampled, resulting in {regressor_len} datapoints.")
                dataframes.append(regressor_df)
            else:
                logger.warning(
                    f"Regressor '{regressor.feature_name}' data is empty or None after resampling. It will be excluded."
                )

    # Find the common date range to avoid going outside the training range
    min_date = max(df[TIMESTAMP_COLUMN_NAME].min() for df in dataframes)
    max_date = min(df[TIMESTAMP_COLUMN_NAME].max() for df in dataframes)
    logger.info(f"Common date range for training data: {min_date} to {max_date}")

    # Create a full index for the common date range
    full_index = pd.date_range(start=min_date, end=max_date, freq=frequency)

    # Start with target data
    result = target_df[
        (target_df[TIMESTAMP_COLUMN_NAME] >= min_date) & (target_df[TIMESTAMP_COLUMN_NAME] <= max_date)
    ].copy()

    # Merge the regressors if they are provided
    if regressors is not None:
        for i, _regressor in enumerate(regressors):
            regressor_df = dataframes[i + 1]  # note +1 because target_df is first component
            if regressor_df is not None and not regressor_df.empty:
                result = result.merge(regressor_df, on=TIMESTAMP_COLUMN_NAME, how="left")

    # Update the index and reindex to the full index
    result = result.set_index(TIMESTAMP_COLUMN_NAME)
    result = result.reindex(full_index)

    # Interpolate any missing values using time-based interpolation
    numeric_columns = result.select_dtypes(include=["float64", "int64"]).columns
    for col in numeric_columns:
        result[col] = result[col].interpolate(method="time")
        result[col] = result[col].ffill().bfill()

    # Reset index and rename it back to the original timestamp column name
    result = result.reset_index().rename(columns={"index": TIMESTAMP_COLUMN_NAME})

    return cast(DataFrame, result)


def _prepare_forecast_dataframe(
    future_df: DataFrame,
    forecast_dataset: ForecastDataSet | None,
    frequency: str,
    config_id: UUID,
) -> DataFrame:
    """Prepares the future dataframe by adding aligned regressor data."""
    if forecast_dataset is None or not forecast_dataset.regressors:
        logger.info(f"No regressors provided for forecast -- {config_id}")
        return future_df

    logger.info(f"Preparing forecast dataframe with {len(forecast_dataset.regressors)} regressor(s) -- {config_id}")

    prepared_future_df = future_df.copy()

    for regressor in forecast_dataset.regressors:
        if regressor.datapoints is None or len(regressor.datapoints) == 0:
            logger.warning(f"Regressor '{regressor.feature_name}' has no data. Skipping.")
            continue

        regressor_dataframe = resample_and_interpolate(
            datapoints=regressor.datapoints,
            frequency=frequency,
            time_col_name=TIMESTAMP_COLUMN_NAME,
            value_col_name=regressor.feature_name,  # use the feature name as the value column
        )

        if regressor_dataframe is None or regressor_dataframe.empty:
            logger.warning(
                f"Regressor '{regressor.feature_name}' data is empty or None after resampling for the forecast period. "
                f"This regressor cannot be added to the future dataframe for model {config_id}."
            )
            continue

        regressor_len = len(regressor_dataframe)
        logger.info(
            f"Regressor '{regressor.feature_name}' resampled for forecast period, result {regressor_len} datapoints."
        )

        # Ensure regressor dataframe covers the future range as much as possible
        regressor_dataframe = regressor_dataframe.set_index(TIMESTAMP_COLUMN_NAME)
        regressor_dataframe = regressor_dataframe.reindex(
            prepared_future_df[TIMESTAMP_COLUMN_NAME],
            method="nearest",
        )
        regressor_dataframe = regressor_dataframe.reset_index()

        # Merge the prepared regressor data with the future dataframe (on the timestamp column)
        prepared_future_df = prepared_future_df.merge(
            regressor_dataframe[[TIMESTAMP_COLUMN_NAME, regressor.feature_name]],
            on=TIMESTAMP_COLUMN_NAME,
            how="left",
        )

    return prepared_future_df
