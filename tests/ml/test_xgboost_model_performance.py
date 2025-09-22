import logging
import time
from datetime import datetime
from uuid import UUID

from openremote_client import AssetDatapoint

from service_ml_forecast.ml.model_provider_factory import ModelProviderFactory
from service_ml_forecast.models.feature_data_wrappers import AssetFeatureDatapoints, TrainingDataSet
from service_ml_forecast.models.model_config import (
    TargetAssetDatapointsFeature,
    XGBoostModelConfig,
)
from service_ml_forecast.models.model_type import ModelTypeEnum

logger = logging.getLogger(__name__)


def test_xgboost_model_performance(power_grid_mock_datapoints: list[AssetDatapoint]) -> None:
    """Test XGBoost model performance with power grid data."""

    config = XGBoostModelConfig(
        id=UUID("12345678-1234-5678-9abc-def012345678"),
        realm="test",
        name="XGBoost Performance Test",
        enabled=True,
        type=ModelTypeEnum.XGBOOST,
        target=TargetAssetDatapointsFeature(
            asset_id="41ORIhkDVAlT97dYGUD3n5",
            attribute_name="power",
            training_data_period="P6M",
        ),
        forecast_interval="PT1H",
        forecast_frequency="1h",
        forecast_periods=24,
        lags=24,
        output_chunk_length=1,
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )

    dataset = sorted(power_grid_mock_datapoints, key=lambda dp: dp.x)

    logger.info("XGBoost Model Performance Test - Power Grid Data")
    logger.info(f"Dataset: {len(dataset)} data points")

    if dataset:
        first_timestamp = dataset[0].x
        last_timestamp = dataset[-1].x
        start_time = datetime.fromtimestamp(first_timestamp / 1000)
        end_time = datetime.fromtimestamp(last_timestamp / 1000)
        logger.info(f"Date range: {start_time} to {end_time}")

    logger.info("Data source: power grid measurements")

    train_start_time = time.time()

    model_provider = ModelProviderFactory.create_provider(config)
    training_dataset = TrainingDataSet(
        target=AssetFeatureDatapoints(
            feature_name=config.target.attribute_name,
            datapoints=dataset,
        ),
    )

    model = model_provider.train_model(training_dataset)
    training_time = time.time() - train_start_time

    logger.info(f"Training time: {training_time:.2f} seconds")
    assert model is not None, "Model training failed"

    model_provider.save_model(model)

    logger.info("Running backtesting evaluation")
    metrics = model_provider.evaluate_model(model)
    assert metrics is not None, "Backtesting metrics should be available"

    forecast_start_time = time.time()
    forecast = model_provider.generate_forecast()
    forecast_time = time.time() - forecast_start_time

    assert forecast is not None, "Forecast generation failed"
    assert forecast.datapoints is not None, "Forecast has no datapoints"
    assert len(forecast.datapoints) > 0, "Forecast is empty"

    logger.info(f"Training Time: {training_time:.2f}s")
    logger.info(f"Forecast Time: {forecast_time:.2f}s")
    logger.info(f"RMSE: {metrics.rmse:.1f}kW (typical forecast error)")
    logger.info(f"MAE: {metrics.mae:.1f}kW (average absolute error)")
    logger.info(f"MAPE: {metrics.mape:.1%} (average percentage error)")
    logger.info(f"R²: {metrics.r2:.3f} (variance explained)")

    assert metrics.rmse >= 0, "RMSE should be non-negative"
    assert metrics.mae >= 0, "MAE should be non-negative"
    assert metrics.r2 <= 1, "R² should be <= 1 (can be negative if model is worse than mean)"

    MAX_ACCEPTABLE_PERCENTAGE = 30
    assert metrics.mape < MAX_ACCEPTABLE_PERCENTAGE, "MAPE should be reasonable"
