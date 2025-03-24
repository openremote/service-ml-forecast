from pydantic import BaseModel

from service_ml_forecast.clients.openremote.models import AssetDatapoint


class DatapointWrapper(BaseModel):
    """Util class for wrapping datapoints with their attribute name."""

    attribute_name: str
    datapoints: list[AssetDatapoint]
