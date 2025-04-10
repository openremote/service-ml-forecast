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
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
This module contains the dependency injectors for the service.

The injectors are used to inject the services into the FastAPI app, or other dependencies.
"""

from service_ml_forecast.clients.openremote.openremote_client import OpenRemoteClient
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
__model_config_service = ModelConfigService()

# --- Dependencies ---
# These can be monkeypatched for testing purposes

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
