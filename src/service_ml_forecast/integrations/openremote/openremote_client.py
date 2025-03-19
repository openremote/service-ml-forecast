# POST Retrieve assets - https://demo.openremote.io/api/master/asset/query
# GET Data point period of asset attribute - https://demo.openremote.io/api/master/asset/datapoint/:assetId/:attributeName/period
# GET Historical data points of asset attribute - https://demo.openremote.io/api/master/asset/datapoint/:assetId/:attributeName
# PUT Write predicted data points of asset attribute - https://demo.openremote.io/api/master/asset/predicted/:assetId/:attributeName
# POST Retrieve predicted data points of asset attribute - https://demo.openremote.io/api/master/asset/predicted/:assetId/:attributeName

import logging
import time
from typing import Any

import httpx
from pydantic import BaseModel

from service_ml_forecast.integrations.openremote.models import (
    Asset,
    AssetDatapointPeriod,
    Datapoint,
    HistoricalDatapointsRequestBody,
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

    """

    logger = logging.getLogger(__name__)

    def __init__(self, openremote_url: str, keycloak_url: str, service_user: str, service_user_secret: str):
        self.openremote_url: str = openremote_url
        self.keycloak_url: str = keycloak_url
        self.service_user: str = service_user
        self.service_user_secret: str = service_user_secret
        self.oauth_token: OAuthTokenResponse = self.__get_token()

        # Fail if the service failed to authenticate with OpenRemote
        if not self.oauth_token:
            raise RuntimeError("Failed to authenticate Service User with OpenRemote")

        self.token_expiration_timestamp: float = time.time() + self.oauth_token.expires_in

        self.logger.info("OpenRemote client initialized")

    def __get_token(self) -> OAuthTokenResponse:
        """Get OAuth2 token for the Service User."""
        url = f"{self.keycloak_url}/auth/realms/master/protocol/openid-connect/token"

        data = OAuthTokenRequest(
            grant_type="client_credentials",
            client_id=self.service_user,
            client_secret=self.service_user_secret,
        )

        with httpx.Client() as client:
            response = client.post(url, data=data.model_dump())
            response.raise_for_status()
            token_data = OAuthTokenResponse(**response.json())

            return token_data

    def __refresh_token(self) -> None:
        """Refresh the OAuth2 token if it is expired."""

        # Refresh token if it has expired with an offset of 10 seconds
        if self.token_expiration_timestamp and time.time() > self.token_expiration_timestamp - 10:
            self.oauth_token = self.__get_token()
            self.token_expiration_timestamp = time.time() + self.oauth_token.expires_in

    def __build_headers(self) -> dict[str, str]:
        """Build headers dictionary."""
        headers = {
            "Authorization": f"Bearer {self.oauth_token.access_token}",
            "Content-Type": "application/json",
        }
        return headers

    def __build_request(self, method: str, url: str, data: Any | None = None) -> httpx.Request:
        """Build a HTTPX request object."""
        headers = self.__build_headers()
        self.__refresh_token()
        return httpx.Request(method, url, headers=headers, json=data)

    def retrieve_assets(self, realm: str) -> list[Asset]:
        """Retrieve all assets for a given realm."""
        url = f"{self.openremote_url}/api/{realm}/asset/query"

        asset_query = {"recursive": True, "realm": {"name": realm}}

        request = self.__build_request("POST", url, data=asset_query)

        with httpx.Client() as client:
            response = client.send(request)
            response.raise_for_status()
            assets = response.json()

            return [Asset(**asset) for asset in assets]

    def retrieve_asset_datapoint_period(self, asset_id: str, attribute_name: str) -> AssetDatapointPeriod:
        """Retrieve the datapoints timestamp period of a given asset attribute."""
        query = f"?assetId={asset_id}&attributeName={attribute_name}"
        url = f"{self.openremote_url}/api/master/asset/datapoint/periods{query}"

        request = self.__build_request("GET", url)

        with httpx.Client() as client:
            response = client.send(request)
            response.raise_for_status()
            datapoint_period = AssetDatapointPeriod(**response.json())

            return datapoint_period

    def retrieve_historical_datapoints(
        self, asset_id: str, attribute_name: str, from_timestamp: int, to_timestamp: int
    ) -> list[Datapoint]:
        """Retrieve the historical data points of a given asset attribute."""
        params = f"{asset_id}/{attribute_name}"
        url = f"{self.openremote_url}/api/master/asset/datapoint/{params}"

        request_body = HistoricalDatapointsRequestBody(
            fromTimestamp=from_timestamp,
            toTimestamp=to_timestamp,
        )
        request = self.__build_request("POST", url, data=request_body.model_dump())

        with httpx.Client() as client:
            response = client.send(request)
            response.raise_for_status()
            datapoints = response.json()

            return [Datapoint(**datapoint) for datapoint in datapoints]
