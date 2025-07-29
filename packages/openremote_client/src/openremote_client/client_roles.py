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

"""
This module contains the client roles for the OpenRemote API.
"""


class ClientRoles:
    """Client roles for the OpenRemote API."""

    READ_LOGS_ROLE = "read:logs"
    READ_USERS_ROLE = "read:users"
    READ_ADMIN_ROLE = "read:admin"
    READ_MAP_ROLE = "read:map"
    READ_ASSETS_ROLE = "read:assets"
    READ_RULES_ROLE = "read:rules"
    READ_INSIGHTS_ROLE = "read:insights"
    READ_ALARMS_ROLE = "read:alarms"
    READ_SERVICES_ROLE = "read:services"
    WRITE_SERVICES_ROLE = "write:services"
    WRITE_USER_ROLE = "write:user"
    WRITE_ADMIN_ROLE = "write:admin"
    WRITE_LOGS_ROLE = "write:logs"
    WRITE_ASSETS_ROLE = "write:assets"
    WRITE_ATTRIBUTES_ROLE = "write:attributes"
    WRITE_RULES_ROLE = "write:rules"
