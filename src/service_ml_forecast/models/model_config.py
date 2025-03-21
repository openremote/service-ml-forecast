from enum import Enum

from pydantic import BaseModel, Field


class AssetAttribute(BaseModel):
    asset_id: str = Field(description="The id of the asset. This is the id of the asset in the OpenRemote API.")
    attribute_name: str = Field(
        description="The name of the attribute of the asset from OpenRemote. This attribute requires historical data."
    )


class ModelType(str, Enum):
    PROPHET = "prophet"


# TODO: Add validators for the iso duration strings
# TODO: Add validations that use the OpenRemote API to check if the asset attributes exist and has data -
# use DI to inject the OpenRemote API client


class BaseModelConfig(BaseModel):
    """Base model config for all ML models."""

    id: str | None = Field(
        description="ID of the model configuration. If not provided, a random uuid will be generated."
    )
    name: str = Field(description="A friendly name for the model configuration.")
    type: ModelType = Field(description="Which machine learning model to use.")
    predicated_asset_attribute: AssetAttribute = Field(
        description="The target asset attribute to predict. This attribute must have historical data available."
    )
    forecast_interval: str = Field(description="Forecast generation interval. Expects ISO 8601 duration strings.")
    training_interval: str = Field(description="Model training interval. Expects ISO 8601 duration strings.")
    forecast_period: str = Field(description="The duration of the forecast. Expects ISO 8601 duration strings.")
    forecast_datapoint_interval: str = Field(
        description="The interval between forecasted datapoints. Expects ISO 8601 duration strings."
    )
    history_oldest_timestamp: str = Field(
        description="The starting timestamp to use for training. Expects milliseconds since epoch."
    )
    history_newest_timestamp: str = Field(
        description="The ending timestamp to use for training. Expects milliseconds since epoch."
    )


class ProphetModelConfig(BaseModelConfig):
    """Prophet specific model config."""

    type: ModelType = ModelType.PROPHET
    regressors: list[AssetAttribute] = Field(
        description="The asset attributes that will be used as regressors. "
        "These attributes must have historical data and forecasted values available for the configured forecast period."
    )
    seasonality: bool = Field(description="Whether to include seasonality in the model.")
