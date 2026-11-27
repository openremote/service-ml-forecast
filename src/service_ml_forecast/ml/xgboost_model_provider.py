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
from collections.abc import Sequence
from uuid import UUID

import pandas as pd
from darts import TimeSeries
from darts.models import XGBModel
from darts.models.forecasting.forecasting_model import ForecastingModel
from openremote_client import AssetDatapoint

from service_ml_forecast.ml.backtesting import calculate_backtest_parameters, run_darts_backtest
from service_ml_forecast.ml.calendar_regressors import CALENDAR_COLUMNS, add_calendar_regressors
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
from service_ml_forecast.models.model_config import AssetDatapointFeature, TreeModelConfig
from service_ml_forecast.services.model_storage_service import ModelStorageService

logger = logging.getLogger(__name__)

# Constants
MIN_DATAPOINTS_FOR_TREE_MODEL = 10
MIN_RECOMMENDED_DATAPOINTS = 100
TIMESTAMP_COLUMN_NAME = "timestamp"
VALUE_COLUMN_NAME = "value"


class TreeModelProvider(ModelProvider[ForecastingModel]):
    """Shared Darts provider for tree-regression forecasting models."""

    model_class: type[ForecastingModel] = XGBModel
    model_name = "tree model"

    def __init__(self, config: TreeModelConfig) -> None:
        self.config = config
        self.model_storage_service = ModelStorageService()

    def train_model(self, training_dataset: TrainingDataSet) -> ForecastingModel | None:
        """Train a Darts tree model on the provided dataset.

        Args:
            training_dataset: Dataset containing target and optional regressor data

        Returns:
            Trained model or None if training fails
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

        if dataframe.empty or len(dataframe) < MIN_DATAPOINTS_FOR_TREE_MODEL:
            logger.error(
                "Insufficient training data for model %s: %s aligned rows; require %s at %s",
                self.config.id,
                len(dataframe),
                MIN_DATAPOINTS_FOR_TREE_MODEL,
                self.config.forecast_frequency,
            )
            return None
        elif len(dataframe) < MIN_RECOMMENDED_DATAPOINTS:
            logger.warning(
                f"Limited training data: {len(dataframe)} points (recommended: {MIN_RECOMMENDED_DATAPOINTS})"
            )

        # Check the window before Darts expands integer lags into a large list.
        # This is a necessary lower bound; Darts still checks exact fit coverage.
        lookback = max(
            max(-min(value), 0) if isinstance(value, list) else value or 0
            for value in (self.config.lags, self.config.lags_past_covariates)
        )
        future_lags = self.config.lags_future_covariates
        future_end = future_lags if isinstance(future_lags, int) else max(future_lags or [0])
        required_rows = max(3, lookback + max(self.config.output_chunk_length, future_end + 1))
        if len(dataframe) < required_rows:
            raise ValueError(
                f"Tree lag/chunk window requires at least {required_rows} aligned training rows; "
                f"only {len(dataframe)} are available. Reduce lags/chunk length or provide more history."
            )

        if self.config.calendar_timezone:
            dataframe = add_calendar_regressors(dataframe, TIMESTAMP_COLUMN_NAME, self.config.calendar_timezone)

        target_series = TimeSeries.from_dataframe(
            dataframe, time_col=TIMESTAMP_COLUMN_NAME, value_cols=[VALUE_COLUMN_NAME]
        )

        past_cols, future_cols = self._training_covariate_columns(training_dataset)
        past_covariates = (
            TimeSeries.from_dataframe(dataframe, time_col=TIMESTAMP_COLUMN_NAME, value_cols=past_cols)
            if past_cols
            else None
        )
        future_covariates = (
            TimeSeries.from_dataframe(dataframe, time_col=TIMESTAMP_COLUMN_NAME, value_cols=future_cols)
            if future_cols
            else None
        )

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

        if self.config.lags_future_covariates is not None or self.config.calendar_timezone:
            model_kwargs["lags_future_covariates"] = (
                self.config.lags_future_covariates if self.config.lags_future_covariates is not None else [0]
            )

        if self.config.lags_past_covariates is not None:
            model_kwargs["lags_past_covariates"] = self.config.lags_past_covariates

        model = self.model_class(**model_kwargs)

        # Fit model with appropriate covariates
        fit_kwargs = {"series": target_series}
        if future_covariates is not None:
            fit_kwargs["future_covariates"] = future_covariates
        if past_covariates is not None:
            fit_kwargs["past_covariates"] = past_covariates

        model.fit(**fit_kwargs)

        return model

    def _training_covariate_columns(self, dataset: TrainingDataSet) -> tuple[list[str], list[str]]:
        names = [item.feature_name for item in dataset.covariates or []]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate covariate input names")
        features = [*(self.config.past_covariates or []), *(self.config.future_covariates or [])]

        def columns(group: Sequence[AssetDatapointFeature]) -> list[str]:
            resolved = []
            for feature in group:
                name = feature.get_feature_name()
                # Standalone provider callers may use attribute-only names.
                if name not in names and sum(f.attribute_name == feature.attribute_name for f in features) == 1:
                    name = feature.attribute_name
                if name not in names:
                    raise ValueError(f"Missing training covariate input: {feature.get_feature_name()}")
                resolved.append(name)
            return resolved

        past = columns(self.config.past_covariates or [])
        future = columns(self.config.future_covariates or [])
        if past and self.config.lags_past_covariates is None:
            raise ValueError("Historical inputs require past-covariate lags")
        if future and self.config.lags_future_covariates is None and not self.config.calendar_timezone:
            raise ValueError("Future inputs require future-covariate lags")
        if not features:  # Preserve standalone provider use with explicit lag settings.
            past = names if self.config.lags_past_covariates is not None else []
            future = names if self.config.lags_future_covariates is not None or self.config.calendar_timezone else []
        if self.config.calendar_timezone:
            future = [*future, *CALENDAR_COLUMNS]
        return past, future

    def load_model(self, model_id: UUID) -> ForecastingModel:
        """Load a trained tree model from storage.

        Args:
            model_id: UUID of the model to load

        Returns:
            Loaded model instance
        """
        return self.model_storage_service.load(self.model_class, model_id, self.config)

    def save_model(self, model: ForecastingModel) -> None:
        """Save a trained tree model to storage.

        Args:
            model: Trained model to save
        """
        self.model_storage_service.save(model, self.config.id, self.config)

    def generate_forecast(self, forecast_dataset: ForecastDataSet | None = None) -> ForecastResult:
        """Generate a forecast using the trained tree model.

        Args:
            forecast_dataset: Optional dataset containing regressor data for forecasting

        Returns:
            ForecastResult containing predicted datapoints
        """
        return self._predict(self.load_model(self.config.id), forecast_dataset, self.config.forecast_periods)

    def _predict(
        self,
        model: ForecastingModel,
        forecast_dataset: ForecastDataSet | None,
        periods: int,
    ) -> ForecastResult:
        predict_kwargs = {"n": periods}
        if model.training_series is None:
            raise ValueError("Stored model has no training cutoff; retrain before forecasting")
        first = model.training_series.end_time() + pd.Timedelta(self.config.forecast_frequency)
        # A calendar feature is future-known; an observed input is not. Never
        # align both groups over one shared historical/future window.
        for role, stored, lag_start in [
            ("past", model.past_covariate_series, 2),
            ("future", model.future_covariate_series, 4),
        ]:
            if stored is None:
                continue
            columns = list(stored.components)
            if role == "future" and any(column.startswith("past_") for column in columns):
                raise ValueError("Stored model mixes historical and future input roles; retrain this configuration")
            minimum, maximum = model.extreme_lags[lag_start : lag_start + 2]
            last_step = maximum + max(0, periods - self.config.output_chunk_length)
            # Keep the existing complete-horizon requirement for future inputs.
            if role == "future":
                minimum = min(0, minimum)
                last_step = max(periods - 1, last_step)
            base = pd.DataFrame(
                {
                    TIMESTAMP_COLUMN_NAME: pd.date_range(
                        start=first + minimum * pd.Timedelta(self.config.forecast_frequency),
                        periods=last_step - minimum + 1,
                        freq=self.config.forecast_frequency,
                    )
                }
            )
            supplied = (
                {item.feature_name: item for item in forecast_dataset.covariates or []} if forecast_dataset else {}
            )
            if forecast_dataset and len(supplied) != len(forecast_dataset.covariates or []):
                raise ValueError("Duplicate covariate input names")
            needed = [column for column in columns if column not in CALENDAR_COLUMNS]
            missing = [column for column in needed if column not in supplied]
            if missing:
                raise ValueError(f"Missing {role} covariate input: {', '.join(missing)}")
            selected = ForecastDataSet(covariates=[supplied[column] for column in needed])
            prepared = align_forecast_data(base, selected, self.config.forecast_frequency, self.config.id)
            if self.config.calendar_timezone and role == "future":
                prepared = add_calendar_regressors(prepared, TIMESTAMP_COLUMN_NAME, self.config.calendar_timezone)
            predict_kwargs[role + "_covariates"] = TimeSeries.from_dataframe(
                prepared,
                time_col=TIMESTAMP_COLUMN_NAME,
                value_cols=columns,
                freq=self.config.forecast_frequency,
            )

        forecast_series = model.predict(**predict_kwargs)
        datapoints = _convert_darts_forecast_to_datapoints(forecast_series.to_dataframe())

        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=datapoints,
        )

    def evaluate_model(self, model: ForecastingModel) -> EvaluationMetrics | None:
        """Evaluate a tree model using Darts backtesting.

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


class XGBoostModelProvider(TreeModelProvider):
    """XGBoost model provider using Darts."""

    model_class = XGBModel
    model_name = "XGBoost"


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
        millis = row[timestamp_col].value // 1_000_000
        datapoints.append(AssetDatapoint(x=millis, y=row[value_col]))

    return datapoints
