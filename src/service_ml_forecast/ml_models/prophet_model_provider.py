import logging

import pandas as pd
from prophet import Prophet  # type: ignore  # noqa: PGH003 # provides no type hints
from prophet.serialize import model_from_json, model_to_json  # type: ignore  # noqa: PGH003 # provides no type hints

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
from service_ml_forecast.ml_models.model_provider import ModelProvider
from service_ml_forecast.ml_models.model_util import DatapointWrapper, load_model, save_model
from service_ml_forecast.schemas.model_config import ProphetModelConfig

logger = logging.getLogger(__name__)


class ProphetModelProvider(ModelProvider):
    """Prophet model provider."""

    def __init__(
        self,
        config: ProphetModelConfig,
        openremote_client: OpenRemoteClient,
    ) -> None:
        self.config = config
        self.openremote_client = openremote_client

    def train_model(self) -> bool:
        dataframe = self.__get_dataframe()
        if dataframe is None:
            logger.error("Failed to obtain valid dataframe for training the Prophet model")
            return False

        # Train the Prophet model
        model = Prophet()
        model.fit(dataframe)

        # Save the trained model
        if not save_model(model_to_json(model), f"{self.config.id}.json"):
            logger.error(f"Failed to save trained model for {self.config.id}")
            return False

        return True

    def __get_dataframe(self) -> pd.DataFrame | None:
        """Retrieve the target and regressors data from the OpenRemote client and convert it to a Prophet dataframe."""
        target = self.config.predicted_asset_attribute
        regressor_list = self.config.regressors

        regressors_data_list: list[DatapointWrapper] | None = None

        target_data = DatapointWrapper(
            attribute_name=target.attribute_name,
            datapoints=self.openremote_client.retrieve_historical_datapoints(
                asset_id=target.asset_id,
                attribute_name=target.attribute_name,
                from_timestamp=target.cutoff_timestamp,
                to_timestamp=(int(pd.Timestamp.now().timestamp())) * 1000,
            ),
        )

        if (target_data.datapoints is None) or (len(target_data.datapoints) == 0):
            logger.error(f"No target datapoints are available for {target.attribute_name}")
            return None

        if regressor_list is not None:
            regressors_data_list = [
                DatapointWrapper(
                    attribute_name=regressor.attribute_name,
                    datapoints=self.openremote_client.retrieve_historical_datapoints(
                        asset_id=regressor.asset_id,
                        attribute_name=regressor.attribute_name,
                        from_timestamp=regressor.cutoff_timestamp,
                        to_timestamp=(int(pd.Timestamp.now().timestamp())) * 1000,
                    ),
                )
                for regressor in regressor_list
            ]

            for regressor_data in regressors_data_list:
                if (regressor_data.datapoints is None) or (len(regressor_data.datapoints) == 0):
                    logger.error(f"No regressor datapoints are available for {regressor_data.attribute_name}")
                    return None

        # Convert the target and regressors data to a Prophet dataframe
        prophet_dataframe = self.__create_prophet_dataframe(target_data, regressors_data_list)
        logger.info(f"Prophet dataframe: {prophet_dataframe}")

        return prophet_dataframe

    def __create_prophet_dataframe(
        self, target_data: DatapointWrapper, regressors_data_list: list[DatapointWrapper] | None = None
    ) -> pd.DataFrame:
        """Creates a valid Prophet dataframe from the target and regressors datapoints."""

        # Convert the datapoints to a dataframe - prophet expects the target data to be 'ds' and 'y' structure
        dataframe = pd.DataFrame([{"ds": point.x, "y": point.y} for point in target_data.datapoints])
        dataframe["ds"] = pd.to_datetime(dataframe["ds"], unit="ms")

        # Add regressors if they are provided
        if regressors_data_list is not None:
            for regressor_data in regressors_data_list:
                # Prophet expects regressors to be added as an additional column
                regressor_dataframe = pd.DataFrame(
                    [{"ds": point.x, regressor_data.attribute_name: point.y} for point in regressor_data.datapoints]
                )
                regressor_dataframe["ds"] = pd.to_datetime(regressor_dataframe["ds"], unit="ms")

                # Interpolate the regressor values to the target data point timestamps
                dataframe = pd.merge_asof(dataframe, regressor_dataframe, on="ds", direction="nearest")

        return dataframe

    def generate_forecast(self) -> bool:
        """Predict the target data using the saved model based on the provider config."""
        model_json = load_model(f"{self.config.id}.json")

        if model_json is None:
            logger.error(f"Failed to load model for {self.config.id}")
            return False

        model: Prophet = model_from_json(model_json)

        # Predict the target data
        future = model.make_future_dataframe(periods=96, freq="30min")
        forecast = model.predict(future)

        # Filter historical data from the forecast dataframe
        last_train_date = model.history["ds"].max()
        forecast_future = forecast[forecast["ds"] > last_train_date]

        datapoints = self.__prophet_forecast_to_datapoints(forecast_future)
        logger.info(f"Datapoints: {datapoints}, {len(datapoints)}")

        # Send the datapoints to the OpenRemote client
        return self.openremote_client.write_predicted_datapoints(
            asset_id=self.config.predicted_asset_attribute.asset_id,
            attribute_name=self.config.predicted_asset_attribute.attribute_name,
            datapoints=datapoints,
        )

    def __prophet_forecast_to_datapoints(self, dataframe: pd.DataFrame) -> list[AssetDatapoint]:
        """Convert a Prophet forecasted dataframe to a list of AssetDatapoint objects."""
        datapoints = []

        # Convert ds datetime to milliseconds since epoch
        for _, row in dataframe.iterrows():
            datapoints.append(AssetDatapoint(x=int(row["ds"].timestamp() * 1000), y=row["yhat"]))

        return datapoints
