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


from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from service_ml_forecast import find_project_root

PROJECT_ROOT = find_project_root()


class AppEnvironment(BaseSettings):
    """Application environment settings.

    All settings can be overridden via environment variables.

    The environment variables are prefixed with "ML_" to avoid conflicts with other services.
    """

    # Logging
    ML_LOG_LEVEL: str = "INFO"

    # Environment
    ML_ENVIRONMENT: str = "development"

    # File paths
    ML_BASE_DIR: Path = PROJECT_ROOT
    ML_MODELS_DIR: Path = ML_BASE_DIR / "deployment/data/models"
    ML_CONFIGS_DIR: Path = ML_BASE_DIR / "deployment/data/configs"

    # FastAPI Settings
    ML_PUBLISH_DOCS: bool = True  # whether to make the docs available

    # OpenRemote Settings
    ML_OR_URL: str = "http://localhost:8080"
    ML_OR_KEYCLOAK_URL: str = "http://localhost:8081"
    ML_OR_SERVICE_USER: str = "serviceuser"
    ML_OR_SERVICE_USER_SECRET: str = "secret"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", env_file_encoding="utf-8")

    def is_production(self) -> bool:
        """Check if the environment is production."""
        return self.ML_ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """Check if the environment is development."""
        return self.ML_ENVIRONMENT == "development"


ENV = AppEnvironment()
