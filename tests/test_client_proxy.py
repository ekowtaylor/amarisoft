"""Tests for WebSocketClient proxy functionality."""

from __future__ import annotations

import base64
import json
import socket
import ssl
import struct
from unittest.mock import MagicMock, patch

import pytest
from client.websocket.client import ConnectionMethod, WebSocketClient
from client.websocket.exceptions import (
    AmariConnectionError,
    AmariTimeoutError,
    ProxyConnectionError,
)


# ── ConnectionMethod Enum ───────────────────────────────────────────


class TestConnectionMethod:
    def test_direct_value(self):
        assert ConnectionMethod.DIRECT.value == "direct"

    def test_proxy_value(self):
        assert ConnectionMethod.PROXY.value == "proxy"

    def test_enum_from_string_direct(self):
        assert ConnectionMethod("direct") == ConnectionMethod.DIRECT

    def test_enum_from_string_proxy(self):
        assert ConnectionMethod("proxy") == ConnectionMethod.PROXY

    def test_enum_is_string_subclass(self):
        assert isinstance(ConnectionMethod.DIRECT, str)
        assert isinstance(ConnectionMethod.PROXY, str)

    def test_invalid_value_raises_error(self):
        with pytest.raises(ValueError):
            ConnectionMethod("invalid")


# ── Proxy Configuration ─────────────────────────────────────────────


class TestProxyConfiguration:
    def test_default_connection_method_is_direct(self):
        client = WebSocketClient("10.0.0.1", 9001)
        assert client.connection_method == ConnectionMethod.DIRECT

    def test_connection_method_string_converted_to_enum(self):
        client = WebSocketClient("10.0.0.1", 9001, connection_method="proxy")
        assert client.connection_method == ConnectionMethod.PROXY
        assert isinstance(client.connection_method, ConnectionMethod)

    def test_connection_method_enum_accepted(self):
        client = WebSocketClient(
            "10.0.0.1", 9001, connection_method=ConnectionMethod.PROXY
        )
        assert client.connection_method == ConnectionMethod.PROXY

    def test_proxy_host_stored(self):
        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
        )
        assert client.proxy_host == "proxy.example.com"

    def test_proxy_port_default(self):
        client = WebSocketClient("10.0.0.1", 9001)
        assert client.proxy_port == 8082

    def test_proxy_port_custom(self):
        client = WebSocketClient("10.0.0.1", 9001, proxy_port=3128)
        assert client.proxy_port == 3128

    def test_proxy_tls_default(self):
        client = WebSocketClient("10.0.0.1", 9001)
        assert client.proxy_tls is True

    def test_proxy_tls_disabled(self):
        client = WebSocketClient("10.0.0.1", 9001, proxy_tls=False)
        assert client.proxy_tls is False

    def test_proxy_insecure_default(self):
        client = WebSocketClient("10.0.0.1", 9001)
        assert client.proxy_insecure is True

    def test_proxy_insecure_disabled(self):
        client = WebSocketClient("10.0.0.1", 9001, proxy_insecure=False)
        assert client.proxy_insecure is False

    def test_proxy_client_cert_stored(self):
        client = WebSocketClient(
            "10.0.0.1",
            9001,
            proxy_client_cert="/path/to/cert.pem",
        )
        assert client.proxy_client_cert == "/path/to/cert.pem"

    def test_proxy_client_key_stored(self):
        client = WebSocketClient(
            "10.0.0.1",
            9001,
            proxy_client_cert="/path/to/cert.pem",
            proxy_client_key="/path/to/key.pem",
        )
        assert client.proxy_client_key == "/path/to/key.pem"


# ── _format_hostport ────────────────────────────────────────────────


class TestFormatHostport:
    def test_ipv4_address(self):
        client = WebSocketClient("10.0.0.1", 9001)
        result = client._format_hostport("192.168.1.1", 9000)
        assert result == "192.168.1.1:9000"

    def test_ipv6_address_brackets(self):
        client = WebSocketClient("10.0.0.1", 9001)
        result = client._format_hostport("2001:db8::1", 9000)
        assert result == "[2001:db8::1]:9000"

    def test_ipv6_full_address(self):
        client = WebSocketClient("10.0.0.1", 9001)
        result = client._format_hostport("2620:10d:c052:12a:aaa1:59ff:fe88:d39", 9000)
        assert result == "[2620:10d:c052:12a:aaa1:59ff:fe88:d39]:9000"

    def test_hostname_no_brackets(self):
        client = WebSocketClient("10.0.0.1", 9001)
        result = client._format_hostport("amarisoft.local", 9001)
        assert result == "amarisoft.local:9001"


# ── _recv_until ─────────────────────────────────────────────────────


class TestRecvUntil:
    def test_receives_until_marker(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Length: 0\r\n",
            b"\r\n",
        ]

        result = client._recv_until(mock_sock)
        assert result == b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"

    def test_receives_all_at_once(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b"HTTP/1.1 200 OK\r\n\r\n"

        result = client._recv_until(mock_sock)
        assert result == b"HTTP/1.1 200 OK\r\n\r\n"

    def test_stops_on_empty_recv(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = [b"partial", b""]

        result = client._recv_until(mock_sock)
        assert result == b"partial"

    def test_raises_on_limit_exceeded(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b"x" * 5000

        with pytest.raises(RuntimeError, match="too large"):
            client._recv_until(mock_sock, limit=10000)


# ── _recv_exact ─────────────────────────────────────────────────────


class TestRecvExact:
    def test_receives_exact_bytes(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b"12345"

        result = client._recv_exact(mock_sock, 5)
        assert result == b"12345"

    def test_receives_in_chunks(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = [b"12", b"34", b"5"]

        result = client._recv_exact(mock_sock, 5)
        assert result == b"12345"

    def test_returns_partial_on_disconnect(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = [b"123", b""]

        result = client._recv_exact(mock_sock, 5)
        assert result == b"123"


# ── Proxy Connection Errors ─────────────────────────────────────────


class TestProxyConnectionErrors:
    def test_proxy_requires_proxy_host(self):
        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host=None,
        )
        with pytest.raises(ProxyConnectionError, match="proxy_host is required"):
            client.connect()

    @patch("client.websocket.client._socket.create_connection")
    def test_proxy_connection_failure(self, mock_conn):
        mock_conn.side_effect = OSError("Connection refused")

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_port=8082,
        )

        with pytest.raises(ProxyConnectionError, match="Failed to connect to proxy"):
            client.connect()

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client._ssl.create_default_context")
    def test_proxy_tls_handshake_failure(self, mock_ssl_ctx, mock_conn):
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        mock_ctx = MagicMock()
        mock_ssl_ctx.return_value = mock_ctx
        mock_ctx.wrap_socket.side_effect = ssl.SSLError("handshake failed")

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=True,
        )

        with pytest.raises(ProxyConnectionError, match="TLS handshake failed"):
            client.connect()
        mock_sock.close.assert_called_once()

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client._ssl.create_default_context")
    def test_proxy_connect_rejected(self, mock_ssl_ctx, mock_conn):
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        mock_ctx = MagicMock()
        mock_ssl_ctx.return_value = mock_ctx
        mock_ctx.wrap_socket.return_value = mock_sock

        mock_sock.recv.return_value = b"HTTP/1.1 403 Forbidden\r\n\r\n"

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
        )

        with pytest.raises(ProxyConnectionError, match="Proxy CONNECT failed"):
            client.connect()


# ── Proxy Connection Success ────────────────────────────────────────


class TestProxyConnectionSuccess:
    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client._ssl.create_default_context")
    @patch("client.websocket.client.os.urandom")
    def test_proxy_connect_success(self, mock_urandom, mock_ssl_ctx, mock_conn):
        mock_urandom.return_value = b"\x00" * 16

        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        mock_ctx = MagicMock()
        mock_ssl_ctx.return_value = mock_ctx
        mock_ctx.wrap_socket.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        ws_frame = self._build_ws_frame(ready_json)

        # With ws_strict_handshake=False (default), no Sec-WebSocket-Accept needed
        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ws_frame[:2],
            ws_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
        )

        result = client.connect()
        assert result["message"] == "ready"
        assert client._tunnel_sock is mock_sock
        assert client._ready is True

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_proxy_no_tls(self, mock_urandom, mock_conn):
        mock_urandom.return_value = b"\x00" * 16

        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        ws_frame = self._build_ws_frame(ready_json)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ws_frame[:2],
            ws_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )

        result = client.connect()
        assert result["message"] == "ready"

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client._ssl.create_default_context")
    @patch("client.websocket.client.os.urandom")
    def test_proxy_with_client_cert(self, mock_urandom, mock_ssl_ctx, mock_conn):
        mock_urandom.return_value = b"\x00" * 16

        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        mock_ctx = MagicMock()
        mock_ssl_ctx.return_value = mock_ctx
        mock_ctx.wrap_socket.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        ws_frame = self._build_ws_frame(ready_json)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ws_frame[:2],
            ws_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_client_cert="/path/to/cert.pem",
            proxy_client_key="/path/to/key.pem",
        )

        client.connect()
        mock_ctx.load_cert_chain.assert_called_once_with(
            certfile="/path/to/cert.pem",
            keyfile="/path/to/key.pem",
        )

    @staticmethod
    def _build_ws_frame(payload: bytes) -> bytes:
        """Build an unmasked WebSocket text frame."""
        frame = bytearray()
        frame.append(0x81)  # FIN + text opcode
        plen = len(payload)
        if plen < 126:
            frame.append(plen)
        elif plen < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(payload)
        return bytes(frame)


# ── WebSocket Frame Building ────────────────────────────────────────


class TestWebSocketFrameBuilding:
    def test_send_ws_frame_small_payload(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        client._tunnel_sock = mock_sock

        with patch("client.websocket.client.os.urandom") as mock_urandom:
            mock_urandom.return_value = b"\x00\x01\x02\x03"
            client._send_ws_frame(b"hello")

        sent_data = mock_sock.sendall.call_args[0][0]
        assert sent_data[0] == 0x81  # FIN + text opcode
        assert (sent_data[1] & 0x80) == 0x80  # Mask bit set
        assert (sent_data[1] & 0x7F) == 5  # Payload length

    def test_send_ws_frame_no_socket_raises(self):
        client = WebSocketClient("10.0.0.1", 9001)
        client._tunnel_sock = None

        with pytest.raises(AmariConnectionError, match="not connected"):
            client._send_ws_frame(b"hello")

    def test_send_ws_frame_os_error(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        mock_sock.sendall.side_effect = OSError("broken pipe")
        client._tunnel_sock = mock_sock
        client._ready = True

        with pytest.raises(AmariConnectionError, match="Send failed"):
            client._send_ws_frame(b"hello")
        assert client._ready is False


# ── WebSocket Frame Receiving ───────────────────────────────────────


class TestWebSocketFrameReceiving:
    def test_recv_ws_frame_text(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        client._tunnel_sock = mock_sock

        payload = json.dumps({"message": "test"}).encode()
        frame = self._build_ws_frame(payload, opcode=1)

        recv_calls = [frame[:2], frame[2:]]
        mock_sock.recv.side_effect = recv_calls

        result = client._recv_ws_frame()
        assert result["message"] == "test"

    def test_recv_ws_frame_close(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        client._tunnel_sock = mock_sock
        client._ready = True

        frame = self._build_ws_frame(b"", opcode=8)  # Close frame
        mock_sock.recv.side_effect = [frame[:2], frame[2:]]

        with pytest.raises(AmariConnectionError, match="Server closed"):
            client._recv_ws_frame()
        assert client._ready is False

    def test_recv_ws_frame_ping_sends_pong(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        client._tunnel_sock = mock_sock

        ping_frame = self._build_ws_frame(b"ping", opcode=9)
        text_payload = json.dumps({"message": "response"}).encode()
        text_frame = self._build_ws_frame(text_payload, opcode=1)

        mock_sock.recv.side_effect = [
            ping_frame[:2],
            ping_frame[2:],  # Ping frame
            text_frame[:2],
            text_frame[2:],  # Text frame
        ]

        with patch.object(client, "_send_pong") as mock_pong:
            result = client._recv_ws_frame()

        mock_pong.assert_called_once_with(b"ping")
        assert result["message"] == "response"

    def test_recv_ws_frame_timeout(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = socket.timeout("timed out")
        client._tunnel_sock = mock_sock

        with pytest.raises(AmariTimeoutError):
            client._recv_ws_frame()

    def test_recv_ws_frame_unexpected_opcode(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        client._tunnel_sock = mock_sock

        frame = self._build_ws_frame(b"data", opcode=2)  # Binary frame
        mock_sock.recv.side_effect = [frame[:2], frame[2:]]

        with pytest.raises(AmariConnectionError, match="Unexpected WebSocket opcode"):
            client._recv_ws_frame()

    def test_recv_ws_frame_no_socket_raises(self):
        client = WebSocketClient("10.0.0.1", 9001)
        client._tunnel_sock = None

        with pytest.raises(AmariConnectionError, match="not connected"):
            client._recv_ws_frame()

    @staticmethod
    def _build_ws_frame(payload: bytes, opcode: int = 1) -> bytes:
        """Build an unmasked WebSocket frame with given opcode."""
        frame = bytearray()
        frame.append(0x80 | opcode)  # FIN + opcode
        plen = len(payload)
        if plen < 126:
            frame.append(plen)  # No mask bit
        elif plen < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(payload)
        return bytes(frame)


# ── Close with Proxy ────────────────────────────────────────────────


class TestCloseWithProxy:
    def test_close_tunnel_socket(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        client._tunnel_sock = mock_sock
        client._ready = True

        client.close()

        assert client._tunnel_sock is None
        assert client._ready is False
        mock_sock.close.assert_called_once()

    def test_close_tunnel_socket_handles_os_error(self):
        client = WebSocketClient("10.0.0.1", 9001)
        mock_sock = MagicMock()
        mock_sock.close.side_effect = OSError("already closed")
        client._tunnel_sock = mock_sock
        client._ready = True

        client.close()  # Should not raise

        assert client._tunnel_sock is None
        assert client._ready is False


# ── Connected Property with Proxy ───────────────────────────────────


class TestConnectedPropertyProxy:
    def test_connected_with_tunnel_socket_and_ready(self):
        client = WebSocketClient("10.0.0.1", 9001)
        client._tunnel_sock = MagicMock()
        client._ready = True

        assert client.connected is True

    def test_connected_with_tunnel_socket_not_ready(self):
        client = WebSocketClient("10.0.0.1", 9001)
        client._tunnel_sock = MagicMock()
        client._ready = False

        assert client.connected is False

    def test_connected_no_tunnel_socket_falls_back_to_ws(self):
        client = WebSocketClient("10.0.0.1", 9001)
        client._tunnel_sock = None
        mock_ws = MagicMock()
        mock_ws.connected = True
        client._ws = mock_ws

        assert client.connected is True


# ── Send/Recv with Proxy ────────────────────────────────────────────


class TestSendRecvWithProxy:
    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client._ssl.create_default_context")
    @patch("client.websocket.client.os.urandom")
    def test_send_uses_tunnel_socket(self, mock_urandom, mock_ssl_ctx, mock_conn):
        mock_urandom.return_value = b"\x00" * 16

        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        mock_ctx = MagicMock()
        mock_ssl_ctx.return_value = mock_ctx
        mock_ctx.wrap_socket.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        response_json = json.dumps({"message_id": 1, "data": "ok"}).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(response_json)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
        )
        client.connect()

        result = client.send({"message": "test"})
        assert result["data"] == "ok"
        assert mock_sock.sendall.call_count >= 2  # CONNECT + WS handshake + message

    @staticmethod
    def _build_ws_frame(payload: bytes) -> bytes:
        """Build an unmasked WebSocket text frame."""
        frame = bytearray()
        frame.append(0x81)
        plen = len(payload)
        if plen < 126:
            frame.append(plen)
        elif plen < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(payload)
        return bytes(frame)


# ── HTTP CONNECT Request Format ─────────────────────────────────────


class TestHTTPConnectFormat:
    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client._ssl.create_default_context")
    def test_connect_request_ipv4(self, mock_ssl_ctx, mock_conn):
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        mock_ctx = MagicMock()
        mock_ssl_ctx.return_value = mock_ctx
        mock_ctx.wrap_socket.return_value = mock_sock

        mock_sock.recv.return_value = b"HTTP/1.1 200 OK\r\n\r\n"

        client = WebSocketClient(
            "192.168.1.80",
            9000,
            connection_method="proxy",
            proxy_host="proxy.example.com",
        )

        with pytest.raises(AmariConnectionError):
            # Will fail on WS handshake, but we can check the CONNECT
            client.connect()

        # Find the CONNECT request call
        connect_call = mock_sock.sendall.call_args_list[0]
        connect_req = connect_call[0][0].decode()
        assert "CONNECT 192.168.1.80:9000 HTTP/1.1" in connect_req
        assert "Host: 192.168.1.80:9000" in connect_req

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client._ssl.create_default_context")
    def test_connect_request_ipv6(self, mock_ssl_ctx, mock_conn):
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        mock_ctx = MagicMock()
        mock_ssl_ctx.return_value = mock_ctx
        mock_ctx.wrap_socket.return_value = mock_sock

        mock_sock.recv.return_value = b"HTTP/1.1 200 OK\r\n\r\n"

        client = WebSocketClient(
            "2001:db8::1",
            9000,
            connection_method="proxy",
            proxy_host="proxy.example.com",
        )

        with pytest.raises(AmariConnectionError):
            client.connect()

        connect_call = mock_sock.sendall.call_args_list[0]
        connect_req = connect_call[0][0].decode()
        assert "CONNECT [2001:db8::1]:9000 HTTP/1.1" in connect_req
        assert "Host: [2001:db8::1]:9000" in connect_req


# ── Proxy SSL Context Configuration ─────────────────────────────────


class TestProxySSLContext:
    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client._ssl.create_default_context")
    def test_proxy_insecure_disables_verification(self, mock_ssl_ctx, mock_conn):
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        mock_ctx = MagicMock()
        mock_ssl_ctx.return_value = mock_ctx
        mock_ctx.wrap_socket.return_value = mock_sock

        mock_sock.recv.return_value = b"HTTP/1.1 403 Forbidden\r\n\r\n"

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_insecure=True,
        )

        with pytest.raises(ProxyConnectionError):
            client.connect()

        assert mock_ctx.check_hostname is False
        assert mock_ctx.verify_mode == ssl.CERT_NONE
        mock_ctx.wrap_socket.assert_called_with(mock_sock, server_hostname=None)

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client._ssl.create_default_context")
    def test_proxy_secure_enables_verification(self, mock_ssl_ctx, mock_conn):
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        mock_ctx = MagicMock()
        mock_ssl_ctx.return_value = mock_ctx
        mock_ctx.wrap_socket.return_value = mock_sock

        mock_sock.recv.return_value = b"HTTP/1.1 403 Forbidden\r\n\r\n"

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_insecure=False,
        )

        with pytest.raises(ProxyConnectionError):
            client.connect()

        mock_ctx.wrap_socket.assert_called_with(
            mock_sock, server_hostname="proxy.example.com"
        )


# ── Direct Connection Still Works ───────────────────────────────────


class TestDirectConnectionUnchanged:
    @patch("client.websocket.client.websocket.WebSocket")
    def test_direct_connection_uses_websocket_library(self, MockWS):
        ready = json.dumps({"message": "ready"})
        ws = MagicMock()
        ws.connected = True
        ws.recv.return_value = ready
        MockWS.return_value = ws

        client = WebSocketClient("127.0.0.1", 9001, connection_method="direct")
        result = client.connect()

        ws.connect.assert_called_once()
        assert result["message"] == "ready"
        assert client._tunnel_sock is None


# ── WebSocket Handshake Sec-WebSocket-Accept Validation ────────────


class TestSecWebSocketAcceptValidation:
    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_valid_sec_websocket_accept(self, mock_urandom, mock_conn):
        # Use a fixed key for predictable testing
        mock_urandom.return_value = b"\x00" * 16
        fixed_key = base64.b64encode(
            b"\x00" * 16
        ).decode()  # "AAAAAAAAAAAAAAAAAAAAAA=="

        # Calculate expected accept value per RFC 6455
        import hashlib

        ws_guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        expected_accept = base64.b64encode(
            hashlib.sha1((fixed_key + ws_guid).encode()).digest()
        ).decode()

        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        ws_frame = self._build_ws_frame(ready_json)

        # Include valid Sec-WebSocket-Accept header
        ws_response = (
            f"HTTP/1.1 101 Switching Protocols\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {expected_accept}\r\n"
            f"\r\n"
        ).encode()

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            ws_response,
            ws_frame[:2],
            ws_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
            ws_strict_handshake=True,  # Enable strict validation
        )

        result = client.connect()
        assert result["message"] == "ready"

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_invalid_sec_websocket_accept_raises(self, mock_urandom, mock_conn):
        mock_urandom.return_value = b"\x00" * 16

        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        # Include invalid Sec-WebSocket-Accept header
        ws_response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: INVALID_ACCEPT_VALUE\r\n"
            "\r\n"
        ).encode()

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            ws_response,
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
            ws_strict_handshake=True,  # Enable strict validation
        )

        with pytest.raises(AmariConnectionError, match="invalid Sec-WebSocket-Accept"):
            client.connect()

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_missing_sec_websocket_accept_raises(self, mock_urandom, mock_conn):
        mock_urandom.return_value = b"\x00" * 16

        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        # No Sec-WebSocket-Accept header
        ws_response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "\r\n"
        ).encode()

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            ws_response,
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
            ws_strict_handshake=True,  # Enable strict validation
        )

        with pytest.raises(AmariConnectionError, match="invalid Sec-WebSocket-Accept"):
            client.connect()

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_validation_skipped_by_default(self, mock_urandom, mock_conn):
        """Test that validation is skipped when ws_strict_handshake is False (default)."""
        mock_urandom.return_value = b"\x00" * 16

        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        ws_frame = self._build_ws_frame(ready_json)

        # No Sec-WebSocket-Accept header - should still work with default settings
        ws_response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "\r\n"
        ).encode()

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            ws_response,
            ws_frame[:2],
            ws_frame[2:],
        ]

        # Default ws_strict_handshake=False
        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )

        result = client.connect()
        assert result["message"] == "ready"

    @staticmethod
    def _build_ws_frame(payload: bytes) -> bytes:
        """Build an unmasked WebSocket text frame."""
        frame = bytearray()
        frame.append(0x81)
        plen = len(payload)
        if plen < 126:
            frame.append(plen)
        elif plen < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(payload)
        return bytes(frame)


class TestWebSocketPackageOptional:
    @patch("client.websocket.client._WEBSOCKET_AVAILABLE", False)
    def test_direct_connection_without_websocket_raises_helpful_error(self):
        client = WebSocketClient("127.0.0.1", 9001, connection_method="direct")

        with pytest.raises(AmariConnectionError) as exc_info:
            client.connect()

        assert "websocket-client" in str(exc_info.value)
        assert "pip install" in str(exc_info.value)
        assert "connection_method='proxy'" in str(exc_info.value)

    @patch("client.websocket.client._WEBSOCKET_AVAILABLE", False)
    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_proxy_connection_works_without_websocket_package(
        self, mock_urandom, mock_conn
    ):
        mock_urandom.return_value = b"\x00" * 16

        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        ws_frame = self._build_ws_frame(ready_json)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ws_frame[:2],
            ws_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )

        result = client.connect()
        assert result["message"] == "ready"

    @staticmethod
    def _build_ws_frame(payload: bytes) -> bytes:
        """Build an unmasked WebSocket text frame."""
        frame = bytearray()
        frame.append(0x81)
        plen = len(payload)
        if plen < 126:
            frame.append(plen)
        elif plen < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(payload)
        return bytes(frame)


# ── IMS API Proxy Tests ─────────────────────────────────────────────


class TestIMSApiWithProxy:
    """Tests for IMS API operations over proxy connections."""

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_ims_users_get_via_proxy(self, mock_urandom, mock_conn):
        """Test IMS users_get command works over proxy."""
        from client.websocket.ims import IMSApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        users_response = json.dumps(
            {
                "message_id": 1,
                "users": [{"impu": "sip:user1@ims.local", "registered": True}],
            }
        ).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(users_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9002,  # IMS default port
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        ims = IMSApi(client)
        result = ims.users_get()

        assert "users" in result
        assert len(result["users"]) == 1
        assert result["users"][0]["impu"] == "sip:user1@ims.local"

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_ims_send_sms_via_proxy(self, mock_urandom, mock_conn):
        """Test IMS send_sms command works over proxy."""
        from client.websocket.ims import IMSApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        sms_response = json.dumps({"message_id": 1, "status": "sent"}).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(sms_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9002,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        ims = IMSApi(client)
        result = ims.send_sms(impu="sip:user@ims.local", text="Hello via proxy")

        assert result["status"] == "sent"

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_ims_dialog_get_via_proxy(self, mock_urandom, mock_conn):
        """Test IMS dialog_get command works over proxy."""
        from client.websocket.ims import IMSApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        dialog_response = json.dumps(
            {"message_id": 1, "dialogs": [{"session_id": "sess1", "state": "active"}]}
        ).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(dialog_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9002,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        ims = IMSApi(client)
        result = ims.dialog_get()

        assert "dialogs" in result
        assert result["dialogs"][0]["session_id"] == "sess1"

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_ims_license_via_proxy(self, mock_urandom, mock_conn):
        """Test IMS license command works over proxy."""
        from client.websocket.ims import IMSApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        license_response = json.dumps(
            {"message_id": 1, "license": {"valid": True, "product": "IMS"}}
        ).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(license_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9002,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        ims = IMSApi(client)
        result = ims.license()

        assert result["license"]["valid"] is True

    @staticmethod
    def _build_ws_frame(payload: bytes) -> bytes:
        """Build an unmasked WebSocket text frame."""
        frame = bytearray()
        frame.append(0x81)
        plen = len(payload)
        if plen < 126:
            frame.append(plen)
        elif plen < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(payload)
        return bytes(frame)


# ── UE API Proxy Tests ──────────────────────────────────────────────


class TestUEApiWithProxy:
    """Tests for UE Simulator API operations over proxy connections."""

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_ue_power_on_via_proxy(self, mock_urandom, mock_conn):
        """Test UE power_on command works over proxy."""
        from client.websocket.ue import UEApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        power_response = json.dumps({"message_id": 1, "status": "ok"}).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(power_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9003,  # UE Sim default port
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        ue = UEApi(client)
        result = ue.power_on(ue_id=1)

        assert result["status"] == "ok"

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_ue_power_off_via_proxy(self, mock_urandom, mock_conn):
        """Test UE power_off command works over proxy."""
        from client.websocket.ue import UEApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        power_response = json.dumps({"message_id": 1, "status": "ok"}).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(power_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9003,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        ue = UEApi(client)
        result = ue.power_off(ue_id=1)

        assert result["status"] == "ok"

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_ue_get_via_proxy(self, mock_urandom, mock_conn):
        """Test UE ue_get command works over proxy."""
        from client.websocket.ue import UEApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        # Keep response small to avoid extended length encoding
        ue_response = json.dumps(
            {"message_id": 1, "ue_list": [{"ue_id": 1, "imsi": "001010123456789"}]}
        ).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(ue_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9003,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        ue = UEApi(client)
        result = ue.ue_get()

        assert "ue_list" in result
        assert len(result["ue_list"]) == 1
        assert result["ue_list"][0]["imsi"] == "001010123456789"

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_ue_add_via_proxy(self, mock_urandom, mock_conn):
        """Test UE ue_add command works over proxy."""
        from client.websocket.ue import UEApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        add_response = json.dumps(
            {"message_id": 1, "ue_id": 3, "status": "created"}
        ).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(add_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9003,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        ue = UEApi(client)
        result = ue.ue_add(
            imsi="001010123456791",
            k="00112233445566778899aabbccddeeff",
            opc="00112233445566778899aabbccddeeff",
        )

        assert result["ue_id"] == 3
        assert result["status"] == "created"

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_ue_stats_via_proxy(self, mock_urandom, mock_conn):
        """Test UE stats command works over proxy."""
        from client.websocket.ue import UEApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        stats_response = json.dumps(
            {
                "message_id": 1,
                "ue_count": 5,
                "active_count": 3,
                "throughput": {"dl": 100.5, "ul": 50.2},
            }
        ).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(stats_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9003,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        ue = UEApi(client)
        result = ue.stats()

        assert result["ue_count"] == 5
        assert result["active_count"] == 3

    @staticmethod
    def _build_ws_frame(payload: bytes) -> bytes:
        """Build an unmasked WebSocket text frame."""
        frame = bytearray()
        frame.append(0x81)
        plen = len(payload)
        if plen < 126:
            frame.append(plen)
        elif plen < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(payload)
        return bytes(frame)


# ── ENB API Proxy Tests ─────────────────────────────────────────────


class TestENBApiWithProxy:
    """Tests for ENB API operations over proxy connections."""

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_enb_stats_via_proxy(self, mock_urandom, mock_conn):
        """Test ENB stats command works over proxy."""
        from client.websocket.enb import ENBApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        stats_response = json.dumps(
            {"message_id": 1, "cells": [{"cell_id": 1, "dl_bitrate": 150.5}]}
        ).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(stats_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9001,  # ENB default port
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        enb = ENBApi(client)
        result = enb.stats()

        assert "cells" in result
        assert result["cells"][0]["cell_id"] == 1

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_enb_cell_gain_via_proxy(self, mock_urandom, mock_conn):
        """Test ENB cell_gain command works over proxy."""
        from client.websocket.enb import ENBApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        gain_response = json.dumps({"message_id": 1, "status": "ok"}).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(gain_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9001,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        enb = ENBApi(client)
        result = enb.cell_gain(cell_id=1, gain=-10)

        assert result["status"] == "ok"

    @staticmethod
    def _build_ws_frame(payload: bytes) -> bytes:
        """Build an unmasked WebSocket text frame."""
        frame = bytearray()
        frame.append(0x81)
        plen = len(payload)
        if plen < 126:
            frame.append(plen)
        elif plen < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(payload)
        return bytes(frame)


# ── MME API Proxy Tests ─────────────────────────────────────────────


class TestMMEApiWithProxy:
    """Tests for MME API operations over proxy connections."""

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_mme_ue_get_via_proxy(self, mock_urandom, mock_conn):
        """Test MME ue_get command works over proxy."""
        from client.websocket.mme import MMEApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        ue_response = json.dumps(
            {
                "message_id": 1,
                "ue_list": [{"imsi": "001010123456789", "state": "registered"}],
            }
        ).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(ue_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9000,  # MME default port
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        mme = MMEApi(client)
        result = mme.ue_get()

        assert "ue_list" in result
        assert result["ue_list"][0]["imsi"] == "001010123456789"

    @patch("client.websocket.client._socket.create_connection")
    @patch("client.websocket.client.os.urandom")
    def test_mme_ue_detach_via_proxy(self, mock_urandom, mock_conn):
        """Test MME ue_detach command works over proxy."""
        from client.websocket.mme import MMEApi

        mock_urandom.return_value = b"\x00" * 16
        mock_sock = MagicMock()
        mock_conn.return_value = mock_sock

        ready_json = json.dumps({"message": "ready"}).encode()
        detach_response = json.dumps({"message_id": 1, "status": "ok"}).encode()
        ready_frame = self._build_ws_frame(ready_json)
        response_frame = self._build_ws_frame(detach_response)

        mock_sock.recv.side_effect = [
            b"HTTP/1.1 200 Connection established\r\n\r\n",
            b"HTTP/1.1 101 Switching Protocols\r\n\r\n",
            ready_frame[:2],
            ready_frame[2:],
            response_frame[:2],
            response_frame[2:],
        ]

        client = WebSocketClient(
            "10.0.0.1",
            9000,
            connection_method="proxy",
            proxy_host="proxy.example.com",
            proxy_tls=False,
        )
        client.connect()

        mme = MMEApi(client)
        result = mme.ue_detach(imsi="001010123456789")

        assert result["status"] == "ok"

    @staticmethod
    def _build_ws_frame(payload: bytes) -> bytes:
        """Build an unmasked WebSocket text frame."""
        frame = bytearray()
        frame.append(0x81)
        plen = len(payload)
        if plen < 126:
            frame.append(plen)
        elif plen < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", plen))
        frame.extend(payload)
        return bytes(frame)
