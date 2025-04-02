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


def _find_project_root(start_path: Path = Path(__file__)) -> Path:
    """Find the project root by looking for marker files."""
    current = start_path.parent
    while current != current.parent:
        if any((current / marker).exists() for marker in ["pyproject.toml", ".env"]):
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")


ENVFILE = Path(_find_project_root()) / ".env"


class AppEnvironment(BaseSettings):
    """Application environment settings.

    All settings can be overridden via environment variables.
    """

    # Application Settings
    PUBLISH_DOCS: bool = True
    BASE_DIR: Path = _find_project_root()
    MODELS_DIR: Path = BASE_DIR / "deployment/data/models"
    CONFIGS_DIR: Path = BASE_DIR / "deployment/data/configs"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Environment
    ENV: str = "development"

    # OpenRemote Settings
    OPENREMOTE_URL: str = "http://localhost:8080"
    OPENREMOTE_KEYCLOAK_URL: str = "http://localhost:8081"
    OPENREMOTE_SERVICE_USER: str = "serviceuser"
    OPENREMOTE_SERVICE_USER_SECRET: str = "secret"

    model_config = SettingsConfigDict(case_sensitive=True, env_prefix="", env_file=ENVFILE, env_file_encoding="utf-8")

    def is_production(self) -> bool:
        """Check if the environment is production."""
        return self.ENV == "production"

    def is_development(self) -> bool:
        """Check if the environment is development."""
        return self.ENV == "development"


ENV = AppEnvironment()
