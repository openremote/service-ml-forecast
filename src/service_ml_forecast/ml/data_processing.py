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

import numpy as np
import pandas as pd
from openremote_client import AssetDatapoint
from pandas import DataFrame

from service_ml_forecast.models.feature_data_wrappers import ForecastDataSet, TrainingDataSet

logger = logging.getLogger(__name__)

# Constants
MIN_UNIQUE_TIMESTAMPS_FOR_RESAMPLE = 2


def convert_datapoints_to_dataframe(
    datapoints: list[AssetDatapoint],
    time_col_name: str,
    value_col_name: str,
) -> pd.DataFrame:
    """Convert AssetDatapoints to DataFrame with time and value columns.

    Args:
        datapoints: List of AssetDatapoint objects
        time_col_name: Name for the time column
        value_col_name: Name for the value column
    """
    if not datapoints:
        return pd.DataFrame(columns=[time_col_name, value_col_name])

    timeseries_df = pd.DataFrame([{time_col_name: point.x, value_col_name: point.y} for point in datapoints])

    # Reject corrupt values before aggregation or interpolation can hide them.
    # NaN remains a missing observation, handled by the existing gap policy.
    if np.isinf(timeseries_df[value_col_name].to_numpy(dtype=float)).any():
        raise ValueError(f"Series '{value_col_name}' contains infinite values")

    timeseries_df[time_col_name] = pd.to_datetime(timeseries_df[time_col_name], unit="ms")
    timeseries_df = timeseries_df.sort_values(time_col_name)
    timeseries_df = timeseries_df.groupby(time_col_name, as_index=False).mean()

    return timeseries_df


def resample_and_interpolate(
    datapoints: list[AssetDatapoint],
    frequency: str,
    time_col_name: str,
    value_col_name: str,
) -> pd.DataFrame | None:
    """Resample and interpolate time series data to specified frequency.

    Args:
        datapoints: List of AssetDatapoint objects
        frequency: Target frequency string (e.g., 'H', '15T')
        time_col_name: Name for the time column
        value_col_name: Name for the value column
    """
    if not datapoints:
        return None

    timeseries_df = convert_datapoints_to_dataframe(
        datapoints, time_col_name=time_col_name, value_col_name=value_col_name
    )

    if timeseries_df[time_col_name].nunique() < MIN_UNIQUE_TIMESTAMPS_FOR_RESAMPLE:
        logger.warning(
            f"Cannot resample series '{value_col_name}' with frequency '{frequency}': "
            f"insufficient unique timestamps ({timeseries_df[time_col_name].nunique()})"
        )
        return timeseries_df.groupby(time_col_name).mean().reset_index() if len(timeseries_df) > 1 else timeseries_df

    timeseries_df = timeseries_df.set_index(time_col_name)

    if not timeseries_df.index.is_monotonic_increasing:
        logger.warning(f"Sorting data for {value_col_name} before resampling")
        timeseries_df = timeseries_df.sort_index()

    try:
        df_resampled = timeseries_df.resample(frequency).mean()
        df_filled = df_resampled.interpolate(method="time", limit=2, limit_area="inside")
    except ValueError as e:
        logger.error(f"Resampling failed for '{value_col_name}': {e}")
        return timeseries_df.reset_index()

    if df_filled[value_col_name].isna().any():
        logger.error(f"Interpolation incomplete for '{value_col_name}' - critical data issue")

    return df_filled.reset_index()


def align_training_data(
    training_dataset: TrainingDataSet, frequency: str, timestamp_col: str = "timestamp", value_col: str = "value"
) -> DataFrame:
    """Prepare aligned training DataFrame with target and regressor data.

    Args:
        training_dataset: Training dataset containing target and optional regressors
        frequency: Target frequency string (e.g., 'H', '15T', 'D')
        timestamp_col: Name for the timestamp column in output DataFrame
        value_col: Name for the target value column in output DataFrame
    """
    target = training_dataset.target
    regressors = training_dataset.covariates
    dataframes = []

    target_df = resample_and_interpolate(
        target.datapoints, frequency, time_col_name=timestamp_col, value_col_name=value_col
    )
    if target_df is None:
        logger.error("Target data resampling failed")
        return DataFrame(columns=[timestamp_col, value_col])

    dataframes.append(target_df)
    logger.info(f"Target data resampled: {len(target_df)} points at {frequency} frequency")

    if regressors:
        for regressor in regressors:
            regressor_df = resample_and_interpolate(
                regressor.datapoints, frequency, time_col_name=timestamp_col, value_col_name=regressor.feature_name
            )
            if regressor_df is not None and not regressor_df.empty:
                logger.info(f"Regressor '{regressor.feature_name}' resampled: {len(regressor_df)} points")
                dataframes.append(regressor_df)
            else:
                raise ValueError(f"Regressor '{regressor.feature_name}' has no usable training data")

    min_date = max(df[timestamp_col].min() for df in dataframes)
    max_date = min(df[timestamp_col].max() for df in dataframes)
    logger.info(f"Aligned date range: {min_date} to {max_date}")

    full_index = pd.date_range(start=min_date, end=max_date, freq=frequency)
    result = target_df[(target_df[timestamp_col] >= min_date) & (target_df[timestamp_col] <= max_date)].copy()

    if regressors:
        for i, _regressor in enumerate(regressors):
            regressor_df = dataframes[i + 1]
            if regressor_df is not None and not regressor_df.empty:
                result = result.merge(regressor_df, on=timestamp_col, how="left")

    result = result.set_index(timestamp_col).reindex(full_index)
    numeric_columns = result.select_dtypes(include=["float64", "int64"]).columns

    if len(numeric_columns) > 0:
        missing = result[numeric_columns].isna().any(axis=1)
        if missing.any():
            last_missing = result.index[missing][-1]
            logger.warning("Using contiguous training suffix after unresolved gap at %s", last_missing)
            result = result.loc[result.index > last_missing]

    result = result.reset_index().rename(columns={"index": timestamp_col})

    return cast(DataFrame, result)


def align_forecast_data(
    future_df: DataFrame,
    forecast_dataset: ForecastDataSet | None,
    frequency: str,
    config_id: UUID,
    timestamp_col: str = "timestamp",
) -> DataFrame:
    """Prepare forecast DataFrame by adding aligned regressor data.

    Args:
        future_df: Base future DataFrame with timestamps
        forecast_dataset: Forecast dataset containing optional regressors
        frequency: Target frequency string (e.g., 'H', '15T', 'D')
        config_id: Model configuration ID for logging
        timestamp_col: Name of the timestamp column in the future DataFrame
    """
    if forecast_dataset is None or not forecast_dataset.covariates:
        logger.info(f"No regressors for forecast {config_id}")
        return future_df

    logger.info(f"Preparing forecast with {len(forecast_dataset.covariates)} regressors - {config_id}")
    prepared_future_df = future_df.copy()

    for regressor in forecast_dataset.covariates:
        if not regressor.datapoints:
            raise ValueError(f"Regressor '{regressor.feature_name}' has no forecast data")

        regressor_dataframe = convert_datapoints_to_dataframe(
            regressor.datapoints, time_col_name=timestamp_col, value_col_name=regressor.feature_name
        )

        if regressor_dataframe is None or regressor_dataframe.empty:
            raise ValueError(f"Regressor '{regressor.feature_name}' has no usable forecast data")

        logger.info(f"Regressor '{regressor.feature_name}' resampled: {len(regressor_dataframe)} points")

        regressor_dataframe = regressor_dataframe.set_index(timestamp_col).resample(frequency).mean()
        regressor_dataframe = regressor_dataframe.reindex(prepared_future_df[timestamp_col])
        regressor_dataframe = regressor_dataframe.reset_index()

        if regressor_dataframe[regressor.feature_name].isna().any():
            raise ValueError(f"Regressor '{regressor.feature_name}' does not cover the full forecast window")

        prepared_future_df = prepared_future_df.merge(
            regressor_dataframe[[timestamp_col, regressor.feature_name]], on=timestamp_col, how="left"
        )

    return prepared_future_df
