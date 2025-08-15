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
Keycloak models.

These models are used to handle the Keycloak token payload and provide
a context for the user.
"""

from collections.abc import Callable

from pydantic import BaseModel


class KeycloakTokenPayload(BaseModel):
    """Partial payload of the JWT token for handling resource access."""

    class RealmAccess(BaseModel):
        roles: list[str]

    class ResourceAccess(BaseModel):
        roles: list[str]

    exp: int
    iss: str
    azp: str
    realm_access: RealmAccess
    resource_access: dict[str, ResourceAccess]
    preferred_username: str


class UserContext:
    """Context for the user."""

    MASTER_REALM = "master"

    def __init__(self, token_payload: KeycloakTokenPayload):
        self.token_payload = token_payload

    def get_username(self) -> str:
        return self.token_payload.preferred_username

    """
    Returns the authenticated realm name.
    """

    def get_authenticated_realm_name(self) -> str:
        return self.token_payload.iss.split("/")[-1]

    """
    Checks if the user has a specific realm role.
    """

    def has_realm_role(self, role: str) -> bool:
        return role in self.token_payload.realm_access.roles

    """
    Checks if the user has a specific resource role.
    """

    def has_resource_role(self, resource: str, role: str) -> bool:
        return role in self.token_payload.resource_access[resource].roles

    """
    Checks if the user has any of the specified resource roles.
    """

    def has_any_resource_role(self, resource: str, roles: list[str]) -> bool:
        return any(role in self.token_payload.resource_access[resource].roles for role in roles)

    """
    Checks if the user is a super user.
    """

    def is_super_user(self) -> bool:
        return self.has_realm_role("admin") and self.get_authenticated_realm_name() == self.MASTER_REALM

    def is_realm_accessible_by_user(self, realm: str) -> bool:
        return self.get_authenticated_realm_name() == realm or self.is_super_user()


# Type alias for issuer provider functions
IssuerProvider = Callable[[], list[str] | None]
