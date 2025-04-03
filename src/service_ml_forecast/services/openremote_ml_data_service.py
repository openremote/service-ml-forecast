import logging

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.models.feature_data_wrappers import FeatureDatapoints, ForecastFeatureSet, TrainingFeatureSet
from service_ml_forecast.models.model_config import ModelConfig
from service_ml_forecast.util.time_util import TimeUtil

logger = logging.getLogger(__name__)


class OpenRemoteMLDataService:
    """Service for ML formatted data from OpenRemote."""

    def __init__(self, client: OpenRemoteClient):
        self.client = client

    def write_predicted_datapoints(self, config: ModelConfig, asset_datapoints: list[AssetDatapoint]) -> bool:
        """Write the predicted datapoints to OpenRemote.

        Args:
            config: The model configuration
            asset_datapoints: The predicted datapoints

        Returns:
            bool: True if the datapoints were written successfully, False otherwise
        """

        return self.client.write_predicted_datapoints(
            config.target.asset_id,
            config.target.attribute_name,
            asset_datapoints,
        )

    def get_training_feature_set(self, config: ModelConfig) -> TrainingFeatureSet | None:
        """Get the training feature set for a given model configuration.

        Args:
            config: The model configuration

        Returns:
            TrainingFeatureSet | None: The training feature set
            None if unable to retrieve target feature datapoints
        """

        target_feature_datapoints: FeatureDatapoints

        # Retrieve target feature datapoints from OpenRemote
        datapoints = self.client.retrieve_historical_datapoints(
            config.target.asset_id,
            config.target.attribute_name,
            config.target.cutoff_timestamp,
            TimeUtil.get_timestamp_ms(),
        )

        if datapoints is None:
            logger.error(f"Unable to retrieve target feature datapoints for {config.id}")
            return None

        target_feature_datapoints = FeatureDatapoints(
            attribute_name=config.target.attribute_name,
            datapoints=datapoints,
        )

        regressors: list[FeatureDatapoints] = []

        # Retrieve regressor historical feature datapoints if configured
        if config.regressors is not None:
            for regressor in config.regressors:
                regressor_datapoints = self.client.retrieve_historical_datapoints(
                    regressor.asset_id,
                    regressor.attribute_name,
                    regressor.cutoff_timestamp,
                    TimeUtil.get_timestamp_ms(),
                )

                if regressor_datapoints is None:
                    logger.error(
                        f"Unable to retrieve regressor datapoints for {config.id}"
                        f" - {regressor.asset_id} - {regressor.attribute_name}",
                    )
                    return None  # Early return if unable to retrieve regressor datapoints

                regressors.append(
                    FeatureDatapoints(
                        attribute_name=regressor.attribute_name,
                        datapoints=regressor_datapoints,
                    ),
                )

        training_feature_set = TrainingFeatureSet(
            target=target_feature_datapoints,
            regressors=regressors if regressors else None,
        )

        return training_feature_set

    def get_forecast_feature_set(self, config: ModelConfig) -> ForecastFeatureSet | None:
        """Get the forecast feature set for a given model configuration.

        Args:
            config: The model configuration

        Returns:
            ForecastFeatureSet | None: The forecast feature set
            None if no regressors are configured or if unable to retrieve regressor datapoints
        """

        # Return None if no regressors are configured
        # Don't need to include a feature set if no regressors are configured for forecasting
        if config.regressors is None:
            return None

        regressors: list[FeatureDatapoints] = []

        # Retrieve regressor predicted feature datapoints if configured
        if config.regressors is not None:
            for regressor in config.regressors:
                regressor_datapoints = self.client.retrieve_predicted_datapoints(
                    regressor.asset_id,
                    regressor.attribute_name,
                    regressor.cutoff_timestamp,
                    TimeUtil.pd_future_timestamp(config.forecast_periods, config.forecast_frequency),
                )

                if regressor_datapoints is None:
                    logger.error(
                        f"Unable to retrieve regressor datapoints for {config.id} "
                        f"- {regressor.asset_id} - {regressor.attribute_name}",
                    )
                    return None  # Early return if unable to retrieve regressor datapoints

                regressors.append(
                    FeatureDatapoints(
                        attribute_name=regressor.attribute_name,
                        datapoints=regressor_datapoints,
                    ),
                )

        forecast_feature_set = ForecastFeatureSet(
            regressors=regressors,
        )

        return forecast_feature_set
