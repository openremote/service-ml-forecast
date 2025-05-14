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

from service_ml_forecast.clients.openremote.models import Asset, RealmConfig
from service_ml_forecast.clients.openremote.openremote_client import OAuthTokenResponse, OpenRemoteClient

logger = logging.getLogger(__name__)


class OpenRemoteProxyService:
    """Service for forwarding requests to the OpenRemote Manager API."""

    def __init__(self, openremote_url: str, token: str):
        self.client = OpenRemoteProxyClient(openremote_url=openremote_url, token=token)

    def get_assets_with_historical_datapoints(self, realm: str) -> list[Asset]:
        """Get all assets from OpenRemote with historical datapoints.

        Returns:
            A list of all assets from OpenRemote with historical datapoints.
        """
        assets = self.client.retrieve_assets_with_historical_datapoints(realm)
        if assets is None:
            logger.warning(f"Unable to retrieve assets with storeDataPoints for realm {realm}")
            return []

        return assets

    def get_assets_by_ids(self, realm: str, asset_ids: list[str]) -> list[Asset]:
        """Get all assets from OpenRemote.

        Returns:
            A list of all assets from OpenRemote.
        """
        assets = self.client.retrieve_assets_by_ids(asset_ids, realm)
        if assets is None:
            logger.warning(f"Unable to retrieve assets by ids for realm {realm}")
            return []

        return assets

    def get_realm_config(self, realm: str) -> RealmConfig | None:
        """Get the realm configuration for a given realm.

        Returns:
            The realm configuration or None if the realm configuration could not be retrieved.
        """
        config = self.client.retrieve_manager_config()

        if config is None:
            logger.warning("Unable to retrieve manager config")
            return None

        if realm not in config.realms:
            logger.warning(f"Realm {realm} not found in manager config")
            return None

        return config.realms[realm]


class OpenRemoteProxyClient(OpenRemoteClient):
    """Override the OpenRemoteClient to use a provided token instead of authenticating.

    Used for directly proxying requests to the OpenRemote API, using the provided token.

    Args:
        openremote_url: The URL of the OpenRemote API.
        token: The authentication token to use for requests.
    """

    def __init__(self, openremote_url: str, token: str):
        # Skip parent class initialization to avoid authentication
        self.openremote_url = openremote_url
        self.keycloak_url = ""  # Not used in proxy client
        self.service_user = ""  # Not used in proxy client
        self.service_user_secret = ""  # Not used in proxy client

        # Set up token directly
        self.oauth_token = OAuthTokenResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=3600,  # Default expiration, not used since we don't refresh
        )
        self.token_expiration_timestamp = None  # We don't expire the token

    def __authenticate(self) -> bool:
        # Override authentication to always return True
        return True

    def __check_and_refresh_auth(self) -> bool:
        # Override token refresh to always return True
        return True
