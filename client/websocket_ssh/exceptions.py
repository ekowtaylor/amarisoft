"""Exceptions for WebSocket over SSH tunnel client."""


class SSHClientError(Exception):
    """Base exception for SSH client errors."""

    pass


class SSHConnectionError(SSHClientError):
    """Raised when SSH connection cannot be established."""

    pass


class SSHTimeoutError(SSHClientError):
    """Raised when SSH operation times out."""

    pass


class SSHTunnelError(SSHClientError):
    """Raised when SSH tunnel creation or operation fails."""

    pass
