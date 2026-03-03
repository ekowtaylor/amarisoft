"""Custom exceptions for the Amarisoft Callbox API client."""

from __future__ import annotations

from typing import Any


class AmariError(Exception):
    """Base exception for all Amarisoft-related errors."""


class AmariConnectionError(AmariError):
    """Raised when a WebSocket connection cannot be established or is lost."""


class ProxyConnectionError(AmariConnectionError):
    """Raised when a proxy tunnel cannot be established."""


class AuthenticationError(AmariError):
    """Raised when authentication with the Amarisoft service fails."""


class AmariTimeoutError(AmariError):
    """Raised when a request times out waiting for a response."""


class CommandError(AmariError):
    """Raised when the server returns an error response to a command.

    Attributes:
        error_code: Optional error code from the server response.
    """

    def __init__(self, message: str, error_code: int | str | None = None):
        super().__init__(message)
        self.error_code = error_code


class InvalidParameterError(AmariError):
    """Raised when invalid parameters are passed to an API method."""
