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

from service_ml_forecast.clients.openremote.models import (
    Asset,
    AssetDatapoint,
    AssetDatapointPeriod,
    AssetDatapointQuery,
)


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
        service_user: The service user for the OpenRemote API.
        service_user_secret: The service user secret for the OpenRemote API.

    Raises:
        Exception: If the authentication fails
    """

    logger = logging.getLogger(__name__)

    def __init__(self, openremote_url: str, keycloak_url: str, service_user: str, service_user_secret: str):
        self.openremote_url: str = openremote_url
        self.keycloak_url: str = keycloak_url
        self.service_user: str = service_user
        self.service_user_secret: str = service_user_secret
        self.oauth_token: OAuthTokenResponse | None = None
        self.token_expiration_timestamp: float | None = None

        self.__authenticate()

    def __authenticate(self) -> bool:
        token = self.__get_token()
        if token is not None:
            self.oauth_token = token
            self.token_expiration_timestamp = time.time() + token.expires_in
            return True
        return False

    def __get_token(self) -> OAuthTokenResponse | None:
        url = f"{self.keycloak_url}/auth/realms/master/protocol/openid-connect/token"

        data = OAuthTokenRequest(
            grant_type="client_credentials",
            client_id=self.service_user,
            client_secret=self.service_user_secret,
        )

        with httpx.Client() as client:
            try:
                response = client.post(url, data=data.model_dump())
                response.raise_for_status()
                token_data = OAuthTokenResponse(**response.json())
                return token_data
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                self.logger.warning(f"Error getting authentication token: {e}")
                return None

    def __check_and_refresh_auth(self) -> bool:
        if self.oauth_token is None or (
            self.token_expiration_timestamp is not None and time.time() > self.token_expiration_timestamp - 10
        ):
            return self.__authenticate()
        return True

    def __build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.oauth_token is not None:
            headers["Authorization"] = f"Bearer {self.oauth_token.access_token}"
        return headers

    def __build_request(self, method: str, url: str, data: Any | None = None) -> httpx.Request:
        self.__check_and_refresh_auth()
        headers = self.__build_headers()
        return httpx.Request(method, url, headers=headers, json=data)

    def health_check(self) -> bool:
        """Check if the OpenRemote API is healthy.

        Returns:
            bool: True if healthy, False if not.
        """

        url = f"{self.openremote_url}/api/master/health"

        request = self.__build_request("GET", url)
        with httpx.Client() as client:
            try:
                response = client.send(request)
                response.raise_for_status()
                return response.status_code == HTTPStatus.OK
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                self.logger.error(f"OpenRemote API is not healthy: {e}")
                return False

    def retrieve_asset_datapoint_period(self, asset_id: str, attribute_name: str) -> AssetDatapointPeriod | None:
        """Retrieve the datapoints timestamp period of a given asset attribute.

        Args:
            asset_id: The ID of the asset.
            attribute_name: The name of the attribute.

        Returns:
            AssetDatapointPeriod | None: The datapoints timestamp period of the asset attribute
        """

        query = f"?assetId={asset_id}&attributeName={attribute_name}"
        url = f"{self.openremote_url}/api/master/asset/datapoint/periods{query}"

        request = self.__build_request("GET", url)

        with httpx.Client() as client:
            try:
                response = client.send(request)
                response.raise_for_status()
                return AssetDatapointPeriod(**response.json())
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                self.logger.error(f"Error retrieving asset datapoint period: {e}")
                return None

    def retrieve_historical_datapoints(
        self,
        asset_id: str,
        attribute_name: str,
        from_timestamp: int,
        to_timestamp: int,
    ) -> list[AssetDatapoint] | None:
        """Retrieve the historical data points of a given asset attribute.

        Args:
            asset_id: The ID of the asset.
            attribute_name: The name of the attribute.
            from_timestamp: Epoch timestamp in milliseconds.
            to_timestamp: Epoch timestamp in milliseconds.

        Returns:
            list[AssetDatapoint] | None: List of historical data points or None
        """

        params = f"{asset_id}/{attribute_name}"
        url = f"{self.openremote_url}/api/master/asset/datapoint/{params}"

        request_body = AssetDatapointQuery(
            fromTimestamp=from_timestamp,
            toTimestamp=to_timestamp,
        )

        request = self.__build_request("POST", url, data=request_body.model_dump())

        with httpx.Client() as client:
            try:
                response = client.send(request)
                response.raise_for_status()
                datapoints = response.json()
                return [AssetDatapoint(**datapoint) for datapoint in datapoints]
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                self.logger.error(f"Error retrieving historical datapoints: {e}")
                return None

    def write_predicted_datapoints(self, asset_id: str, attribute_name: str, datapoints: list[AssetDatapoint]) -> bool:
        """Write the predicted data points of a given asset attribute.

        Args:
            asset_id: The ID of the asset.
            attribute_name: The name of the attribute.
            datapoints: The data points to write.

        Returns:
            bool: True if successful
        """

        params = f"{asset_id}/{attribute_name}"
        url = f"{self.openremote_url}/api/master/asset/predicted/{params}"

        datapoints_json = [datapoint.model_dump() for datapoint in datapoints]

        request = self.__build_request("PUT", url, data=datapoints_json)

        with httpx.Client() as client:
            try:
                response = client.send(request)
                response.raise_for_status()
                return response.status_code == HTTPStatus.NO_CONTENT
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                self.logger.error(f"Error writing predicted datapoints: {e}")
                return False

    def retrieve_predicted_datapoints(
        self,
        asset_id: str,
        attribute_name: str,
        from_timestamp: int,
        to_timestamp: int,
    ) -> list[AssetDatapoint] | None:
        """Retrieve the predicted data points of a given asset attribute.

        Args:
            asset_id: The ID of the asset.
            attribute_name: The name of the attribute.
            from_timestamp: Epoch timestamp in milliseconds.
            to_timestamp: Epoch timestamp in milliseconds.

        Returns:
            list[AssetDatapoint] | None: List of predicted data points or None
        """

        params = f"{asset_id}/{attribute_name}"
        url = f"{self.openremote_url}/api/master/asset/predicted/{params}"

        request_body = AssetDatapointQuery(
            fromTimestamp=from_timestamp,
            toTimestamp=to_timestamp,
        )

        request = self.__build_request("POST", url, data=request_body.model_dump())

        with httpx.Client() as client:
            try:
                response = client.send(request)
                response.raise_for_status()
                datapoints = response.json()
                return [AssetDatapoint(**datapoint) for datapoint in datapoints]
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                self.logger.error(f"Error retrieving predicted datapoints: {e}")
                return None

    def retrieve_assets_with_historical_datapoints(self, realm: str) -> list[Asset] | None:
        """Retrieve all assets for a given realm with historical datapoints.

        ()

        Args:
            realm: The realm to retrieve assets from.

        Returns:
            list[Asset] | None: List of assets or None
        """

        url = f"{self.openremote_url}/api/master/asset/query"
        asset_query = {"recursive": True, "realm": {"name": realm}}

        request = self.__build_request("POST", url, data=asset_query)

        with httpx.Client() as client:
            try:
                response = client.send(request)
                response.raise_for_status()
                assets = response.json()
                return [Asset(**asset) for asset in assets]
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                self.logger.error(f"Error retrieving assets: {e}")
                return None

    def retrieve_assets_by_ids(self, asset_ids: list[str], realm: str) -> list[Asset] | None:
        """Retrieve assets by their IDs.

        Args:
            asset_ids: The IDs of the assets to retrieve.
            realm: The realm to retrieve assets from.

        Returns:
            list[Asset] | None: List of assets or None
        """

        url = f"{self.openremote_url}/api/master/asset/query"
        asset_query = {"recursive": False, "realm": {"name": realm}, "ids": asset_ids}

        request = self.__build_request("POST", url, data=asset_query)

        with httpx.Client() as client:
            try:
                response = client.send(request)
                response.raise_for_status()
                assets = response.json()
                return [Asset(**asset) for asset in assets]
            except (httpx.HTTPStatusError, httpx.ConnectError) as e:
                self.logger.error(f"Error retrieving assets: {e}")
                return None
