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

"""Common exceptions."""


class ResourceNotFoundError(Exception):
    """Exception raised when a resource is not found."""

    pass


class ResourceAlreadyExistsError(Exception):
    """Exception raised when a resource already exists."""

    pass


class ResourceDependencyError(Exception):
    """Exception raised when a resource dependency is invalid."""

    pass


class ExternalApiError(Exception):
    """Exception raised when an external API call fails."""

    pass
