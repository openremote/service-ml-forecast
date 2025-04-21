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

from dataclasses import dataclass
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from service_ml_forecast import find_project_root

PROJECT_ROOT = find_project_root()


@dataclass
class DirectoryConstants:
    """Directory paths constants. Tests can override these constants."""

    ML_BASE_DIR: Path = PROJECT_ROOT  # base directory for the service
    ML_MODELS_DIR: Path = ML_BASE_DIR / "deployment/data/models"  # directory for the models
    ML_CONFIGS_DIR: Path = ML_BASE_DIR / "deployment/data/configs"  # directory for the configs
    ML_WEB_DIST_DIR: Path = ML_BASE_DIR / "deployment/web/dist"  # directory for the web dist


class AppEnvironment(BaseSettings):
    """Application environment settings.

    All settings can be overridden via environment variables.

    The environment variables are prefixed with "ML_" to avoid conflicts with other services.
    """

    # Logging
    ML_LOG_LEVEL: str = "INFO"  # log level to use
    ML_ENVIRONMENT: str = "development"  # environment to run the service in

    # FastAPI Settings
    ML_API_PUBLISH_DOCS: bool = True  # whether to make the openapi docs available

    # Uvicorn Settings
    ML_WEBSERVER_HOST: str = "0.0.0.0"  # host to bind the web server (uvicorn) to
    ML_WEBSERVER_PORT: int = 8000  # port to bind the web server (uvicorn) to
    ML_WEBSERVER_ORIGINS: list[str] = ["http://localhost:8000", "http://localhost:8001"]  # origins to allow
    ML_API_ROOT_PATH: str = (
        "/services/ml-forecast"  # when running behind a reverse proxy, the root path of the fastapi app
    )

    # OpenRemote Settings
    ML_OR_URL: str = "http://localhost:8080"  # OpenRemote URL
    ML_OR_KEYCLOAK_URL: str = "http://localhost:8081/auth"  # OpenRemote Keycloak URL
    ML_OR_SERVICE_USER: str = "serviceuser"  # OpenRemote service user
    ML_OR_SERVICE_USER_SECRET: str = "secret"  # OpenRemote service user secret

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def is_production(self) -> bool:
        """Check if the environment is production."""
        return self.ML_ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """Check if the environment is development."""
        return self.ML_ENVIRONMENT == "development"


DIRS = DirectoryConstants()
ENV = AppEnvironment()
