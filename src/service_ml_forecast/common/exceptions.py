"""Common exceptions."""


class ResourceNotFoundError(Exception):
    """Exception raised when a resource is not found."""

    pass


class ResourceAlreadyExistsError(Exception):
    """Exception raised when a resource already exists."""

    pass


class ExternalApiError(Exception):
    """Exception raised when an external API call fails."""

    pass
