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
from typing import Protocol, TypeVar
from uuid import UUID

import pandas as pd

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.models.feature_data_wrappers import ForecastDataSet, ForecastResult, TrainingDataSet

logger = logging.getLogger(__name__)

# Constants
MIN_UNIQUE_TIMESTAMPS_FOR_RESAMPLE = 2

# Type variables
ModelType = TypeVar("ModelType")


class ModelProvider(Protocol[ModelType]):
    """Base protocol for all ML models.

    This protocol defines the methods that all ML model providers must implement.
    """

    def train_model(self, training_dataset: TrainingDataSet) -> ModelType | None:
        """Train the model on the training dataset.

        Args:
            training_dataset: The training dataset to train the model on.

        Returns:
            The trained model or None if the model could not be trained.
        """

    def generate_forecast(self, forecast_dataset: ForecastDataSet | None = None) -> ForecastResult:
        """Generate a forecast for the given forecast dataset.

        Args:
            forecast_dataset: any additional datapoints (e.g. regressors) to use for forecasting

        Returns:
            The forecast result or None if the forecast could not be generated.
        """

    def save_model(self, model: ModelType) -> None:
        """Save the trained model via the model storage service.

        Args:
            model: The trained model to save.
        """

    def load_model(self, model_config_id: UUID) -> ModelType:
        """Load the trained model via the model storage service.

        Args:
            model_config_id: The ID of the model config to load the model for.

        Returns:
            The loaded model, or None if the model could not be loaded.
        """


# Data processing helper functions


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

    # Sort the dataframe by timestamp
    timeseries_df = timeseries_df.sort_values(time_col_name)

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

    # Check if interpolation introduced NaNs
    if df_filled[value_col_name].isna().any():
        logger.warning(
            f"Interpolation resulted in NaNs for series '{value_col_name}' with frequency '{frequency}'. "
            f"This might indicate insufficient data or gaps larger than the interpolation limit."
        )

    return df_filled.reset_index()
