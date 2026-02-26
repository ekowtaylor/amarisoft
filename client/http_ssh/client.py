"""HTTP over SSH client for Amarisoft REST API access.

This module provides an HTTP-compatible client that forwards requests through
an SSH tunnel. This allows accessing the Amarisoft REST API from remote
machines without exposing the HTTP port directly.

The HTTPOverSSHClient has the same interface as HTTPClient, making it easy
to switch between direct HTTP and SSH tunnel access.
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import subprocess
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

    This client provides the same interface as HTTPClient, allowing you to
    access the Amarisoft REST API through an SSH tunnel. This is useful when:
    - The REST API is only listening on localhost
    - You want to access the API securely over SSH
    - Firewall rules prevent direct HTTP access

    Uses the system's SSH client via subprocess for reliable tunnel creation.

    Args:
        ssh_host: Hostname or IP of the SSH server (Amarisoft box).
        ssh_port: SSH port (default: 22).
        ssh_username: SSH username.
        ssh_password: SSH password (optional if using key-based auth).
        ssh_key_path: Path to SSH private key file (optional).
        remote_host: Host where REST API is running on the remote side (default: localhost).
        remote_port: Port of the REST API on the remote side (default: 9010).
        local_port: Local port for the tunnel (default: 19010).
        timeout: Request timeout in seconds.
        retries: Number of retries for failed requests.
        api_key: Optional API key for REST API authentication.
        connect_timeout: SSH connection timeout in seconds.

    Example::

        # Using password authentication
        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_password="amarisoft",
        )

        with client:
            # Use exactly like HTTPClient
            response = client.get("/enb/stats")
            print(response)

        # Using key-based authentication
        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_key_path="~/.ssh/id_rsa",
        )
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

        # Connection state
        self._connected = False

        # HTTP session (created when tunnel is established)
        self._session: requests.Session | None = None

    @property
    def connected(self) -> bool:
        """Return True if SSH tunnel is active."""
        if not self._connected:
            return False
        # Verify tunnel is still working by checking if port is in use
        return self._is_port_in_use(self.local_port)

    @property
    def base_url(self) -> str:
        """Return the local tunnel URL."""
        return f"http://localhost:{self.local_port}"

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is in use (supports both IPv4 and IPv6).

        Attempts to connect to the port on localhost using both IPv4 and IPv6.
        Returns True if either connection succeeds.

        Args:
            port: Port number to check.

        Returns:
            True if port is in use, False otherwise.
        """
        # Try both IPv4 and IPv6 localhost addresses
        for host in ("127.0.0.1", "::1"):
            try:
                family = socket.AF_INET if host == "127.0.0.1" else socket.AF_INET6
                with socket.socket(family, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    if s.connect_ex((host, port)) == 0:
                        return True
            except OSError:
                # IPv6 may not be available on all systems
                continue
        return False

    def _cleanup_port(self, port: int) -> bool:
        """Kill any process using the specified port."""
        logger.debug("Checking for existing processes on port %d...", port)
        try:
            # Method 1: Using lsof
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        logger.debug("Killing process %s using port %d...", pid, port)
                        os.kill(int(pid), signal.SIGTERM)
                    except ProcessLookupError:
                        logger.debug("Process %s already gone", pid)
                time.sleep(2)  # Give processes time to clean up
                logger.debug("Cleaned up port %d", port)
                return True
            else:
                logger.debug("Port %d is free", port)
                return False
        except FileNotFoundError:
            # lsof not available, try ss
            logger.debug("lsof not found, trying alternative method...")
            try:
                result = subprocess.run(
                    ["ss", "-lptn", f"sport = :{port}"],
                    capture_output=True,
                    text=True,
                )
                if f":{port}" in result.stdout:
                    logger.debug(
                        "Port %d appears in use, attempting to kill SSH tunnels...",
                        port,
                    )
                    subprocess.run(
                        ["pkill", "-f", f"ssh.*{port}"], capture_output=True
                    )
                    time.sleep(2)
                    return True
            except Exception:
                pass
        except Exception as e:
            logger.debug("Note during cleanup: %s", e)

        return False

    def _check_sshpass_available(self) -> bool:
        """Check if sshpass is available for password authentication."""
        try:
            subprocess.run(
                ["sshpass", "-V"],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def connect(self) -> None:
        """Establish SSH tunnel.

        Raises:
            SSHConnectionError: If SSH connection fails.
            SSHTimeoutError: If connection times out.
        """
        if self.connected:
            logger.debug("Tunnel already connected")
            return

        # Clean up any existing process on the local port
        self._cleanup_port(self.local_port)

        # Build SSH command
        ssh_args = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ExitOnForwardFailure=yes",
            "-o", f"ConnectTimeout={int(self.connect_timeout)}",
            "-f", "-N",  # Background and no command
            "-L", f"{self.local_port}:{self.remote_host}:{self.remote_port}",
        ]

        # Add port if not default
        if self.ssh_port != 22:
            ssh_args.extend(["-p", str(self.ssh_port)])

        # Add key file if specified
        if self.ssh_key_path:
            key_path = os.path.expanduser(self.ssh_key_path)
            ssh_args.extend(["-i", key_path])

        # Add destination
        ssh_args.append(f"{self.ssh_username}@{self.ssh_host}")

        # Use sshpass for password authentication if password provided
        if self.ssh_password:
            if not self._check_sshpass_available():
                raise SSHConnectionError(
                    "sshpass is required for password authentication. "
                    "Install it with: apt-get install sshpass (Linux) or "
                    "brew install hudochenkov/sshpass/sshpass (macOS)"
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
            raise SSHConnectionError(
                f"SSH command not found. Ensure ssh is installed: {e}"
            ) from e

        # Wait a moment for tunnel to establish
        time.sleep(1)

        # Verify tunnel is working
        if not self._is_port_in_use(self.local_port):
            raise SSHConnectionError(
                f"SSH tunnel created but port {self.local_port} is not listening. "
                "The tunnel may have failed to establish."
            )

        self._connected = True

        # Create HTTP session
        self._create_session()

        logger.info(
            "SSH tunnel established: localhost:%d -> %s:%d",
            self.local_port,
            self.remote_host,
            self.remote_port,
        )

    def _create_session(self) -> None:
        """Create HTTP session for making requests."""
        self._session = requests.Session()

        retry_strategy = Retry(
            total=self._retries,
            backoff_factor=0.5,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        if self.api_key:
            self._session.headers["X-API-Key"] = self.api_key

    def close(self) -> None:
        """Close SSH tunnel."""
        if self._session:
            self._session.close()
            self._session = None

        # Kill the SSH tunnel process
        self._cleanup_port(self.local_port)
        self._connected = False
        logger.info("SSH tunnel closed")

    def reconnect(self) -> None:
        """Close and re-establish the SSH tunnel."""
        self.close()
        self.connect()

    def _ensure_connected(self) -> None:
        """Ensure tunnel is connected, raise if not."""
        if not self.connected:
            raise SSHConnectionError(
                "SSH tunnel not connected. Call connect() first."
            )

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        return f"{self.base_url}{endpoint}"

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate errors."""
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if response.status_code == 401:
            raise AuthenticationError(data.get("error", "Authentication failed"))

        if response.status_code >= 400:
            raise APIError(
                message=data.get("error", f"HTTP {response.status_code}"),
                status_code=response.status_code,
                error_code=data.get("error_code"),
                detail=data.get("detail"),
            )

        return data

    def get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request through the SSH tunnel.

        Args:
            endpoint: API endpoint (e.g., "/enb/stats").
            params: Optional query parameters.

        Returns:
            JSON response data.

        Raises:
            SSHConnectionError: If tunnel is not connected.
            SSHTimeoutError: If request times out.
            APIError: If API returns an error.
        """
        self._ensure_connected()
        try:
            response = self._session.get(
                self._build_url(endpoint),
                params=params,
                timeout=self.timeout,
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            raise SSHConnectionError(f"Request failed (tunnel may be down): {e}") from e
        except requests.exceptions.Timeout as e:
            raise SSHTimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.RequestException as e:
            raise SSHClientError(f"Request failed: {e}") from e

    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request through the SSH tunnel.

        Args:
            endpoint: API endpoint.
            data: Request body data.
            params: Optional query parameters.

        Returns:
            JSON response data.
        """
        self._ensure_connected()
        try:
            response = self._session.post(
                self._build_url(endpoint),
                json=data,
                params=params,
                timeout=self.timeout,
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            raise SSHConnectionError(f"Request failed (tunnel may be down): {e}") from e
        except requests.exceptions.Timeout as e:
            raise SSHTimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.RequestException as e:
            raise SSHClientError(f"Request failed: {e}") from e

    def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a PUT request through the SSH tunnel."""
        self._ensure_connected()
        try:
            response = self._session.put(
                self._build_url(endpoint),
                json=data,
                timeout=self.timeout,
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            raise SSHConnectionError(f"Request failed (tunnel may be down): {e}") from e
        except requests.exceptions.Timeout as e:
            raise SSHTimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.RequestException as e:
            raise SSHClientError(f"Request failed: {e}") from e

    def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a DELETE request through the SSH tunnel."""
        self._ensure_connected()
        try:
            response = self._session.delete(
                self._build_url(endpoint),
                params=params,
                timeout=self.timeout,
            )
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            raise SSHConnectionError(f"Request failed (tunnel may be down): {e}") from e
        except requests.exceptions.Timeout as e:
            raise SSHTimeoutError(f"Request to {endpoint} timed out") from e
        except requests.exceptions.RequestException as e:
            raise SSHClientError(f"Request failed: {e}") from e

    def health_check(self) -> dict[str, Any]:
        """Check if the REST API service is healthy.

        Returns:
            Health status response.
        """
        return self.get("/health")

    def is_listening(self, timeout: float = 2.0) -> bool:
        """Check if the SSH host is reachable.

        Performs a lightweight TCP socket connection check to determine if
        the SSH service is listening on the configured host and port.

        Note: This checks SSH connectivity, not the REST API. To check if
        the REST API is available, establish the tunnel first and use
        health_check().

        Args:
            timeout: Connection timeout in seconds (default: 2.0).

        Returns:
            True if SSH service is listening, False otherwise.

        Example::

            client = HTTPOverSSHClient(
                ssh_host="192.168.1.80",
                ssh_username="root",
            )

            if client.is_listening():
                print("SSH service is reachable")
                client.connect()
                health = client.health_check()
                print(f"REST API healthy: {health}")
        """
        try:
            with socket.create_connection(
                (self.ssh_host, self.ssh_port), timeout=timeout
            ):
                return True
        except OSError:
            return False

    def is_tunnel_active(self) -> bool:
        """Check if the SSH tunnel is active and forwarding traffic.

        Returns:
            True if tunnel is established and active, False otherwise.
        """
        return self.connected

    def __enter__(self) -> "HTTPOverSSHClient":
        """Context manager entry - establish tunnel."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit - close tunnel."""
        self.close()

    def __repr__(self) -> str:
        status = "connected" if self.connected else "disconnected"
        tunnel_info = ""
        if self.connected:
            tunnel_info = f", tunnel=localhost:{self.local_port}"
        return (
            f"HTTPOverSSHClient({self.ssh_username}@{self.ssh_host}:{self.ssh_port}, "
            f"{status}{tunnel_info})"
        )
