"""Service ML Forecast application."""

import logging.config
from pathlib import Path

import tomli
from pydantic import BaseModel

from service_ml_forecast.logging_config import LOGGING_CONFIG

# Load the logging configuration
logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)


class AppInfo(BaseModel):
    """Application information."""

    name: str
    description: str
    version: str


def get_app_info() -> AppInfo | None:
    """Read app info (name, description, version) from pyproject.toml file."""
    try:
        pyproject_path = Path(__file__).parents[2] / "pyproject.toml"

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)

        return AppInfo(**pyproject_data["project"])
    except (FileNotFoundError, KeyError, tomli.TOMLDecodeError):
        logger.exception("Failed to read app info")
        return None


__app_info__ = get_app_info()
