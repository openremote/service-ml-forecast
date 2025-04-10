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

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class FsUtil:
    """Utility class for file system operations."""

    @staticmethod
    def create_file(path: Path, content: str, overwrite: bool = False) -> None:
        """Create a new file atomically.

        Args:
            path: Path where the new file should be created
            content: Content to write to the file
            overwrite: Whether to overwrite an existing file

        Raises:
            FileExistsError: If the file already exists and overwrite is False
        """
        if path.exists() and not overwrite:
            raise FileExistsError(f"Cannot create file that already exists: {path}")

        # Create the parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        FsUtil._atomic_write(path, content)

    @staticmethod
    def update_file(path: Path, content: str) -> None:
        """Update an existing file atomically. Fails if the file doesn't exist.

        Args:
            path: Path to the file to update
            content: New content to write to the file

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Cannot update file that doesn't exist: {path}")

        FsUtil._atomic_write(path, content)

    @staticmethod
    def read_file(path: Path) -> str:
        """Read the contents from a file."

        Args:
            path: Path to read from

        Returns:
            Contents of the file

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        return path.read_text()

    @staticmethod
    def get_files_in_dir(path: Path, extension: str) -> list[Path]:
        """Get all files in a directory with the given extension.

        Args:
            path: Path to directory
            extension: Extension to filter by

        Returns:
            List of files with the given extension
        """
        files = list(path.glob(f"*.{extension}"))
        return files

    @staticmethod
    def delete_file(path: Path) -> None:
        """Delete a file.

        Args:
            path: Path to file

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        path.unlink()

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        """Write a file atomically."""

        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            temp_path = Path(temp_file.name)

        temp_path.replace(path)
