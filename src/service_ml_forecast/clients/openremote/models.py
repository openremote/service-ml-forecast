from typing import Any

from pydantic import BaseModel


class AssetAttribute(BaseModel):
    """Minimal attribute of an asset."""

    name: str
    value: Any | None
    timestamp: int


class Asset(BaseModel):
    """Minimal asset of OpenRemote."""

    id: str
    realm: str
    parentId: str | None = None
    attributes: dict[str, AssetAttribute]

    def get_attribute_value(self, attribute_name: str) -> Any | None:
        """Helper method to get an attribute value."""
        if attribute_name in self.attributes:
            return self.attributes[attribute_name].value
        return None


class AssetDatapointPeriod(BaseModel):
    """Datapoint period of an asset attribute."""

    assetId: str
    attributeName: str
    oldestTimestamp: int
    latestTimestamp: int


class AssetDatapoint(BaseModel):
    """Data point of an asset attribute.

    Args:
        x: The timestamp of the data point.
        y: The value of the data point.

    """

    x: int
    y: Any


class DatapointsRequestBody(BaseModel):
    """Request body for retrieving either historical or predicted data points of an asset attribute."""

    fromTimestamp: int
    toTimestamp: int
    fromTime: str = ""
    toTime: str = ""
    type: str = "string"
