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

import logging
import time
from http import HTTPStatus
from typing import Any

import httpx
from pydantic import BaseModel

from openremote_client.models import (
    AssetDatapoint,
    AssetDatapointPeriod,
    AssetDatapointQuery,
    BasicAsset,
    Realm,
    ServiceInfo,
)

MASTER_REALM = "master"


class OAuthTokenResponse(BaseModel):
    """Response model for OpenRemote OAuth token."""

    access_token: str
    token_type: str
    expires_in: int


class OAuthTokenRequest(BaseModel):
    """Request model for OpenRemote OAuth token."""

    grant_type: str
    client_id: str
    client_secret: str


class OpenRemoteClient:
    """Client for OpenRemote API.

    Args:
        openremote_url: The URL of the OpenRemote API.
        keycloak_url: The URL of the Keycloak API.
        realm: The default realm to use for the OpenRemote API.
        service_user: The service user for the OpenRemote API.
        service_user_secret: The service user secret for the OpenRemote API.
        timeout: Timeout in seconds for HTTP requests. Defaults to 30 seconds.

    Raises:
        Exception: If the authentication fails
    """

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        openremote_url: str,
        keycloak_url: str,
        realm: str,
        service_user: str,
        service_user_secret: str,
        timeout: float = 60.0,
    ):
        self.openremote_url: str = openremote_url
        self.keycloak_url: str = keycloak_url
        self.realm: str = realm
        self.service_user: str = service_user
        self.service_user_secret: str = service_user_secret
        self.oauth_token: OAuthTokenResponse | None = None
        self.token_expiration_timestamp: float | None = None
        self.timeout: float = timeout

        # Initialize nested clients
        self.assets = self._Assets(self)
        self.realms = self._Realms(self)
        self.health = self._Health(self)
        self.services = self._Services(self)

        self._authenticate()

    def _authenticate(self) -> bool:
        token = self._get_token()
        if token is not None:
            self.oauth_token = token
            self.token_expiration_timestamp = time.time() + token.expires_in
            return True
        return False

    def _get_token(self) -> OAuthTokenResponse | None:
        url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"

        data = OAuthTokenRequest(
            grant_type="client_credentials",
            client_id=self.service_user,
            client_secret=self.service_user_secret,
        )

        with httpx.Client(timeout=self.timeout) as client:
            try:
                response = client.post(url, data=data.model_dump())
                response.raise_for_status()
                token_data = OAuthTokenResponse(**response.json())
                return token_data
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                self.logger.warning(f"Error getting authentication token: {e}")
                return None

    def _check_and_refresh_auth(self) -> bool:
        if self.oauth_token is None or (
            self.token_expiration_timestamp is not None and time.time() > self.token_expiration_timestamp - 10
        ):
            return self._authenticate()
        return True

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.oauth_token is not None:
            headers["Authorization"] = f"Bearer {self.oauth_token.access_token}"
        return headers

    def _build_request(self, method: str, url: str, data: Any | None = None) -> httpx.Request:
        self._check_and_refresh_auth()
        headers = self._build_headers()
        return httpx.Request(method, url, headers=headers, json=data)

    class _Health:
        """Health check operations."""

        def __init__(self, client: "OpenRemoteClient"):
            self._client = client

        def check(self) -> bool:
            """Check if the OpenRemote API is healthy.

            Returns:
                bool: True if healthy, False if not.
            """
            url = f"{self._client.openremote_url}/api/master/health"

            request = self._client._build_request("GET", url)
            with httpx.Client(timeout=self._client.timeout) as client:
                try:
                    response = client.send(request)
                    response.raise_for_status()
                    return response.status_code == HTTPStatus.OK
                except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                    self._client.logger.error(f"OpenRemote API is not healthy: {e}")
                    return False

    class _Assets:
        """Asset-related operations."""

        def __init__(self, client: "OpenRemoteClient"):
            self._client = client

        def get_datapoint_period(
            self, asset_id: str, attribute_name: str, realm: str | None = None
        ) -> AssetDatapointPeriod | None:
            """Retrieve the datapoints timestamp period of a given asset attribute.

            Args:
                asset_id: The ID of the asset.
                attribute_name: The name of the attribute.
                realm: The realm to retrieve assets from defaulting to the configured realm.

            Returns:
                AssetDatapointPeriod | None: The datapoints timestamp period of the asset attribute
            """
            if realm is None:
                realm = self._client.realm

            query = f"?assetId={asset_id}&attributeName={attribute_name}"
            url = f"{self._client.openremote_url}/api/{realm}/asset/datapoint/periods{query}"

            request = self._client._build_request("GET", url)

            with httpx.Client(timeout=self._client.timeout) as client:
                try:
                    response = client.send(request)
                    response.raise_for_status()
                    return AssetDatapointPeriod(**response.json())
                except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                    self._client.logger.error(f"Error retrieving asset datapoint period: {e}")
                    return None

        def get_historical_datapoints(
            self,
            asset_id: str,
            attribute_name: str,
            from_timestamp: int,
            to_timestamp: int,
            realm: str | None = None,
        ) -> list[AssetDatapoint] | None:
            """Retrieve the historical data points of a given asset attribute.

            Remarks:
            - Note, request may fail if more than 100k datapoints are requested, depending on the OpenRemote instance.

            Args:
                asset_id: The ID of the asset.
                attribute_name: The name of the attribute.
                from_timestamp: Epoch timestamp in milliseconds.
                to_timestamp: Epoch timestamp in milliseconds.
                realm: The realm to retrieve assets from defaulting to the configured realm.
            Returns:
                list[AssetDatapoint] | None: List of historical data points or None
            """
            if realm is None:
                realm = self._client.realm

            params = f"{asset_id}/{attribute_name}"
            url = f"{self._client.openremote_url}/api/{realm}/asset/datapoint/{params}"

            request_body = AssetDatapointQuery(
                fromTimestamp=from_timestamp,
                toTimestamp=to_timestamp,
            )

            request = self._client._build_request("POST", url, data=request_body.model_dump())

            with httpx.Client(timeout=self._client.timeout) as client:
                try:
                    response = client.send(request)
                    response.raise_for_status()
                    datapoints = response.json()
                    return [AssetDatapoint(**datapoint) for datapoint in datapoints]
                except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                    self._client.logger.error(f"Error retrieving historical datapoints: {e}")
                    return None

        def write_predicted_datapoints(
            self,
            asset_id: str,
            attribute_name: str,
            datapoints: list[AssetDatapoint],
            realm: str | None = None,
        ) -> bool:
            """Write the predicted data points of a given asset attribute.

            Args:
                asset_id: The ID of the asset.
                attribute_name: The name of the attribute.
                datapoints: The data points to write.
                realm: The realm to write the data points to defaulting to the configured realm.
            Returns:
                bool: True if successful
            """
            if realm is None:
                realm = self._client.realm

            params = f"{asset_id}/{attribute_name}"
            url = f"{self._client.openremote_url}/api/{realm}/asset/predicted/{params}"

            datapoints_json = [datapoint.model_dump() for datapoint in datapoints]

            request = self._client._build_request("PUT", url, data=datapoints_json)

            with httpx.Client(timeout=self._client.timeout) as client:
                try:
                    response = client.send(request)
                    response.raise_for_status()
                    return response.status_code == HTTPStatus.NO_CONTENT
                except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                    self._client.logger.error(f"Error writing predicted datapoints: {e}")
                    return False

        def get_predicted_datapoints(
            self,
            asset_id: str,
            attribute_name: str,
            from_timestamp: int,
            to_timestamp: int,
            realm: str | None = None,
        ) -> list[AssetDatapoint] | None:
            """Retrieve the predicted data points of a given asset attribute.

            Args:
                asset_id: The ID of the asset.
                attribute_name: The name of the attribute.
                from_timestamp: Epoch timestamp in milliseconds.
                to_timestamp: Epoch timestamp in milliseconds.
                realm: The realm to retrieve assets from defaulting to the configured realm.
            Returns:
                list[AssetDatapoint] | None: List of predicted data points or None
            """
            if realm is None:
                realm = self._client.realm

            params = f"{asset_id}/{attribute_name}"
            url = f"{self._client.openremote_url}/api/{realm}/asset/predicted/{params}"

            request_body = AssetDatapointQuery(
                fromTimestamp=from_timestamp,
                toTimestamp=to_timestamp,
            )

            request = self._client._build_request("POST", url, data=request_body.model_dump())

            with httpx.Client(timeout=self._client.timeout) as client:
                try:
                    response = client.send(request)
                    response.raise_for_status()
                    datapoints = response.json()
                    return [AssetDatapoint(**datapoint) for datapoint in datapoints]
                except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                    self._client.logger.error(f"Error retrieving predicted datapoints: {e}")
                    return None

        def query(
            self, asset_query: dict[str, Any], query_realm: str, realm: str | None = None
        ) -> list[BasicAsset] | None:
            """Perform an asset query.

            Args:
                asset_query: The asset query dict to send to the OpenRemote API.
                query_realm: The realm for the asset query.
                realm: The realm to retrieve assets from defaulting to the configured realm.
            Returns:
                list[Asset] | None: List of assets or None
            """
            if realm is None:
                realm = self._client.realm

            url = f"{self._client.openremote_url}/api/{realm}/asset/query"
            request = self._client._build_request("POST", url, data=asset_query)
            with httpx.Client(timeout=self._client.timeout) as client:
                try:
                    response = client.send(request)
                    response.raise_for_status()
                    assets = response.json()
                    return [BasicAsset(**asset) for asset in assets]
                except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                    self._client.logger.error(f"Error retrieving assets: {e}")
                    return None

        def get_by_ids(
            self, asset_ids: list[str], query_realm: str, realm: str | None = None
        ) -> list[BasicAsset] | None:
            """Retrieve assets by their IDs.

            Args:
                asset_ids: The IDs of the assets to retrieve.
                query_realm: The realm for the asset query.
                realm: The realm to retrieve assets from defaulting to the configured realm.

            Returns:
                list[Asset] | None: List of assets or None
            """
            if realm is None:
                realm = self._client.realm

            asset_query = {
                "recursive": False,
                "realm": {"name": query_realm},
                "ids": asset_ids,
            }
            return self.query(asset_query, query_realm, realm)

    class _Realms:
        """Realm-related operations."""

        def __init__(self, client: "OpenRemoteClient"):
            self._client = client

        def get_accessible(self, realm: str | None = None) -> list[Realm] | None:
            """Retrieves all realms.

            Args:
                realm: The realm to retrieve realms from defaulting to the configured realm.

            Returns:
                list[Realm] | None: List of realms or None
            """
            if realm is None:
                realm = self._client.realm

            url = f"{self._client.openremote_url}/api/{realm}/realm/accessible"
            request = self._client._build_request("GET", url)

            with httpx.Client(timeout=self._client.timeout) as client:
                try:
                    response = client.send(request)
                    response.raise_for_status()

                    return [Realm(**realm) for realm in response.json()]

                except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                    self._client.logger.error(f"Error retrieving realms: {e}")
                    return None

    class _Services:
        """Service-related operations."""

        def __init__(self, client: "OpenRemoteClient"):
            self._client = client

        def register(self, service: ServiceInfo) -> ServiceInfo | None:
            """Registers a service with the OpenRemote API."""
            url = f"{self._client.openremote_url}/api/{self._client.realm}/service"
            request = self._client._build_request("POST", url, data=service.model_dump())
            with httpx.Client(timeout=self._client.timeout) as client:
                try:
                    response = client.send(request)
                    response.raise_for_status()
                    return ServiceInfo(**response.json())
                except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                    self._client.logger.error(f"Error registering service: {e}")
                    return None

        def heartbeat(self, service_id: str, instance_id: str) -> bool:
            """Sends a heartbeat to the OpenRemote API."""
            url = f"{self._client.openremote_url}/api/{MASTER_REALM}/service/{service_id}/{instance_id}"
            request = self._client._build_request("PUT", url)
            with httpx.Client(timeout=self._client.timeout) as client:
                try:
                    response = client.send(request)
                    response.raise_for_status()
                    return response.status_code == HTTPStatus.NO_CONTENT
                except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                    self._client.logger.error(f"Error sending heartbeat: {e}")
                    return False

        def deregister(self, service_id: str, instance_id: str) -> bool:
            """Deregisters a service with the OpenRemote API."""
            url = f"{self._client.openremote_url}/api/{MASTER_REALM}/service/{service_id}/{instance_id}"
            request = self._client._build_request("DELETE", url)
            with httpx.Client(timeout=self._client.timeout) as client:
                try:
                    response = client.send(request)
                    response.raise_for_status()
                    return response.status_code == HTTPStatus.NO_CONTENT
                except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                    self._client.logger.error(f"Error deregistering service: {e}")
                    return False
