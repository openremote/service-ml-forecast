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
    """Utility class for file system operations.

    Methods raise OSError if any IO operation fails.
    """

    @staticmethod
    def save_file(content: str, relative_path: str) -> bool:
        """Atomically save content to a file.

        Args:
            content: The content to save.
            path: Relative path from the project root

        Returns:
            True if the content was saved successfully.
        """
        file_path = f"{find_project_root()}{relative_path}"
        dir_path = os.path.dirname(file_path)

        os.makedirs(dir_path, exist_ok=True)

        with tempfile.NamedTemporaryFile(mode="w", dir=dir_path, delete=False) as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())

            # Replace the existing file with the new content
            os.replace(temp_file.name, file_path)

        logger.debug(f"Saved content to {file_path}")
        return True

    @staticmethod
    def read_file(relative_path: str) -> str:
        """Load content from a file.

        Args:
            path: Relative path from the project root

        Returns:
            The file contents.
        """
        file_path = f"{find_project_root()}{relative_path}"
        try:
            with open(file_path) as file:
                logger.debug(f"Loaded content from {file_path}")
                return file.read()
        except OSError as e:
            raise e

    @staticmethod
    def get_all_file_names(relative_path: str, extension: str) -> list[str]:
        """Get all files in a directory.

        Args:
            path: Relative path from the project root
            extension: The extension of the files to get.

        Returns:
            A list of all the file names in the directory.
        """
        file_path = f"{find_project_root()}{relative_path}"
        files = [f for f in os.listdir(file_path) if f.endswith(extension)]
        logger.debug(f"Found {len(files)} files in {relative_path}")
        return files

    @staticmethod
    def delete_file(relative_path: str) -> bool:
        """Delete a file.

        Args:
            path: Relative path from the project root

        Returns:
            True if the file was deleted successfully.
        """
        file_path = f"{find_project_root()}{relative_path}"
        os.remove(file_path)
        logger.debug(f"Deleted content from {file_path}")
        return True

    @staticmethod
    def delete_directory(relative_path: str) -> bool:
        """Delete a directory.

        Args:
            path: Relative path from the project root

        Returns:
            True if the directory was deleted successfully.
        """
        file_path = f"{find_project_root()}{relative_path}"
        shutil.rmtree(file_path)
        logger.debug(f"Deleted directory {file_path}")
        return True
