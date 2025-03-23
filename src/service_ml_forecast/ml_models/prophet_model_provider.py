import logging

import pandas as pd

from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.ml_models.base_model_provider import BaseModelProvider
from service_ml_forecast.schemas.model_config import ProphetModelConfig

logger = logging.getLogger(__name__)


class ProphetModelProvider(BaseModelProvider):
    """Prophet model provider."""

    def __init__(
        self,
        config: ProphetModelConfig,
        openremote_client: OpenRemoteClient,
    ) -> None:
        self.config = config
        self.openremote_client = openremote_client

    def train(self) -> bool:
        logger.info("Training Prophet model")
        self.__get_prophet_dataframe()

        return True

    def __get_prophet_dataframe(self) -> pd.DataFrame:
        target = self.config.predicted_asset_attribute
        regressors = self.config.regressors

        target_data = self.openremote_client.retrieve_historical_datapoints(
            asset_id=target.asset_id,
            attribute_name=target.attribute_name,
            from_timestamp=target.oldest_timestamp,
            to_timestamp=target.newest_timestamp,
        )
        logger.info("Target data: %s", target_data)

        if regressors is None:
            regressors_data = []
        else:
            regressors_data = [
                self.openremote_client.retrieve_historical_datapoints(
                    asset_id=regressor.asset_id,
                    attribute_name=regressor.attribute_name,
                    from_timestamp=regressor.oldest_timestamp,
                    to_timestamp=regressor.newest_timestamp,
                )
                for regressor in regressors
            ]
            logger.info("Regressors data: %s", regressors_data)

        return pd.DataFrame()

    def predict(self) -> bool:
        return True
