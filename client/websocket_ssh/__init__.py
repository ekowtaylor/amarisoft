"""WebSocket client package for Amarisoft Remote API access via SSH tunnel."""

from .client import WebSocketOverSSHClient
from .exceptions import (
    SSHClientError,
    SSHConnectionError,
    SSHTimeoutError,
    SSHTunnelError,
)

__all__ = [
    "WebSocketOverSSHClient",
    "SSHClientError",
    "SSHConnectionError",
    "SSHTimeoutError",
    "SSHTunnelError",
]
