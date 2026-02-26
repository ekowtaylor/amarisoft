"""Tests for HTTPOverSSHClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from client.http_ssh.client import HTTPOverSSHClient
from client.http_ssh.exceptions import (
    SSHConnectionError,
    SSHTimeoutError,
    APIError,
)


class TestHTTPOverSSHClientInit:
    """Tests for HTTPOverSSHClient initialization."""

    def test_init_with_password(self):
        """Test initialization with password authentication."""
        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_password="secret",
        )
        assert client.ssh_host == "192.168.1.80"
        assert client.ssh_port == 22
        assert client.ssh_username == "root"
        assert client.ssh_password == "secret"
        assert client.remote_port == 9010
        assert client.local_port == 19010
        assert client.connected is False

    def test_init_with_key(self):
        """Test initialization with key-based authentication."""
        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_key_path="~/.ssh/id_rsa",
        )
        assert client.ssh_key_path == "~/.ssh/id_rsa"

    def test_init_custom_ports(self):
        """Test initialization with custom ports."""
        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_port=2222,
            remote_port=8080,
            local_port=9999,
        )
        assert client.ssh_port == 2222
        assert client.remote_port == 8080
        assert client.local_port == 9999

    def test_base_url(self):
        """Test base_url property."""
        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            local_port=19010,
        )
        assert client.base_url == "http://localhost:19010"


class TestHTTPOverSSHClientConnect:
    """Tests for HTTPOverSSHClient.connect()."""

    @patch("client.http_ssh.client.subprocess.run")
    @patch("client.http_ssh.client.socket.socket")
    @patch("client.http_ssh.client.time.sleep")
    def test_connect_success_with_password(self, mock_sleep, mock_socket, mock_run):
        """Test successful SSH connection with password."""
        # Mock sshpass check
        mock_run.side_effect = [
            MagicMock(returncode=0),  # sshpass -V check
            MagicMock(returncode=0, stdout="", stderr=""),  # lsof check (port free)
            MagicMock(returncode=0, stdout="", stderr=""),  # ssh tunnel command
        ]

        # Mock port check - port is in use after tunnel created
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 0  # Port in use
        mock_socket.return_value.__enter__.return_value = mock_sock_instance

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_password="secret",
        )
        client.connect()

        assert client._connected is True

    @patch("client.http_ssh.client.subprocess.run")
    def test_connect_sshpass_not_available(self, mock_run):
        """Test error when sshpass is not installed."""
        # Mock sshpass check to fail
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # lsof check
            FileNotFoundError("sshpass not found"),
        ]

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_password="secret",
        )

        with pytest.raises(SSHConnectionError, match="sshpass is required"):
            client.connect()

    @patch("client.http_ssh.client.subprocess.run")
    @patch("client.http_ssh.client.socket.socket")
    @patch("client.http_ssh.client.time.sleep")
    def test_connect_success_with_key(self, mock_sleep, mock_socket, mock_run):
        """Test successful SSH connection with key file."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # lsof check
            MagicMock(returncode=0, stdout="", stderr=""),  # ssh tunnel command
        ]

        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 0
        mock_socket.return_value.__enter__.return_value = mock_sock_instance

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_key_path="~/.ssh/id_rsa",
        )
        client.connect()

        assert client._connected is True

    @patch("client.http_ssh.client.subprocess.run")
    def test_connect_auth_failure(self, mock_run):
        """Test SSH authentication failure."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # sshpass check
            MagicMock(returncode=0, stdout=""),  # lsof check
            MagicMock(returncode=1, stdout="", stderr="Permission denied"),
        ]

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_password="wrong",
        )

        with pytest.raises(SSHConnectionError, match="authentication failed"):
            client.connect()

    @patch("client.http_ssh.client.subprocess.run")
    def test_connect_timeout(self, mock_run):
        """Test SSH connection timeout."""
        import subprocess

        mock_run.side_effect = [
            MagicMock(returncode=0),  # sshpass check
            MagicMock(returncode=0, stdout=""),  # lsof check
            subprocess.TimeoutExpired(cmd="ssh", timeout=10),
        ]

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_password="secret",
            connect_timeout=5.0,
        )

        with pytest.raises(SSHTimeoutError, match="timed out"):
            client.connect()


class TestHTTPOverSSHClientIsListening:
    """Tests for HTTPOverSSHClient.is_listening()."""

    @patch("client.http_ssh.client.socket.create_connection")
    def test_is_listening_returns_true(self, mock_conn):
        """Test is_listening returns True when SSH is reachable."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
        )
        result = client.is_listening()

        assert result is True
        mock_conn.assert_called_once_with(("192.168.1.80", 22), timeout=2.0)

    @patch("client.http_ssh.client.socket.create_connection")
    def test_is_listening_returns_false(self, mock_conn):
        """Test is_listening returns False when SSH is unreachable."""
        mock_conn.side_effect = OSError("Connection refused")

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
        )
        result = client.is_listening()

        assert result is False

    @patch("client.http_ssh.client.socket.create_connection")
    def test_is_listening_custom_timeout(self, mock_conn):
        """Test is_listening uses custom timeout."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            ssh_port=2222,
        )
        client.is_listening(timeout=5.0)

        mock_conn.assert_called_once_with(("192.168.1.80", 2222), timeout=5.0)


class TestHTTPOverSSHClientRequests:
    """Tests for HTTP request methods."""

    @patch("client.http_ssh.client.requests.Session")
    def test_get_request(self, mock_session_class):
        """Test GET request through tunnel."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
        )
        # Manually set connected state for testing
        client._connected = True
        client._create_session()

        result = client.get("/health")

        assert result == {"status": "ok"}

    @patch("client.http_ssh.client.requests.Session")
    def test_post_request(self, mock_session_class):
        """Test POST request through tunnel."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
        )
        client._connected = True
        client._create_session()

        result = client.post("/enb/power", data={"action": "on"})

        assert result == {"result": "success"}

    def test_get_without_connection_raises(self):
        """Test that GET without connection raises error."""
        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
        )

        with pytest.raises(SSHConnectionError, match="not connected"):
            client.get("/health")

    @patch("client.http_ssh.client.requests.Session")
    def test_api_error_response(self, mock_session_class):
        """Test API error response handling."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
        )
        client._connected = True
        client._create_session()

        with pytest.raises(APIError):
            client.get("/nonexistent")


class TestHTTPOverSSHClientClose:
    """Tests for close() method."""

    @patch("client.http_ssh.client.subprocess.run")
    def test_close_cleans_up(self, mock_run):
        """Test close cleans up resources."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
        )
        client._connected = True
        client._session = MagicMock()

        client.close()

        assert client._connected is False
        assert client._session is None


class TestHTTPOverSSHClientRepr:
    """Tests for __repr__."""

    def test_repr_disconnected(self):
        """Test repr when disconnected."""
        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
        )
        repr_str = repr(client)
        assert "root@192.168.1.80:22" in repr_str
        assert "disconnected" in repr_str

    @patch("client.http_ssh.client.socket.socket")
    def test_repr_connected(self, mock_socket):
        """Test repr when connected."""
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 0
        mock_socket.return_value.__enter__.return_value = mock_sock_instance

        client = HTTPOverSSHClient(
            ssh_host="192.168.1.80",
            ssh_username="root",
            local_port=19010,
        )
        client._connected = True

        repr_str = repr(client)

        assert "connected" in repr_str
        assert "tunnel=localhost:19010" in repr_str
