"""Exceptions for SSH tunnel client."""

from __future__ import annotations


class SSHClientError(Exception):
    """Base exception for SSH client errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class SSHConnectionError(SSHClientError):
    """Raised when SSH connection fails."""

    pass


class SSHTimeoutError(SSHClientError):
    """Raised when SSH operation times out."""

    pass


class SSHTunnelError(SSHClientError):
    """Raised when SSH tunnel creation or operation fails."""

    pass


class APIError(SSHClientError):
    """Raised when API returns an error response."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        detail: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        return " ".join(parts)


class AuthenticationError(SSHClientError):
    """Raised when authentication fails."""

    pass
