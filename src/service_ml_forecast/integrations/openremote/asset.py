from typing import Any

from pydantic import BaseModel


class AssetAttribute(BaseModel):
    name: str
    value: Any | None
    timestamp: int


class Asset(BaseModel):
    id: str
    realm: str
    parentId: str | None = None
    attributes: dict[str, AssetAttribute]

    def get_attribute_value(self, attribute_name: str) -> Any | None:
        """Helper method to easily get an attribute value."""
        if attribute_name in self.attributes:
            return self.attributes[attribute_name].value
        return None
