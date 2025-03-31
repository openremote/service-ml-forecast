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

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(BaseSettings):
    """Application environment settings.

    All settings can be overridden via environment variables.
    """

    # Application Settings
    PUBLISH_DOCS: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"

    # Environment
    ENV: str = "development"

    # OpenRemote Settings
    OPENREMOTE_URL: str = "http://localhost:8080"
    OPENREMOTE_KEYCLOAK_URL: str = "http://localhost:8081"
    OPENREMOTE_SERVICE_USER: str = "serviceuser"
    OPENREMOTE_SERVICE_USER_SECRET: str = "secret"

    model_config = SettingsConfigDict(case_sensitive=True, env_prefix="", env_file=".env", env_file_encoding="utf-8")

    def is_production(self) -> bool:
        """Check if the environment is production."""
        return self.ENV == "production"

    def is_development(self) -> bool:
        """Check if the environment is development."""
        return self.ENV == "development"


# Clear environment before initialization
os.environ.clear()
ENV = AppEnvironment()
