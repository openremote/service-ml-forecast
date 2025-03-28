from pydantic import BaseModel

from service_ml_forecast.clients.openremote.models import AssetDatapoint


class FeatureDatapoints(BaseModel):
    """Feature with the attribute name and the datapoints."""

    attribute_name: str
    datapoints: list[AssetDatapoint]


class TrainingFeatureSet(BaseModel):
    """Training set of the target and regressors."""

    target: FeatureDatapoints
    regressors: list[FeatureDatapoints] | None = None


class ForecastFeatureSet(BaseModel):
    """Forecast feature set with regressors."""

    regressors: list[FeatureDatapoints]


class ForecastResult(BaseModel):
    """Forecast result with the asset id, attribute name and the forecasted datapoints."""

    asset_id: str
    attribute_name: str
    datapoints: list[AssetDatapoint]
