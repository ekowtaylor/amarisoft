"""SSH client package for Amarisoft REST API access via SSH tunnel."""

from .client import HTTPOverSSHClient
from .exceptions import (
    SSHClientError,
    SSHConnectionError,
    SSHTimeoutError,
    SSHTunnelError,
)

__all__ = [
    "HTTPOverSSHClient",
    "SSHClientError",
    "SSHConnectionError",
    "SSHTimeoutError",
    "SSHTunnelError",
]
