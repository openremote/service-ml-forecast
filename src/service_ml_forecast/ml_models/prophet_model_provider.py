import logging

import pandas as pd
from prophet import Prophet
from prophet.serialize import model_from_json, model_to_json

from service_ml_forecast.clients.openremote.models import AssetDatapoint
from service_ml_forecast.ml_models.model_provider import ModelProvider, SaveModelCallable
from service_ml_forecast.ml_models.model_util import (
    ForecastResult,
    TrainingDataset,
    load_model,
    save_model,
)
from service_ml_forecast.schemas.model_config import ProphetModelConfig

logger = logging.getLogger(__name__)


def prophet_forecast_to_datapoints(dataframe: pd.DataFrame) -> list[AssetDatapoint]:
    """Convert a Prophet forecasted dataframe to a list of AssetDatapoint objects.

    Args:
        dataframe: The forecasted dataframe to convert.

    Returns:
        A list of AssetDatapoint objects.
    """
    datapoints = []
    # Convert ds datetime to milliseconds since epoch
    for _, row in dataframe.iterrows():
        datapoints.append(AssetDatapoint(x=int(row["ds"].timestamp() * 1000), y=row["yhat"]))

    return datapoints


def create_prophet_dataframe(training_dataset: TrainingDataset) -> pd.DataFrame | None:
    """Creates a Prophet dataframe from the training dataset.

    Args:
        training_dataset: The training dataset to create the dataframe from.

    Returns:
        A valid Prophet dataframe.
    """
    target = training_dataset.target
    regressors = training_dataset.regressors

    # Convert the datapoints to a dataframe - prophet expects the target data to be 'ds' and 'y' structure
    dataframe = pd.DataFrame([{"ds": point.x, "y": point.y} for point in target.datapoints])
    dataframe["ds"] = pd.to_datetime(dataframe["ds"], unit="ms")

    # Add regressors if they are provided
    if regressors is not None:
        for regressor in regressors:
            regressor_dataframe = pd.DataFrame(
                [{"ds": point.x, regressor.attribute_name: point.y} for point in regressor.datapoints]
            )
            regressor_dataframe["ds"] = pd.to_datetime(regressor_dataframe["ds"], unit="ms")

            # Interpolate the regressor values to the target data point timestamps
            dataframe = pd.merge_asof(dataframe, regressor_dataframe, on="ds", direction="nearest")

    return dataframe


class ProphetModelProvider(ModelProvider):
    """Prophet model provider."""

    def __init__(
        self,
        config: ProphetModelConfig,
    ) -> None:
        self.config = config

    def __load_model(self) -> Prophet | None:
        model_json = load_model(f"{self.config.id}.json")

        if model_json is None:
            logger.error(f"Failed to load model for {self.config.id}")
            return None

        model: Prophet = model_from_json(model_json)

        return model

    def train_model(self, training_dataset: TrainingDataset) -> SaveModelCallable | None:
        """Train the Prophet model

        Args:
            training_dataset: The training dataset to train the model on.

        Returns:
            A callable that saves the trained model to a file.
        """
        if training_dataset.target.datapoints is None or len(training_dataset.target.datapoints) == 0:
            logger.error("No target data provided, cannot train Prophet model")
            return None

        dataframe = create_prophet_dataframe(training_dataset)
        if dataframe is None:
            logger.error("Failed to obtain valid dataframe for training the Prophet model")
            return None

        # Train the Prophet model
        model = Prophet()
        model.fit(dataframe)

        # Return a callable that saves the trained model to a file
        def callback() -> bool:
            if not save_model(model_to_json(model), f"{self.config.id}.json"):
                logger.error(f"Failed to save trained model for {self.config.id}")
                return False

            logger.info(f"Successfully trained and saved model for {self.config.id}")
            return True

        return callback

    def generate_forecast(self) -> ForecastResult | None:
        """Generate a forecast for the target attribute.

        Returns:
            A ForecastResult object containing the forecasted datapoints.
        """
        model = self.__load_model()
        if model is None:
            logger.error(f"Failed to load model for {self.config.id}")
            return None

        future = model.make_future_dataframe(periods=96, freq="30min")
        forecast = model.predict(future)

        # Filter historical data from the forecast dataframe
        last_train_date = model.history["ds"].max()
        forecast_future = forecast[forecast["ds"] > last_train_date]

        # noinspection PyTypeChecker
        datapoints = prophet_forecast_to_datapoints(forecast_future)
        logger.info(f"Generated {len(datapoints)} forecasted datapoints")

        return ForecastResult(
            asset_id=self.config.target.asset_id,
            attribute_name=self.config.target.attribute_name,
            datapoints=datapoints,
        )
