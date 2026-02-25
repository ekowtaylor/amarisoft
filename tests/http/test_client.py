"""Tests for HTTPClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from client.http.client import HTTPClient


class TestIsListening:
    """Tests for HTTPClient.is_listening() method."""

    @patch("client.http.client.socket.create_connection")
    def test_is_listening_returns_true_when_service_available(self, mock_conn):
        """Test is_listening returns True when service accepts connections."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = HTTPClient("http://192.168.1.80:9010")
        result = client.is_listening()

        assert result is True
        mock_conn.assert_called_once_with(("192.168.1.80", 9010), timeout=2.0)

    @patch("client.http.client.socket.create_connection")
    def test_is_listening_returns_false_on_connection_refused(self, mock_conn):
        """Test is_listening returns False when connection is refused."""
        mock_conn.side_effect = OSError("Connection refused")

        client = HTTPClient("http://192.168.1.80:9010")
        result = client.is_listening()

        assert result is False

    @patch("client.http.client.socket.create_connection")
    def test_is_listening_returns_false_on_timeout(self, mock_conn):
        """Test is_listening returns False on timeout."""
        import socket

        mock_conn.side_effect = socket.timeout("Connection timed out")

        client = HTTPClient("http://192.168.1.80:9010")
        result = client.is_listening()

        assert result is False

    @patch("client.http.client.socket.create_connection")
    def test_is_listening_with_custom_timeout(self, mock_conn):
        """Test is_listening uses custom timeout."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = HTTPClient("http://192.168.1.80:9010")
        client.is_listening(timeout=5.0)

        mock_conn.assert_called_once_with(("192.168.1.80", 9010), timeout=5.0)

    @patch("client.http.client.socket.create_connection")
    def test_is_listening_parses_url_correctly(self, mock_conn):
        """Test is_listening correctly parses host and port from URL."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = HTTPClient("http://10.0.0.1:8080")
        client.is_listening()

        mock_conn.assert_called_once_with(("10.0.0.1", 8080), timeout=2.0)

    @patch("client.http.client.socket.create_connection")
    def test_is_listening_default_http_port(self, mock_conn):
        """Test is_listening uses default port 80 for HTTP without explicit port."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = HTTPClient("http://192.168.1.80")
        client.is_listening()

        mock_conn.assert_called_once_with(("192.168.1.80", 80), timeout=2.0)

    @patch("client.http.client.socket.create_connection")
    def test_is_listening_default_https_port(self, mock_conn):
        """Test is_listening uses default port 443 for HTTPS without explicit port."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = HTTPClient("https://192.168.1.80")
        client.is_listening()

        mock_conn.assert_called_once_with(("192.168.1.80", 443), timeout=2.0)

    @patch("client.http.client.socket.create_connection")
    def test_is_listening_without_scheme(self, mock_conn):
        """Test is_listening works when URL is provided without http:// prefix."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = HTTPClient("192.168.1.80:9010")
        client.is_listening()

        mock_conn.assert_called_once_with(("192.168.1.80", 9010), timeout=2.0)
