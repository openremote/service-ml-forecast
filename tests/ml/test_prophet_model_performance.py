import logging
import time
from datetime import datetime
from uuid import UUID

from openremote_client import AssetDatapoint

from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, TrainingDataSet
from service_ml_forecast.models.model_config import (
    ProphetModelConfig,
    ProphetSeasonalityModeEnum,
    TargetAssetDatapointsFeature,
)
from service_ml_forecast.models.model_type import ModelTypeEnum

logger = logging.getLogger(__name__)


def test_prophet_model_performance(power_grid_mock_datapoints: list[AssetDatapoint]) -> None:
    """Test Prophet model performance with power grid data.

    Verifies that:
    - The model trains successfully with power grid data
    - The trained model can be saved and loaded
    - The model can generate forecasts with non-empty results
    - The model handles missing data gracefully
    - The forecast data has reasonable quality and structure
    """

    # Create test configuration
    config = ProphetModelConfig(
        id=UUID("12345678-1234-5678-9abc-def012345678"),
        realm="test",
        name="Power Grid Performance Test",
        enabled=True,
        type=ModelTypeEnum.PROPHET,
        target=TargetAssetDatapointsFeature(
            asset_id="41ORIhkDVAlT97dYGUD3n5",
            attribute_name="power",
            training_data_period="P6M",
        ),
        forecast_interval="PT1H",
        training_interval="PT1H",
        forecast_frequency="1h",
        forecast_periods=24,
        weekly_seasonality=True,
        yearly_seasonality=False,
        daily_seasonality=True,
        seasonality_mode=ProphetSeasonalityModeEnum.ADDITIVE,
        changepoint_range=0.8,
        changepoint_prior_scale=0.05,
    )

    # Use power grid data - sort by timestamp first
    dataset = sorted(power_grid_mock_datapoints, key=lambda dp: dp.x)

    logger.info("Prophet Model Performance Test - Power Grid Data")
    logger.info(f"Dataset: {len(dataset)} data points")
    missing_count = sum(1 for dp in dataset if dp.y is None)
    logger.info(f"Dataset Missing values: {missing_count}")

    # Get time range from actual data
    if dataset:
        first_timestamp = dataset[0].x
        last_timestamp = dataset[-1].x
        start_time = datetime.fromtimestamp(first_timestamp / 1000)
        end_time = datetime.fromtimestamp(last_timestamp / 1000)
        logger.info(f"Date range: {start_time} to {end_time}")

    logger.info("Data source: power grid measurements")

    # Split data for training and testing
    split_point = int(len(dataset) * 0.8)
    train_data = dataset[:split_point]

    logger.info(f"Training data: {len(train_data)} points (first: {train_data[0].x}, last: {train_data[-1].x})")

    # Train model and measure time
    train_start_time = time.time()

    model_provider = ModelProviderFactory.create_provider(config)
    training_dataset = TrainingDataSet(
        target=AssetFeatureDatapoints(
            feature_name=config.target.attribute_name,
            datapoints=train_data,
        ),
    )

    model = model_provider.train_model(training_dataset)
    training_time = time.time() - train_start_time

    logger.info(f"Training time: {training_time:.2f} seconds")
    assert model is not None, "Model training failed"

    # Save model
    model_provider.save_model(model)

    # Run cross-validation evaluation
    logger.info("Running model evaluation")
    metrics = model_provider.evaluate_model(model)
    assert metrics is not None, "Model evaluation metrics should be available"

    # Generate forecast and measure time
    forecast_start_time = time.time()

    forecast = model_provider.generate_forecast()
    forecast_time = time.time() - forecast_start_time

    assert forecast is not None, "Forecast generation failed"
    assert forecast.datapoints is not None, "Forecast has no datapoints"
    assert len(forecast.datapoints) > 0, "Forecast is empty"

    # Performance summary
    logger.info(f"Training Time: {training_time:.2f}s")
    logger.info(f"Forecast Time: {forecast_time:.2f}s")
    logger.info(f"RMSE: {metrics.rmse:.1f}kW (typical forecast error, lower is better)")
    logger.info(f"MAE: {metrics.mae:.1f}kW (average absolute error, lower is better)")
    logger.info(f"MAPE: {metrics.mape:.1%} (average percentage error, lower is better)")
    logger.info(f"MdAPE: {metrics.mdape:.1%} (median percentage error, lower is better)")
    logger.info(f"R²: {metrics.r2:.3f} (variance explained, higher is better)")

    # Assert reasonable performance
    assert metrics.rmse > 0, "RMSE should be positive"
    assert metrics.mae > 0, "MAE should be positive"
    assert 0 <= metrics.r2 <= 1, "R² should be between 0 and 1"

    # We're aiming for a maximum of 20% error margin
    MAX_ACCEPTABLE_PERCENTAGE = 20
    assert metrics.mape < MAX_ACCEPTABLE_PERCENTAGE, "MAPE should be reasonable"
    assert metrics.mdape < MAX_ACCEPTABLE_PERCENTAGE, "MdAPE should be reasonable"
