import logging
from typing import cast
from uuid import UUID

import pandas as pd
from openremote_client import AssetDatapoint
from pandas import DataFrame
from sklearn.impute import KNNImputer

from service_ml_forecast.models.feature_data_wrappers import ForecastDataSet, TrainingDataSet

logger = logging.getLogger(__name__)

# Constants
MIN_UNIQUE_TIMESTAMPS_FOR_RESAMPLE = 2


def convert_datapoints_to_dataframe(
    datapoints: list[AssetDatapoint],
    time_col_name: str,
    value_col_name: str,
) -> pd.DataFrame:
    """Converts a list of AssetDatapoint objects to a Pandas DataFrame.

    Args:
        datapoints: List of AssetDatapoint objects.
        time_col_name: Name for the time column
        value_col_name: Name for the value column

    Returns:
        A Pandas DataFrame with time and value columns, sorted by time.
    """
    if not datapoints:
        return pd.DataFrame(columns=[time_col_name, value_col_name])

    timeseries_df = pd.DataFrame([{time_col_name: point.x, value_col_name: point.y} for point in datapoints])

    # Convert the millis timestamp to datetime objects
    timeseries_df[time_col_name] = pd.to_datetime(timeseries_df[time_col_name], unit="ms")

    # Sort and aggregate duplicate timestamps
    timeseries_df = timeseries_df.sort_values(time_col_name)
    timeseries_df = timeseries_df.groupby(time_col_name, as_index=False).mean()

    return timeseries_df


def resample_and_interpolate(
    datapoints: list[AssetDatapoint],
    frequency: str,
    time_col_name: str,
    value_col_name: str,
) -> pd.DataFrame | None:
    """Resamples and interpolates a time series represented by AssetDatapoints.

    Args:
        datapoints: List of AssetDatapoint objects.
        frequency: The target frequency string (e.g., 'H', '15T').
        time_col_name: Name for the time column
        value_col_name: Name for the value column

    Returns:
        A Pandas DataFrame resampled to the specified frequency with interpolated values,
        or None if input is empty. Returns the original data (potentially aggregated if duplicate timestamps)
        if resampling fails or is not possible (e.g., < 2 unique timestamps).
    """
    if not datapoints:
        return None

    timeseries_df = convert_datapoints_to_dataframe(
        datapoints, time_col_name=time_col_name, value_col_name=value_col_name
    )

    if timeseries_df[time_col_name].nunique() < MIN_UNIQUE_TIMESTAMPS_FOR_RESAMPLE:
        logger.warning(
            f"Cannot resample/interpolate series '{value_col_name}' with frequency '{frequency}' "
            f"as it has less than {MIN_UNIQUE_TIMESTAMPS_FOR_RESAMPLE} unique timestamps."
        )
        # If only one point, return frame with that point
        if timeseries_df.shape[0] == 1:
            return timeseries_df
        # If multiple points but only one unique timestamp, aggregate (mean) and return
        else:
            df_agg = timeseries_df.groupby(time_col_name).mean().reset_index()
            return df_agg

    timeseries_df = timeseries_df.set_index(time_col_name)

    # Ensure the index is sorted by time
    if not timeseries_df.index.is_monotonic_increasing:
        logger.warning(f"Data for {value_col_name} is not sorted by time. Sorting before resampling.")
        timeseries_df = timeseries_df.sort_index()

    # Resample, interpolate temporally, fill edges
    try:
        df_resampled = timeseries_df.resample(frequency).mean()  # resample to target frequency
        df_interpolated = df_resampled.interpolate(method="time")  # interpolate by time
        df_filled = df_interpolated.ffill().bfill()  # fill edges
    except ValueError as e:
        logger.error(
            f"Error resampling/interpolating series '{value_col_name}' with frequency '{frequency}': {e}. "
            f"Returning original sorted data."
        )
        # Fallback: Return original sorted data if resampling fails
        return timeseries_df.reset_index()

    # Check if interpolation still has NaNs
    if df_filled[value_col_name].isna().any():
        logger.error(
            f"Interpolation still has NaNs for series '{value_col_name}' with frequency '{frequency}'. "
            f"This indicates a critical data processing issue."
        )

    return df_filled.reset_index()


def align_training_data(
    training_dataset: TrainingDataSet, frequency: str, timestamp_col: str = "timestamp", value_col: str = "value"
) -> DataFrame:
    """Prepare training dataframe with aligned timestamps for target and optional regressors.

    This function resamples all data to a consistent frequency and aligns timestamps
    across target and regressor data, ensuring a clean dataset for model training.

    Args:
        training_dataset: Training dataset containing target and optional regressors
        frequency: Target frequency string (e.g., 'H', '15T', 'D')
        timestamp_col: Name for the timestamp column in output DataFrame
        value_col: Name for the target value column in output DataFrame

    Returns:
        Aligned DataFrame with target and regressor data
    """
    target = training_dataset.target
    regressors = training_dataset.regressors

    dataframes = []

    # Resample and interpolate target data
    target_df = resample_and_interpolate(
        target.datapoints,
        frequency,
        time_col_name=timestamp_col,
        value_col_name=value_col,
    )
    if target_df is None:
        logger.error("Cannot prepare training data: Target data resampling resulted in None.")
        return DataFrame(columns=[timestamp_col, value_col])

    dataframes.append(target_df)
    target_len = len(target_df)
    logger.info(f"Target data resampled to {frequency} frequency, resulting in {target_len} datapoints.")

    # Resample and interpolate regressor data if they are provided
    if regressors is not None:
        for regressor in regressors:
            regressor_df = resample_and_interpolate(
                regressor.datapoints,
                frequency,
                time_col_name=timestamp_col,
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
    min_date = max(df[timestamp_col].min() for df in dataframes)
    max_date = min(df[timestamp_col].max() for df in dataframes)
    logger.info(f"Common date range for training data: {min_date} to {max_date}")

    # Create a full index for the common date range
    full_index = pd.date_range(start=min_date, end=max_date, freq=frequency)

    # Start with target data
    result = target_df[(target_df[timestamp_col] >= min_date) & (target_df[timestamp_col] <= max_date)].copy()

    # Merge the regressors if they are provided
    if regressors is not None:
        for i, _regressor in enumerate(regressors):
            regressor_df = dataframes[i + 1]  # note +1 because target_df is first component
            if regressor_df is not None and not regressor_df.empty:
                result = result.merge(regressor_df, on=timestamp_col, how="left")

    # Update the index and reindex to the full index
    result = result.set_index(timestamp_col)
    result = result.reindex(full_index)

    numeric_columns = result.select_dtypes(include=["float64", "int64"]).columns

    if len(numeric_columns) > 0 and result[numeric_columns].isna().any().any():
        # Try and apply KNN imputation if we have missing values
        try:
            # Use sensible defaults for KNN imputation, keep small datasets from failing
            n_samples = (result[numeric_columns].notna().any(axis=1)).sum()
            n_neighbors = max(1, min(5, n_samples - 1))
            imputer = KNNImputer(n_neighbors=n_neighbors)
            result[numeric_columns] = imputer.fit_transform(result[numeric_columns])
            logger.info(f"Applied KNN imputation with {n_neighbors} neighbors for missing values")
        except Exception as e:
            logger.warning(f"KNN imputation failed: {e}. Falling back to time-based interpolation")
            # Fallback to original method (temporal interpolation and forward/backward fill for edges)
            for col in numeric_columns:
                result[col] = result[col].interpolate(method="time", limit_direction="both")
                result[col] = result[col].ffill().bfill()

    # Check for completely empty columns (shouldn't happen)
    for col in numeric_columns:
        if result[col].isna().all():
            raise ValueError(f"All values in column '{col}' are NaN after imputation. Cannot proceed with forecasting.")

    # Reset index and rename it back to the original timestamp column name
    result = result.reset_index().rename(columns={"index": timestamp_col})

    return cast(DataFrame, result)


def align_forecast_data(
    future_df: DataFrame,
    forecast_dataset: ForecastDataSet | None,
    frequency: str,
    config_id: UUID,
    timestamp_col: str = "timestamp",
) -> DataFrame:
    """Prepare forecast dataframe by adding aligned regressor data.

    This function resamples regressor data to match the forecast frequency
    and aligns it with the future dataframe timestamps.

    Args:
        future_df: Base future dataframe with timestamps
        forecast_dataset: Forecast dataset containing optional regressors
        frequency: Target frequency string (e.g., 'H', '15T', 'D')
        config_id: Model configuration ID for logging
        timestamp_col: Name of the timestamp column in the future dataframe

    Returns:
        Future dataframe with aligned regressor data
    """
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
            time_col_name=timestamp_col,
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
        regressor_dataframe = regressor_dataframe.set_index(timestamp_col)
        regressor_dataframe = regressor_dataframe.reindex(
            prepared_future_df[timestamp_col],
            method="ffill",
        )
        regressor_dataframe = regressor_dataframe.reset_index()

        # Check for completely empty regressor columns (should be impossible after ffill)
        if regressor_dataframe[regressor.feature_name].isna().all():
            raise ValueError(
                f"All values in regressor '{regressor.feature_name}' are NaN after resampling. "
                f"Cannot proceed with forecasting."
            )

        # Merge the prepared regressor data with the future dataframe (on the timestamp column)
        prepared_future_df = prepared_future_df.merge(
            regressor_dataframe[[timestamp_col, regressor.feature_name]],
            on=timestamp_col,
            how="left",
        )

    return prepared_future_df
