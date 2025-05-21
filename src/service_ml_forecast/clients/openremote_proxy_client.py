from service_ml_forecast.clients.openremote.openremote_client import OAuthTokenResponse, OpenRemoteClient


class OpenRemoteProxyClient(OpenRemoteClient):
    """Override the OpenRemoteClient to use a provided token instead of authenticating.

    Used for directly proxying requests to the OpenRemote API, using the provided token.

    Args:
        openremote_url: The URL of the OpenRemote API.
        token: The authentication token to use for requests.
    """

    def __init__(self, openremote_url: str, token: str):
        # Skip parent class initialization to avoid authentication
        self.openremote_url = openremote_url
        self.keycloak_url = ""  # Not used in proxy client
        self.service_user = ""  # Not used in proxy client
        self.service_user_secret = ""  # Not used in proxy client
        self.timeout = 60.0

        # Set up token directly
        self.oauth_token = OAuthTokenResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=3600,  # Default expiration, not used since we don't refresh
        )
        self.token_expiration_timestamp = None  # We don't expire the token

    def __authenticate(self) -> bool:
        # Override authentication to always return True
        return True

    def __check_and_refresh_auth(self) -> bool:
        # Override token refresh to always return True
        return True
