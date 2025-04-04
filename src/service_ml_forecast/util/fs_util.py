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
    def save_file(content: str, path: Path) -> bool:
        """Atomically save content to a file.

        Args:
            content: The content to save.
            path: Path to the file
        """
        try:
            dir_path = path.parent

            dir_path.mkdir(parents=True, exist_ok=True)

            with tempfile.NamedTemporaryFile(mode="w", dir=dir_path, delete=False) as temp_file:
                temp_file.write(content)
                temp_file.flush()

                # Replace the existing file with the new content
                Path(temp_file.name).replace(path)

            logger.debug(f"Saved content to {path}")
            return True
        except OSError as e:
            logger.exception(f"Failed to save content to {path}: {e!s}")
            return False

    @staticmethod
    def read_file(path: Path) -> str | None:
        """Load content from a file.

        Args:
            path: Path to the file
        """
        try:
            content = path.read_text()
            logger.debug(f"Loaded content from {path}")
            return content
        except FileNotFoundError:
            logger.error(f"File not found: {path}")
            return None
        except OSError as e:
            logger.exception(f"Failed to read file {path}: {e!s}")
            return None

    @staticmethod
    def get_all_file_names(path: Path, extension: str) -> list[str]:
        """Get all files in a directory.

        Args:
            path: Path to the directory

        Returns:
            A list of all the file names in the directory
        """
        try:
            files = [f.name for f in path.glob(f"*.{extension}")]
            logger.debug(f"Found {len(files)} files in {path}")
            return files
        except FileNotFoundError:
            logger.error(f"Directory not found: {path}")
            return []
        except OSError as e:
            logger.exception(f"Failed to list files in {path}: {e!s}")
            return []

    @staticmethod
    def delete_file(path: Path) -> bool:
        """Delete a file.

        Args:
            path: Path to the file

        Returns:
            True if the file was deleted successfully, False if an error occurred.
        """
        try:
            path.unlink(missing_ok=True)  # missing_ok=True prevents FileNotFoundError
            logger.debug(f"Deleted content from {path}")
            return True
        except OSError as e:
            logger.exception(f"Failed to delete file {path}: {e!s}")
            return False

    @staticmethod
    def file_exists(path: Path) -> bool:
        """Check if a file exists.

        Args:
            path: Path to the file
        """
        return path.exists()
