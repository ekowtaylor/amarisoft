"""HTTP over SSH client for Amarisoft REST API access (stdlib only).

This module provides an HTTP-compatible client that forwards requests through
an SSH tunnel using only Python standard library (no requests dependency).
"""

from __future__ import annotations

import json
import logging
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .exceptions import (
    APIError,
    AuthenticationError,
    SSHClientError,
    SSHConnectionError,
    SSHTimeoutError,
)

logger = logging.getLogger(__name__)


class HTTPOverSSHClient:
    """HTTP client that forwards requests through an SSH tunnel.

    Uses only Python standard library - no external dependencies required.

    Args:
        ssh_host: Hostname or IP of the SSH server (Amarisoft box).
        ssh_port: SSH port (default: 22).
        ssh_username: SSH username.
        ssh_password: SSH password (optional if using key-based auth).
        ssh_key_path: Path to SSH private key file (optional).
        remote_host: Host where REST API is running on the remote side.
        remote_port: Port of the REST API on the remote side (default: 9010).
        local_port: Local port for the tunnel (default: 19010).
        timeout: Request timeout in seconds.
        connect_timeout: SSH connection timeout in seconds.
    """

    def __init__(
        self,
        ssh_host: str,
        ssh_username: str,
        ssh_port: int = 22,
        ssh_password: str | None = None,
        ssh_key_path: str | None = None,
        remote_host: str = "localhost",
        remote_port: int = 9010,
        local_port: int = 19010,
        timeout: float = 30.0,
        retries: int = 3,
        api_key: str | None = None,
        connect_timeout: float = 10.0,
    ):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.ssh_key_path = ssh_key_path
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_port = local_port
        self.timeout = timeout
        self.api_key = api_key
        self.connect_timeout = connect_timeout
        self._retries = retries
        self._connected = False

    @property
    def connected(self) -> bool:
        """Return True if SSH tunnel is active."""
        if not self._connected:
            return False
        return self._is_port_in_use(self.local_port)

    @property
    def base_url(self) -> str:
        """Return the local tunnel URL."""
        return f"http://localhost:{self.local_port}"

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use."""
        for host in ("127.0.0.1", "::1"):
            try:
                family = socket.AF_INET if host == "127.0.0.1" else socket.AF_INET6
                with socket.socket(family, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    if s.connect_ex((host, port)) == 0:
                        return True
            except OSError:
                continue
        return False

    def _cleanup_port(self, port: int) -> bool:
        """Kill any process using the specified port."""
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                time.sleep(2)
                return True
        except FileNotFoundError:
            try:
                subprocess.run(["pkill", "-f", f"ssh.*{port}"], capture_output=True)
                time.sleep(2)
            except Exception:
                pass
        except Exception:
            pass
        return False

    def _check_sshpass_available(self) -> bool:
        """Check if sshpass is available."""
        try:
            subprocess.run(["sshpass", "-V"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def connect(self) -> None:
        """Establish SSH tunnel."""
        if self.connected:
            return

        self._cleanup_port(self.local_port)

        ssh_args = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            f"ConnectTimeout={int(self.connect_timeout)}",
            "-f",
            "-N",
            "-L",
            f"{self.local_port}:{self.remote_host}:{self.remote_port}",
        ]

        if self.ssh_port != 22:
            ssh_args.extend(["-p", str(self.ssh_port)])

        if self.ssh_key_path:
            key_path = os.path.expanduser(self.ssh_key_path)
            ssh_args.extend(["-i", key_path])

        ssh_args.append(f"{self.ssh_username}@{self.ssh_host}")

        if self.ssh_password:
            if not self._check_sshpass_available():
                raise SSHConnectionError(
                    "sshpass is required for password authentication. "
                    "Install with: yum install sshpass"
                )
            ssh_command = ["sshpass", "-p", self.ssh_password] + ssh_args
        else:
            ssh_command = ssh_args

        logger.info(
            "Creating SSH tunnel: localhost:%d -> %s:%d via %s@%s",
            self.local_port,
            self.remote_host,
            self.remote_port,
            self.ssh_username,
            self.ssh_host,
        )

        try:
            result = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                timeout=self.connect_timeout + 5,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                if "Permission denied" in error_msg:
                    raise SSHConnectionError(f"SSH authentication failed: {error_msg}")
                raise SSHConnectionError(f"SSH tunnel failed: {error_msg}")

        except subprocess.TimeoutExpired as e:
            raise SSHTimeoutError(f"SSH connection timed out: {e}") from e
        except FileNotFoundError as e:
            raise SSHConnectionError(f"SSH command not found: {e}") from e

        time.sleep(1)

        if not self._is_port_in_use(self.local_port):
            raise SSHConnectionError(
                f"SSH tunnel created but port {self.local_port} is not listening."
            )

        self._connected = True
        logger.info("SSH tunnel established: localhost:%d", self.local_port)

    def close(self) -> None:
        """Close SSH tunnel."""
        self._cleanup_port(self.local_port)
        self._connected = False
        logger.info("SSH tunnel closed")

    def reconnect(self) -> None:
        """Close and re-establish the SSH tunnel."""
        self.close()
        self.connect()

    def _ensure_connected(self) -> None:
        """Ensure tunnel is connected."""
        if not self.connected:
            raise SSHConnectionError("SSH tunnel not connected. Call connect() first.")

    def _build_url(self, endpoint: str, params: dict | None = None) -> str:
        """Build full URL from endpoint."""
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        url = f"{self.base_url}{endpoint}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"
        return url

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request through tunnel."""
        self._ensure_connected()

        url = self._build_url(endpoint, params)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        for attempt in range(self._retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    response_data = resp.read().decode("utf-8")
                    return json.loads(response_data) if response_data else {}

            except urllib.error.HTTPError as e:
                try:
                    error_body = e.read().decode("utf-8")
                    error_data = json.loads(error_body)
                except Exception:
                    error_data = {"error": str(e)}

                if e.code == 401:
                    raise AuthenticationError(error_data.get("error", "Auth failed"))

                raise APIError(
                    message=error_data.get("error", f"HTTP {e.code}"),
                    status_code=e.code,
                    error_code=error_data.get("error_code"),
                    detail=error_data.get("detail"),
                )

            except urllib.error.URLError as e:
                if attempt < self._retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise SSHConnectionError(f"Request failed: {e}") from e

            except TimeoutError as e:
                raise SSHTimeoutError(f"Request to {endpoint} timed out") from e

        raise SSHClientError("Request failed after retries")

    def get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make a GET request through the SSH tunnel."""
        return self._make_request("GET", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make a POST request through the SSH tunnel."""
        return self._make_request("POST", endpoint, data=data, params=params)

    def put(self, endpoint: str, data: dict | None = None) -> dict[str, Any]:
        """Make a PUT request through the SSH tunnel."""
        return self._make_request("PUT", endpoint, data=data)

    def delete(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make a DELETE request through the SSH tunnel."""
        return self._make_request("DELETE", endpoint, params=params)

    def health_check(self) -> dict[str, Any]:
        """Check if the REST API service is healthy."""
        return self.get("/health")

    def is_listening(self, timeout: float = 2.0) -> bool:
        """Check if the SSH host is reachable."""
        try:
            with socket.create_connection(
                (self.ssh_host, self.ssh_port), timeout=timeout
            ):
                return True
        except OSError:
            return False

    def is_tunnel_active(self) -> bool:
        """Check if the SSH tunnel is active."""
        return self.connected

    def __enter__(self) -> "HTTPOverSSHClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        status = "connected" if self.connected else "disconnected"
        return f"HTTPOverSSHClient({self.ssh_username}@{self.ssh_host}, {status})"
