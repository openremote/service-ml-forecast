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
        if any((current / marker).exists() for marker in [".git", "pyproject.toml", "Makefile"]):
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
