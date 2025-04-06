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

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class FsUtil:
    """Utility class for file system operations."""

    @staticmethod
    def save_file(content: str, path: Path) -> None:
        """Atomically save content to a file."""

        dir_path = path.parent

        dir_path.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(mode="w", dir=dir_path, delete=False) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            Path(temp_file.name).replace(path)

    @staticmethod
    def read_file(path: Path) -> str:
        """Read the contents from a file."""

        content = path.read_text()
        return content

    @staticmethod
    def get_all_file_names(path: Path, extension: str) -> list[str]:
        """Get all files in a directory."""

        files = [f.name for f in path.glob(f"*.{extension}")]
        return files

    @staticmethod
    def delete_file(path: Path) -> None:
        """Delete a file."""

        path.unlink()
