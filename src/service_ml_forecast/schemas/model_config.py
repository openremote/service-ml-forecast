from enum import Enum

from pydantic import BaseModel, Field


class ModelInputAssetAttribute(BaseModel):
    asset_id: str = Field(description="The id of the asset. This is the id of the asset in the OpenRemote API.")
    attribute_name: str = Field(
        description="The name of the attribute of the asset from OpenRemote. This attribute requires historical data."
    )
    oldest_timestamp: int = Field(
        description="The oldest timestamp to use for training. Expects milliseconds since epoch."
    )
    newest_timestamp: int = Field(
        description="The newest timestamp to use for training. Expects milliseconds since epoch."
    )


class ModelType(str, Enum):
    PROPHET = "prophet"


class ModelConfig(BaseModel):
    """Base model config for all ML models."""

    id: str | None = Field(
        description="ID of the model configuration. If not provided, a random uuid will be generated."
    )
    name: str = Field(description="A friendly name for the model configuration.")
    type: ModelType = Field(description="Which machine learning model to use.")
    predicted_asset_attribute: ModelInputAssetAttribute = Field(
        description="The asset attribute to predict. This attribute must have historical data available."
    )
    forecast_interval: str = Field(description="Forecast generation interval. Expects ISO 8601 duration strings.")
    training_interval: str = Field(description="Model training interval. Expects ISO 8601 duration strings.")
    forecast_period: str = Field(description="The duration of the forecast. Expects ISO 8601 duration strings.")
    forecast_datapoint_interval: str = Field(
        description="The interval between forecasted datapoints. Expects ISO 8601 duration strings."
    )
    trained_at: int | None = Field(
        default=None, description="The timestamp when the model was trained. Expects milliseconds since epoch."
    )
    forecasted_at: int | None = Field(
        default=None, description="The timestamp when the forecast was generated. Expects milliseconds since epoch."
    )


class ProphetModelConfig(ModelConfig):
    """Prophet specific model config."""

    type: ModelType = ModelType.PROPHET
    regressors: list[ModelInputAssetAttribute] | None = Field(
        default=None,
        description="List of model input asset attributes that will be used as regressors. "
        "They must have historical data and predicted values available for the configured forecast period.",
    )
    seasonality: bool = Field(
        default=True,
        description="Whether to include seasonality in the model.",
    )
