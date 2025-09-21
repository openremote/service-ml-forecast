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
from dataclasses import dataclass
from typing import Any

import numpy as np
from darts import TimeSeries
from darts.models.forecasting.forecasting_model import ForecastingModel

from service_ml_forecast.ml.evaluation_metrics import EvaluationMetrics

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Configuration for walk-forward backtesting."""
    start: int                      # First evaluation point (training window size)
    stride: int                     # Step size between evaluations
    forecast_horizon: int           # Number of periods to forecast
    retrain: bool = True           # Retrain at each step (standard practice)
    last_points_only: bool = False # Use full forecast horizon (not just last point)


def calculate_backtest_parameters(
    series_length: int,
    forecast_periods: int,
    min_train_size: int | None = None,
    stride: int | None = None,
) -> BacktestConfig | None:
    """
    Calculate walk-forward cross-validation parameters.
    
    This follows the standard approach from forecasting literature:
    1. Reserve sufficient data for initial training (typically 70-80% or minimum viable)
    2. Walk forward through remaining data with retraining
    3. Use stride = forecast_horizon for non-overlapping evaluation (standard)
    
    Args:
        series_length: Total length of time series
        forecast_periods: Forecast horizon (h-step ahead)
        min_train_size: Minimum training window (default: max(50, 0.7 * series_length))
        stride: Step size between evaluations (default: forecast_periods)
        
    Returns:
        BacktestConfig for walk-forward evaluation
    """
    if series_length <= 0:
        logger.warning("Invalid series length for backtesting")
        return None
    if forecast_periods < 1:
        logger.warning("Invalid forecast horizon")
        return None
    
    # use 70% for initial training, minimum 50 observations
    if min_train_size is None:
        min_train_size = max(50, int(0.7 * series_length))
    
    # Standard stride: forecast horizon (non-overlapping evaluations)
    if stride is None:
        stride = forecast_periods
        
    # Ensure sufficient data for at least one evaluation
    min_required = min_train_size + forecast_periods
    if series_length < min_required:
        logger.warning(
            f"Insufficient data: need ≥{min_required} points (train={min_train_size} + horizon={forecast_periods}), got {series_length}"
        )
        return None
    
    # Calculate number of evaluation windows
    available_for_eval = series_length - min_train_size
    num_evaluations = max(1, available_for_eval // stride)
    
    logger.info(
        f"Walk-forward CV: train_start={min_train_size}, evaluations={num_evaluations}, "
        f"stride={stride}, horizon={forecast_periods} (using {100*available_for_eval/series_length:.1f}% for evaluation)"
    )
    
    return BacktestConfig(
        start=min_train_size,
        stride=stride,
        forecast_horizon=forecast_periods,
        retrain=True,
        last_points_only=False
    )


def run_darts_backtest(
    model: ForecastingModel,
    backtest_config: BacktestConfig,
) -> EvaluationMetrics:
    """
    Run walk-forward cross-validation.
    
    This implements the standard approach from forecasting literature:
    1. Start with minimum training window
    2. Forecast next h periods
    3. Move forward by stride, retrain on expanded window
    4. Repeat until end of series
    5. Aggregate all forecasts for global metrics
    """
    series = getattr(model, "training_series", None)
    future_covariates = getattr(model, "future_covariate_series", None)
    
    if series is None:
        raise ValueError("Model has no training data for backtesting")
    
    # Use Darts' historical_forecasts
    forecasts = model.historical_forecasts(
        series=series,
        future_covariates=future_covariates,
        start=backtest_config.start,
        forecast_horizon=backtest_config.forecast_horizon,
        stride=backtest_config.stride,
        retrain=backtest_config.retrain,
        last_points_only=backtest_config.last_points_only,
    )
    
    # Collect all forecast vs actual pairs
    y_true_all: list[np.ndarray[Any, Any]] = []
    y_pred_all: list[np.ndarray[Any, Any]] = []
    
    # Diagnostic tracking
    window_errors = []
    
    for i, forecast in enumerate(forecasts):
        # Get corresponding actual values
        actual_slice = series.slice(forecast.start_time(), forecast.end_time())
        
        if len(actual_slice) != len(forecast):
            logger.debug(f"Window {i}: length mismatch (actual={len(actual_slice)}, forecast={len(forecast)})")
            continue  # Skip if lengths don't match
            
        y_true = actual_slice.values().flatten()
        y_pred = forecast.values().flatten()
        
        # Only include finite values
        mask = np.isfinite(y_true) & np.isfinite(y_pred)
        if np.any(mask):
            y_true_masked = y_true[mask]
            y_pred_masked = y_pred[mask]
            y_true_all.append(y_true_masked)
            y_pred_all.append(y_pred_masked)
            
            # Track per-window diagnostics
            window_mae = np.mean(np.abs(y_true_masked - y_pred_masked))
            window_mean_actual = np.mean(y_true_masked)
            window_mean_pred = np.mean(y_pred_masked)
            window_errors.append({
                'window': i,
                'mae': window_mae,
                'mean_actual': window_mean_actual,
                'mean_pred': window_mean_pred,
                'bias': window_mean_pred - window_mean_actual
            })
    
    if not y_true_all:
        logger.warning("No valid forecast-actual pairs collected")
        return EvaluationMetrics(rmse=0.0, mae=0.0, mape=0.0, r2=0.0)
    
    # Compute global metrics across all forecasts
    y_true_concat = np.concatenate(y_true_all)
    y_pred_concat = np.concatenate(y_pred_all)
    
    # Additional diagnostics for massive errors
    logger.info(f"Data range analysis:")
    logger.info(f"  Actual values - min: {np.min(y_true_concat):.1f}, max: {np.max(y_true_concat):.1f}, mean: {np.mean(y_true_concat):.1f}")
    logger.info(f"  Predicted values - min: {np.min(y_pred_concat):.1f}, max: {np.max(y_pred_concat):.1f}, mean: {np.mean(y_pred_concat):.1f}")
    
    # Check for extreme outliers or zeros causing MAPE issues
    near_zero_actuals = np.sum(np.abs(y_true_concat) < 1.0)
    if near_zero_actuals > 0:
        logger.warning(f"Found {near_zero_actuals}/{len(y_true_concat)} actual values near zero (< 1.0) - this inflates MAPE")
    
    rmse, mae, mape, r2 = _compute_metrics(y_true_concat, y_pred_concat)
    
    n_points = len(y_true_concat)
    n_windows = len(forecasts)
    
    # Diagnostic analysis
    if window_errors:
        worst_windows = sorted(window_errors, key=lambda x: x['mae'], reverse=True)[:3]
        best_windows = sorted(window_errors, key=lambda x: x['mae'])[:3]
        avg_bias = np.mean([w['bias'] for w in window_errors])
        
        logger.info(f"Diagnostic analysis:")
        logger.info(f"  Average bias: {avg_bias:.2f} (positive = over-prediction)")
        logger.info(f"  Worst 3 windows: {[(w['window'], f'{w['mae']:.1f}') for w in worst_windows]}")
        logger.info(f"  Best 3 windows: {[(w['window'], f'{w['mae']:.1f}') for w in best_windows]}")
        
        # Check for systematic issues
        high_error_windows = [w for w in window_errors if w['mae'] > mae * 1.5]
        if len(high_error_windows) > len(window_errors) * 0.3:
            logger.warning(f"Performance issue: {len(high_error_windows)}/{len(window_errors)} windows have >1.5x average error")
    
    logger.info(
        f"Walk-forward CV results: {n_points} points across {n_windows} windows — "
        f"RMSE: {rmse:.4f}, MAE: {mae:.4f}, MAPE: {mape:.4f}, R²: {r2:.4f}"
    )
    
    return EvaluationMetrics(rmse=rmse, mae=mae, mape=mape, r2=r2)


def _compute_metrics(y_true: np.ndarray[Any, Any], y_pred: np.ndarray[Any, Any]) -> tuple[float, float, float, float]:
    """
    Compute standard forecasting metrics.
    
    Returns: (RMSE, MAE, MAPE, R²)
    """
    if len(y_true) == 0 or len(y_pred) == 0:
        return 0.0, 0.0, 0.0, 0.0
    
    errors = y_true - y_pred
    abs_errors = np.abs(errors)
    
    # Root Mean Square Error
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    
    # Mean Absolute Error  
    mae = float(np.mean(abs_errors))
    
    # Mean Absolute Percentage Error (as decimal)
    # Use small epsilon to avoid division by zero
    epsilon = 1e-8
    mape = float(np.mean(abs_errors / np.maximum(np.abs(y_true), epsilon)))
    
    # Coefficient of Determination (R²)
    ss_res = np.sum(errors ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0
    
    return rmse, mae, mape, r2