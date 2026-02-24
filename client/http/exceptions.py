"""HTTP client exceptions."""

from __future__ import annotations


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ConnectionError(HTTPClientError):
    """Raised when connection to the REST API service fails."""

    def __init__(self, message: str = "Failed to connect to REST API service"):
        super().__init__(message)


class TimeoutError(HTTPClientError):
    """Raised when a request times out."""

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message)


class AuthenticationError(HTTPClientError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class APIError(HTTPClientError):
    """Raised when the API returns an error response."""

    def __init__(
        self,
        message: str,
        status_code: int,
        error_code: str | None = None,
        detail: str | None = None,
    ):
        self.error_code = error_code
        self.detail = detail
        super().__init__(message, status_code)

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.detail:
            parts.append(f": {self.detail}")
        return " ".join(parts)
