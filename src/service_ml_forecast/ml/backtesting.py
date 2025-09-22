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

"""Walk-forward backtesting for time series model evaluation."""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from darts.models.forecasting.forecasting_model import ForecastingModel

from service_ml_forecast.ml.evaluation_metrics import EvaluationMetrics

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Configuration for walk-forward backtesting.

    Args:
        start: Start index.
        stride: Stride.
        forecast_horizon: Forecast horizon.
        retrain: Whether to retrain the model.
        last_points_only: Whether to use only the last points.
    """

    start: int
    stride: int
    forecast_horizon: int
    retrain: bool = True
    last_points_only: bool = False


def calculate_backtest_parameters(
    series_length: int,
    forecast_periods: int,
    min_train_size: int | None = None,
    stride: int | None = None,
) -> BacktestConfig | None:
    """Calculate walk-forward cross-validation parameters.

    Args:
        series_length: Length of the time series.
        forecast_periods: Forecast horizon.
        min_train_size: Minimum training size.
        stride: Stride.
    """
    if series_length <= 0 or forecast_periods < 1:
        logger.warning("Invalid series length or forecast horizon")
        return None

    # Default: 70% for training, minimum 50 observations
    if min_train_size is None:
        min_train_size = max(50, int(0.7 * series_length))

    # Default: non-overlapping evaluation windows
    if stride is None:
        stride = forecast_periods

    # Check sufficient data
    min_required = min_train_size + forecast_periods
    if series_length < min_required:
        logger.warning(f"Insufficient data: need ≥{min_required}, got {series_length}")
        return None

    available_for_eval = series_length - min_train_size
    num_evaluations = max(1, available_for_eval // stride)

    logger.info(f"Backtesting: {num_evaluations} windows, stride={stride}, horizon={forecast_periods}")

    return BacktestConfig(
        start=min_train_size,
        stride=stride,
        forecast_horizon=forecast_periods,
    )


def run_darts_backtest(
    model: ForecastingModel,
    backtest_config: BacktestConfig,
) -> EvaluationMetrics:
    """Run walk-forward cross-validation using Darts.

    Args:
        model: The Darts forecasting model to evaluate.
        backtest_config: Configuration for walk-forward cross-validation.
    """
    series = getattr(model, "training_series", None)
    future_covariates = getattr(model, "future_covariate_series", None)

    if series is None:
        raise ValueError("Model has no training data for backtesting")

    forecasts = model.historical_forecasts(
        series=series,
        future_covariates=future_covariates,
        start=backtest_config.start,
        forecast_horizon=backtest_config.forecast_horizon,
        stride=backtest_config.stride,
        retrain=backtest_config.retrain,
        last_points_only=backtest_config.last_points_only,
    )

    # Collect forecast vs actual pairs
    y_true_all: list[np.ndarray[Any, Any]] = []
    y_pred_all: list[np.ndarray[Any, Any]] = []

    for forecast in forecasts:
        actual_slice = series.slice(forecast.start_time(), forecast.end_time())

        if len(actual_slice) != len(forecast):
            continue

        y_true = actual_slice.values().flatten()
        y_pred = forecast.values().flatten()

        mask = np.isfinite(y_true) & np.isfinite(y_pred)
        if np.any(mask):
            y_true_all.append(y_true[mask])
            y_pred_all.append(y_pred[mask])

    if not y_true_all:
        logger.warning("No valid forecast pairs collected")
        return EvaluationMetrics(rmse=0.0, mae=0.0, mape=0.0, r2=0.0)

    y_true_concat = np.concatenate(y_true_all)
    y_pred_concat = np.concatenate(y_pred_all)

    rmse, mae, mape, r2 = _compute_metrics(y_true_concat, y_pred_concat)

    logger.info(
        f"Backtest results: {len(y_true_concat)} points, {len(forecasts)} windows — "
        f"RMSE: {rmse:.3f}, MAE: {mae:.3f}, MAPE: {mape:.3f}, R²: {r2:.3f}"
    )

    return EvaluationMetrics(rmse=rmse, mae=mae, mape=mape, r2=r2)


def _compute_metrics(y_true: np.ndarray[Any, Any], y_pred: np.ndarray[Any, Any]) -> tuple[float, float, float, float]:
    """Compute RMSE, MAE, MAPE, R².

    Args:
        y_true: True values.
        y_pred: Predicted values.
    """
    if len(y_true) == 0 or len(y_pred) == 0:
        return 0.0, 0.0, 0.0, 0.0

    errors = y_true - y_pred
    abs_errors = np.abs(errors)

    rmse = float(np.sqrt(np.mean(errors**2)))
    mae = float(np.mean(abs_errors))
    mape = float(np.mean(abs_errors / np.maximum(np.abs(y_true), 1e-8)))

    ss_res = np.sum(errors**2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    return rmse, mae, mape, r2
