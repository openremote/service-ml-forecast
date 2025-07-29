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
Keycloak constants.

These constants are used to configure the Keycloak middleware, decorators
hold common error messages.
"""

# Constants for JWT and JWKS configuration
JWKS_CACHE_TTL_SECONDS = 600  # 10 minutes
JWKS_REQUEST_TIMEOUT_SECONDS = 10.0
JWKS_ENDPOINT_PATH = "/protocol/openid-connect/certs"

# JWT token constants
JWT_ALGORITHM_RS256 = "RS256"
JWT_KEY_TYPE_RSA = "RSA"
JWT_KEY_USE_SIGNATURE = "sig"

# Common error messages
ERROR_MISSING_AUTH_HEADER = "Missing or malformed Authorization header"
ERROR_INVALID_TOKEN = "Invalid token"
ERROR_TOKEN_EXPIRED = "Token has expired"
ERROR_INSUFFICIENT_PERMISSIONS = "Insufficient permissions"
ERROR_REALM_REQUIRED = "Realm is required"
ERROR_USER_NOT_AUTHENTICATED = "User not authenticated"
ERROR_INTERNAL_SERVER_ERROR = "Internal server error"
ERROR_UNEXPECTED_ERROR = "An unexpected error occurred"
