"""WebSocket over SSH client for Amarisoft Remote API access.

This module provides a WebSocket client that forwards connections through
an SSH tunnel, supporting both direct SSH and ProxyJump configurations.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import socket
import subprocess
import threading
import time
from typing import Any, Callable

import websocket

from .exceptions import (
    SSHClientError,
    SSHConnectionError,
    SSHTimeoutError,
    SSHTunnelError,
)

logger = logging.getLogger(__name__)

_MAX_SKIP = 200


class WebSocketOverSSHClient:
    """WebSocket client that forwards connections through an SSH tunnel.

    Supports both direct SSH connections and ProxyJump (jump host) configurations
    for accessing Amarisoft services through intermediate hosts.

    Args:
        ssh_host: Hostname or IP of the SSH target (Amarisoft box).
        ssh_username: SSH username.
        ssh_port: SSH port on the target (default: 22).
        ssh_password: SSH password (optional if using key-based auth).
        ssh_key_path: Path to SSH private key file (optional).
        ssh_proxy_host: Jump host for ProxyJump (optional).
        ssh_proxy_user: Username for jump host (optional, defaults to ssh_username).
        remote_port: WebSocket port on the remote Amarisoft service (default: 9001).
        local_port: Local port for the tunnel (default: 19001).
        timeout: WebSocket operation timeout in seconds.
        connect_timeout: SSH connection timeout in seconds.
        password: Amarisoft WebSocket authentication password (com_auth).
        auto_reconnect: Automatically reconnect on send failure.

    Example::

        # Direct connection
        client = WebSocketOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_password="toor",
            remote_port=9001,
        )

        # With jump host (ProxyJump)
        client = WebSocketOverSSHClient(
            ssh_host="2620:10d:c052:12a:aaa1:59ff:fe88:d39",
            ssh_username="root",
            ssh_password="toor",
            ssh_proxy_host="devvm14066.vll0.facebook.com",
            remote_port=9001,
        )

        with client:
            response = client.send({"message": "stats"})
            print(response)
    """

    def __init__(
        self,
        ssh_host: str,
        ssh_username: str,
        ssh_port: int = 22,
        ssh_password: str | None = None,
        ssh_key_path: str | None = None,
        ssh_proxy_host: str | None = None,
        ssh_proxy_user: str | None = None,
        remote_port: int = 9001,
        local_port: int = 19001,
        timeout: float = 10.0,
        connect_timeout: float = 30.0,
        password: str | None = None,
        auto_reconnect: bool = False,
    ):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.ssh_key_path = ssh_key_path
        self.ssh_proxy_host = ssh_proxy_host
        self.ssh_proxy_user = ssh_proxy_user or ssh_username
        self.remote_port = remote_port
        self.local_port = local_port
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.password = password
        self.auto_reconnect = auto_reconnect

        self._ssh_process: subprocess.Popen | None = None
        self._ws: websocket.WebSocket | None = None
        self._tunnel_active = False
        self._ws_connected = False
        self._message_id = 0
        self._lock = threading.Lock()

    @property
    def uri(self) -> str:
        """WebSocket URI through the local tunnel."""
        return f"ws://127.0.0.1:{self.local_port}"

    @property
    def tunnel_active(self) -> bool:
        """Return True if SSH tunnel is active."""
        if not self._tunnel_active:
            return False
        return self._is_port_in_use(self.local_port)

    @property
    def connected(self) -> bool:
        """Return True if WebSocket is connected through tunnel."""
        ws = self._ws
        return ws is not None and ws.connected

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
                time.sleep(1)
                return True
        except FileNotFoundError:
            try:
                subprocess.run(["pkill", "-f", f"ssh.*{port}"], capture_output=True)
                time.sleep(1)
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

    def connect_tunnel(self) -> None:
        """Establish SSH tunnel to the remote WebSocket port.

        Raises:
            SSHConnectionError: If tunnel cannot be established.
            SSHTimeoutError: If connection times out.
        """
        if self.tunnel_active:
            logger.debug("SSH tunnel already active")
            return

        self._cleanup_port(self.local_port)

        ssh_args = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            f"ConnectTimeout={int(self.connect_timeout)}",
            "-N",
            "-L",
            f"{self.local_port}:localhost:{self.remote_port}",
        ]

        if self.ssh_proxy_host:
            proxy_target = (
                f"{self.ssh_proxy_user}@{self.ssh_proxy_host}"
                if self.ssh_proxy_user
                else self.ssh_proxy_host
            )
            ssh_args.extend(["-J", proxy_target])
            logger.info(
                "Creating SSH tunnel with ProxyJump: localhost:%d -> %s:%d via %s",
                self.local_port,
                self.ssh_host,
                self.remote_port,
                self.ssh_proxy_host,
            )
        else:
            logger.info(
                "Creating SSH tunnel: localhost:%d -> %s:%d",
                self.local_port,
                self.ssh_host,
                self.remote_port,
            )

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
                    "Install with: brew install sshpass (macOS) or apt install sshpass"
                )
            ssh_command = ["sshpass", "-p", self.ssh_password] + ssh_args
        else:
            ssh_command = ssh_args

        try:
            self._ssh_process = subprocess.Popen(
                ssh_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            for _ in range(int(self.connect_timeout * 2)):
                if self._is_port_in_use(self.local_port):
                    self._tunnel_active = True
                    logger.info("SSH tunnel established: localhost:%d", self.local_port)
                    return
                if self._ssh_process.poll() is not None:
                    _, stderr = self._ssh_process.communicate()
                    error_msg = stderr.decode().strip() if stderr else "Unknown error"
                    raise SSHConnectionError(f"SSH tunnel failed: {error_msg}")
                time.sleep(0.5)

            self._ssh_process.terminate()
            raise SSHTimeoutError(
                f"SSH tunnel did not become ready within {self.connect_timeout}s"
            )

        except FileNotFoundError as e:
            raise SSHConnectionError(f"SSH command not found: {e}") from e

    def close_tunnel(self) -> None:
        """Close the SSH tunnel."""
        if self._ssh_process:
            self._ssh_process.terminate()
            try:
                self._ssh_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._ssh_process.kill()
            self._ssh_process = None

        self._cleanup_port(self.local_port)
        self._tunnel_active = False
        logger.info("SSH tunnel closed")

    def connect(self) -> dict[str, Any]:
        """Establish SSH tunnel and WebSocket connection.

        Returns:
            The ``ready`` message from the Amarisoft service.

        Raises:
            SSHConnectionError: If tunnel cannot be established.
            SSHTunnelError: If WebSocket connection through tunnel fails.
        """
        self.connect_tunnel()

        if self.connected:
            return {"message": "ready"}

        try:
            self._ws = websocket.WebSocket()
            self._ws.settimeout(self.timeout)
            self._ws.connect(self.uri, origin="Python-AmariClient-SSH")
        except websocket.WebSocketException as e:
            raise SSHTunnelError(f"WebSocket connection failed: {e}") from e
        except OSError as e:
            raise SSHTunnelError(f"WebSocket connection failed: {e}") from e

        ready_msg = self._recv()
        if ready_msg.get("message") != "ready":
            self.close()
            raise SSHTunnelError(
                f"Expected 'ready' message, got: {ready_msg.get('message')}"
            )

        if self.password:
            self._ws.send(
                json.dumps(
                    {
                        "message": "authenticate",
                        "password": self.password,
                    }
                )
            )
            auth_resp = self._recv()
            if "error" in auth_resp:
                self.close()
                raise SSHTunnelError(f"Authentication failed: {auth_resp['error']}")

        self._ws_connected = True
        logger.info(
            "WebSocket connected through tunnel to %s:%d",
            self.ssh_host,
            self.remote_port,
        )
        return ready_msg

    def reconnect(self) -> dict[str, Any]:
        """Close and re-establish tunnel and WebSocket connection."""
        self.close()
        return self.connect()

    def close(self) -> None:
        """Close WebSocket connection and SSH tunnel."""
        if self._ws:
            try:
                self._ws.close()
            except websocket.WebSocketException:
                pass
            self._ws = None
            self._ws_connected = False

        self.close_tunnel()
        logger.info("WebSocket and tunnel closed")

    def send(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON message and return the matching response.

        Args:
            message: The message dictionary to send.

        Returns:
            The parsed JSON response from the server.

        Raises:
            SSHTunnelError: If not connected or send fails.
        """
        self._ensure_connected()

        with self._lock:
            self._message_id += 1
            msg_id = self._message_id
            message["message_id"] = msg_id

            payload = json.dumps(message)
            logger.debug("TX >>> %s", payload)

            try:
                self._ws.send(payload)
            except websocket.WebSocketException as e:
                self._ws_connected = False
                raise SSHTunnelError(f"Send failed: {e}") from e

            return self._recv_matching(msg_id)

    def send_raw(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send a message without adding a ``message_id``."""
        self._ensure_connected()

        payload = json.dumps(message)
        logger.debug("TX (raw) >>> %s", payload)

        try:
            self._ws.send(payload)
        except websocket.WebSocketException as e:
            self._ws_connected = False
            raise SSHTunnelError(f"Send failed: {e}") from e

        return self._recv()

    def send_batch(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Send multiple messages as a JSON array batch."""
        self._ensure_connected()

        with self._lock:
            for msg in messages:
                self._message_id += 1
                msg["message_id"] = self._message_id

            payload = json.dumps(messages)
            logger.debug("TX (batch) >>> %s", payload)

            try:
                self._ws.send(payload)
            except websocket.WebSocketException as e:
                self._ws_connected = False
                raise SSHTunnelError(f"Batch send failed: {e}") from e

            responses: list[dict[str, Any]] = []
            for msg in messages:
                responses.append(self._recv_matching(msg["message_id"]))
            return responses

    def listen(
        self,
        callback: Callable[[dict[str, Any]], bool | None],
        duration: float | None = None,
    ) -> None:
        """Listen for unsolicited messages (events, logs).

        Args:
            callback: Called with each received message. Return ``False`` to stop.
            duration: Maximum listen time in seconds.
        """
        self._ensure_connected()

        start = time.monotonic()
        while True:
            if duration is not None and (time.monotonic() - start) >= duration:
                break
            try:
                msg = self._recv()
            except SSHTimeoutError:
                if duration is not None:
                    continue
                break
            except SSHTunnelError:
                break
            if callback(msg) is False:
                break

    def health_check(self) -> dict[str, Any]:
        """Perform a health check using an appropriate message for the service.

        Uses config_get for MME (port 9000) and eNB (port 9001) services,
        and stats for other services.

        Returns:
            Response from the Amarisoft service.
        """
        # MME (9000) and eNB (9001) should use config_get
        if self.remote_port in (9000, 9001):
            return self.send({"message": "config_get"})
        return self.send({"message": "stats"})

    def is_healthy(self) -> bool:
        """Check if the connection is healthy.

        Returns:
            True if connected and responsive, False otherwise.
        """
        try:
            response = self.health_check()
            return "error" not in response
        except Exception:
            return False

    def _ensure_connected(self) -> None:
        """Raise or attempt reconnect if not connected."""
        if self.connected:
            return
        if self.auto_reconnect:
            logger.info("Auto-reconnecting...")
            self.reconnect()
        else:
            raise SSHTunnelError("Not connected. Call connect() first.")

    def _recv_matching(self, msg_id: int) -> dict[str, Any]:
        """Receive messages until one with a matching message_id arrives."""
        for _ in range(_MAX_SKIP):
            resp = self._recv()
            if resp.get("message_id") == msg_id:
                if "error" in resp:
                    raise SSHTunnelError(
                        f"Command error: {resp['error']} (code: {resp.get('error_code')})"
                    )
                return resp
            logger.debug("Skipped unsolicited message: %s", resp.get("message"))
        raise SSHTunnelError(
            f"No matching response for message_id={msg_id} after {_MAX_SKIP} messages"
        )

    def _recv(self) -> dict[str, Any]:
        """Receive and parse a single JSON message."""
        try:
            raw = self._ws.recv()
        except websocket.WebSocketTimeoutException as e:
            raise SSHTimeoutError(f"Timed out waiting for response: {e}") from e
        except websocket.WebSocketException as e:
            self._ws_connected = False
            raise SSHTunnelError(f"Receive failed: {e}") from e

        if not raw:
            raise SSHTunnelError("Received empty message from server")

        logger.debug("RX <<< %s", raw)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise SSHTunnelError(f"Invalid JSON from server: {e}") from e

        if isinstance(data, list):
            return data[0] if data else {}
        return data

    def __enter__(self) -> "WebSocketOverSSHClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        tunnel_status = "tunnel_active" if self.tunnel_active else "tunnel_closed"
        ws_status = "ws_connected" if self.connected else "ws_disconnected"
        proxy = f" via {self.ssh_proxy_host}" if self.ssh_proxy_host else ""
        return (
            f"WebSocketOverSSHClient({self.ssh_username}@{self.ssh_host}:{self.remote_port}"
            f"{proxy}, {tunnel_status}, {ws_status})"
        )
