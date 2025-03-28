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
import os
import shutil
import tempfile

from service_ml_forecast import find_project_root

logger = logging.getLogger(__name__)


class FsUtil:
    """Utility class for file system operations."""

    @staticmethod
    def save_file(content: str, relative_path: str) -> bool:
        """Atomically save content to a file.

        Args:
            content: The content to save.
            path: The relative path from the project root to save the content to.

        Returns:
            True if the content was saved successfully, False otherwise.
        """
        file_path = f"{find_project_root()}{relative_path}"
        dir_path = os.path.dirname(file_path)

        try:
            # Create directory if it doesn't exist
            os.makedirs(dir_path, exist_ok=True)

            with tempfile.NamedTemporaryFile(mode="w", dir=dir_path, delete=False) as temp_file:
                temp_file.write(content)
                temp_file.flush()
                os.fsync(temp_file.fileno())

                # Rename the temporary file to the target file
                os.replace(temp_file.name, file_path)

            logger.info(f"Successfully saved content to {file_path}")
            return True
        except OSError as e:
            logger.error(f"Failed to save content to {file_path}: {e}")
            return False

    @staticmethod
    def read_file(relative_path: str) -> str | None:
        """Load content from a file.

        Args:
            path: The relative path from the project root to load the content from.

        Returns:
            The content, or None if the content could not be loaded.
        """
        file_path = f"{find_project_root()}{relative_path}"
        try:
            with open(file_path) as file:
                logger.info(f"Successfully loaded content from {file_path}")
                return file.read()
        except FileNotFoundError:
            logger.error(f"Failed to load content from {file_path}")
            return None

    @staticmethod
    def get_all_file_names(relative_path: str, extension: str) -> list[str]:
        """Get all files in a directory.

        Args:
            path: The relative path from the project root to get the files from.
            extension: The extension of the files to get.

        Returns:
            A list of all the files in the directory.
        """
        try:
            file_path = f"{find_project_root()}{relative_path}"
            files = [f for f in os.listdir(file_path) if f.endswith(extension)]
            logger.info(f"Successfully returned {len(files)} files from {relative_path}")
            return files
        except OSError as e:
            logger.error(f"Failed to get all files from {relative_path}: {e}")
            return []

    @staticmethod
    def delete_file(relative_path: str) -> bool:
        """Delete content from a file.

        Args:
            path: The relative path from the project root to delete the content from.

        Returns:
            True if the content was deleted successfully, False otherwise.
        """
        file_path = f"{find_project_root()}{relative_path}"
        try:
            os.remove(file_path)
            logger.info(f"Successfully deleted content from {file_path}")
            return True
        except OSError as e:
            logger.error(f"Failed to delete content from {file_path}: {e}")
            return False

    @staticmethod
    def delete_directory(relative_path: str) -> bool:
        """Delete a directory.

        Args:
            path: The relative path from the project root to delete the directory from and all its contents.
        """
        file_path = f"{find_project_root()}{relative_path}"
        try:
            shutil.rmtree(file_path)
            logger.info(f"Successfully deleted directory {file_path}")
            return True
        except OSError as e:
            logger.error(f"Failed to delete directory {file_path}: {e}")
            return False
