from pydantic import BaseModel


class AssetDatapointPeriod(BaseModel):
    assetId: str
    attributeName: str
    oldestTimestamp: int
    latestTimestamp: int
