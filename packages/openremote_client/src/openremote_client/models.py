# Copyright 2025, OpenRemote Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum
from typing import Any

from pydantic import BaseModel


class BasicAttribute(BaseModel):
    """Minimal attribute of an asset."""

    name: str
    value: Any | None
    timestamp: int
    meta: dict[str, Any] | None = None


class BasicAsset(BaseModel):
    """Minimal asset of OpenRemote."""

    id: str
    name: str
    realm: str
    parentId: str | None = None
    attributes: dict[str, BasicAttribute]

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


class AssetDatapointQuery(BaseModel):
    """Request body for querying asset datapoints."""

    fromTimestamp: int
    toTimestamp: int
    fromTime: str = ""
    toTime: str = ""


class Realm(BaseModel):
    """Realm model."""

    id: str
    name: str
    displayName: str
    enabled: bool


class ServiceStatus(str, Enum):
    """The status of a registered service.

    - AVAILABLE: The service is available and can be used
    - UNAVAILABLE: The service is unavailable
    - ERROR: The service is in an error state
    - UNKNOWN: The service status is unknown
    """

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


class ServiceDescriptor(BaseModel):
    """Holds comprehensive details about a service.

    This object is used to register and deregister services.
    """

    label: str
    """The label of the service, e.g. 'Energy Service'"""

    serviceId: str
    """The unique identifier of the service, e.g. 'energy-service'"""

    ipAddress: str | None = None
    """The IP address of the service, e.g. '192.168.1.100'"""

    port: int | None = None
    """The port of the service, e.g. 8080"""

    homepageUrl: str | None = None
    """The URL of the service's homepage which provides the user interface,
    e.g. 'https://openremote.app/services/energy-service/ui'"""

    status: ServiceStatus | None = None
    """The status of the service, e.g. 'AVAILABLE'"""


class ServiceRegistrationResponse(BaseModel):
    """Response object for the service register operation.

    Used to return the instanceId of the registered service.
    """

    instanceId: str
    """The unique instance identifier of the registered service."""
