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

"""
This module contains the dependency injectors for the service.

The injectors are used to inject the services into the FastAPI app, or other dependencies.
"""

import logging

from fastapi.security import OAuth2PasswordBearer
from openremote_client import OpenRemoteClient

from service_ml_forecast.config import ENV
from service_ml_forecast.services.model_config_service import ModelConfigService
from service_ml_forecast.services.openremote_service import OpenRemoteService

logger = logging.getLogger(__name__)

__openremote_client = OpenRemoteClient(
    openremote_url=ENV.ML_OR_URL,
    keycloak_url=ENV.ML_OR_KEYCLOAK_URL,
    service_user=ENV.ML_OR_SERVICE_USER,
    service_user_secret=ENV.ML_OR_SERVICE_USER_SECRET,
)

__openremote_service = OpenRemoteService(__openremote_client)
__model_config_service = ModelConfigService(__openremote_service)


# --- Dependencies ---
def get_config_service() -> ModelConfigService:
    """
    Get the model config service dependency.
    """
    return __model_config_service


def get_openremote_service() -> OpenRemoteService:
    """
    Get the openremote service dependency.
    """
    return __openremote_service


def get_openremote_client() -> OpenRemoteClient:
    """
    Get the openremote client dependency.
    """
    return __openremote_client


def get_openremote_issuers() -> list[str] | None:
    """Get valid issuers from OpenRemote realms.

    Returns:
        List of valid issuer URLs or None if realms cannot be retrieved.
    """
    try:
        openremote_service = get_openremote_service()
        realms = openremote_service.get_realms()

        if realms is None:
            return None

        urls = []
        for realm in realms:
            urls.append(f"{ENV.ML_OR_URL}/auth/realms/{realm.name}")
        return urls
    except Exception as e:
        logger.error(f"Error getting issuers from OpenRemote: {e}", exc_info=True)
        return None


# --- Constants ---
OPENREMOTE_KC_RESOURCE = "openremote"

# --- OAuth2 Scheme ---
# This is used to allow authorization via the Docs and Redoc pages
# Does not validate the token, this should be done via a middleware or manually
OAUTH2_SCHEME = OAuth2PasswordBearer(
    tokenUrl=f"{ENV.ML_OR_KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
    scopes={"openid": "OpenID Connect", "profile": "User profile", "email": "User email"},
    description="Login into the OpenRemote Management -- Expected Client ID: 'openremote'",
    auto_error=False,
)
