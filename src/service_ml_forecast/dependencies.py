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

from fastapi.security import OAuth2PasswordBearer
from openremote_client import OpenRemoteClient

from service_ml_forecast.config import ENV
from service_ml_forecast.services.model_config_service import ModelConfigService
from service_ml_forecast.services.openremote_service import OpenRemoteService

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


# --- OAuth2 Scheme ---
# This is used to allow authorization via the Docs and Redoc pages
# Also allows us to extract the token easily from the Authorization header
# Does not validate the token, this is done in the KeycloakMiddleware!
__realm_name = "master"
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{ENV.ML_OR_KEYCLOAK_URL}/realms/{__realm_name}/protocol/openid-connect/token",
    scopes={"openid": "OpenID Connect", "profile": "User profile", "email": "User email"},
    description="Login into the OpenRemote Management -- Expected Client ID: 'openremote'",
    auto_error=False,
)
