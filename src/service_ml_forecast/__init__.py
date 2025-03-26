"""Service ML Forecast application."""

from pathlib import Path

import tomli
from pydantic import BaseModel


class AppInfo(BaseModel):
    """Application information."""

    name: str
    description: str
    version: str


def find_project_root(start_path: Path = Path(__file__)) -> Path:
    """Find the project root by looking for marker files."""
    current = start_path.parent
    while current != current.parent:
        if any((current / marker).exists() for marker in [".git", "pyproject.toml", "setup.py"]):
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")


def get_app_info() -> AppInfo | None:
    """Read app info (name, description, version) from pyproject.toml file."""
    try:
        pyproject_path = Path(__file__).parents[2] / "pyproject.toml"

        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)

        return AppInfo(**pyproject_data["project"])
    except (FileNotFoundError, KeyError, tomli.TOMLDecodeError):
        return None


__app_info__ = get_app_info()
