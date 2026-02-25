"""Tests for WebSocketClient."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from client.websocket.client import _MAX_SKIP, WebSocketClient
from client.websocket.exceptions import (
    AmariConnectionError,
    AmariTimeoutError,
    AuthenticationError,
    CommandError,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _make_ws_mock(recv_queue: list[str] | None = None):
    """Return a mock ``websocket.WebSocket`` wired with a recv queue."""
    ws = MagicMock()
    ws.connected = True
    if recv_queue is not None:
        ws.recv.side_effect = recv_queue
    return ws


# ── URI ──────────────────────────────────────────────────────────────


class TestUri:
    def test_ws_uri(self):
        c = WebSocketClient("10.0.0.1", 9001)
        assert c.uri == "ws://10.0.0.1:9001"

    def test_wss_uri(self):
        c = WebSocketClient("10.0.0.1", 9001, ssl=True)
        assert c.uri == "wss://10.0.0.1:9001"


# ── connect() ────────────────────────────────────────────────────────


class TestConnect:
    @patch("amarisoft.client.websocket.WebSocket")
    def test_connect_ready_handshake(self, MockWS):
        ready = json.dumps({"message": "ready", "version": "2024-06-01"})
        ws = _make_ws_mock([ready])
        MockWS.return_value = ws

        client = WebSocketClient("127.0.0.1", 9001)
        result = client.connect()

        ws.connect.assert_called_once_with(
            "ws://127.0.0.1:9001", origin="Python-AmariClient"
        )
        assert result["message"] == "ready"
        assert client._ready is True

    @patch("amarisoft.client.websocket.WebSocket")
    def test_connect_with_auth(self, MockWS):
        ready = json.dumps({"message": "ready"})
        auth_ok = json.dumps({"message": "authenticate"})
        ws = _make_ws_mock([ready, auth_ok])
        MockWS.return_value = ws

        client = WebSocketClient("127.0.0.1", 9001, password="secret")
        client.connect()

        # verify authenticate message was sent
        sent = ws.send.call_args[0][0]
        assert json.loads(sent) == {
            "message": "authenticate",
            "password": "secret",
        }

    @patch("amarisoft.client.websocket.WebSocket")
    def test_connect_auth_failure(self, MockWS):
        ready = json.dumps({"message": "ready"})
        auth_fail = json.dumps({"error": "invalid password"})
        ws = _make_ws_mock([ready, auth_fail])
        MockWS.return_value = ws

        client = WebSocketClient("127.0.0.1", 9001, password="wrong")
        with pytest.raises(AuthenticationError):
            client.connect()

    @patch("amarisoft.client.websocket.WebSocket")
    def test_connect_already_connected_returns_cached_ready(self, MockWS):
        ready = json.dumps({"message": "ready"})
        ws = _make_ws_mock([ready])
        MockWS.return_value = ws

        client = WebSocketClient()
        client.connect()
        # Second call should not touch the websocket again
        result = client.connect()
        assert result == {"message": "ready"}
        assert MockWS.return_value.connect.call_count == 1

    @patch("amarisoft.client.websocket.WebSocket")
    def test_connect_bad_ready_raises(self, MockWS):
        bad = json.dumps({"message": "error", "error": "busy"})
        ws = _make_ws_mock([bad])
        MockWS.return_value = ws

        client = WebSocketClient()
        with pytest.raises(AmariConnectionError, match="Expected 'ready'"):
            client.connect()


# ── close() ──────────────────────────────────────────────────────────


class TestClose:
    @patch("amarisoft.client.websocket.WebSocket")
    def test_close_resets_state(self, MockWS):
        ready = json.dumps({"message": "ready"})
        ws = _make_ws_mock([ready])
        MockWS.return_value = ws

        client = WebSocketClient()
        client.connect()
        client.close()

        assert client._ready is False
        assert client._ws is None

    def test_close_when_not_connected_is_noop(self):
        client = WebSocketClient()
        client.close()  # should not raise


# ── reconnect() ──────────────────────────────────────────────────────


class TestReconnect:
    @patch("amarisoft.client.websocket.WebSocket")
    def test_reconnect_calls_close_then_connect(self, MockWS):
        ready = json.dumps({"message": "ready"})
        ws = _make_ws_mock([ready, ready])
        MockWS.return_value = ws

        client = WebSocketClient()
        client.connect()
        result = client.reconnect()
        assert result["message"] == "ready"


# ── send() ───────────────────────────────────────────────────────────


class TestSend:
    @patch("amarisoft.client.websocket.WebSocket")
    def test_send_assigns_message_id_and_returns_response(self, MockWS):
        ready = json.dumps({"message": "ready"})
        resp = json.dumps({"message": "stats", "message_id": 1})
        ws = _make_ws_mock([ready, resp])
        MockWS.return_value = ws

        client = WebSocketClient()
        client.connect()
        result = client.send({"message": "stats"})

        sent = json.loads(ws.send.call_args[0][0])
        assert sent["message_id"] == 1
        assert result["message"] == "stats"

    @patch("amarisoft.client.websocket.WebSocket")
    def test_send_skips_unsolicited_messages(self, MockWS):
        ready = json.dumps({"message": "ready"})
        unsolicited = json.dumps({"message": "log_event", "data": "x"})
        resp = json.dumps({"message": "stats", "message_id": 1})
        ws = _make_ws_mock([ready, unsolicited, resp])
        MockWS.return_value = ws

        client = WebSocketClient()
        client.connect()
        result = client.send({"message": "stats"})
        assert result["message_id"] == 1

    @patch("amarisoft.client.websocket.WebSocket")
    def test_send_raises_command_error_on_error_response(self, MockWS):
        ready = json.dumps({"message": "ready"})
        err = json.dumps(
            {
                "message_id": 1,
                "error": "unknown command",
                "error_code": 404,
            }
        )
        ws = _make_ws_mock([ready, err])
        MockWS.return_value = ws

        client = WebSocketClient()
        client.connect()
        with pytest.raises(CommandError) as exc_info:
            client.send({"message": "bad"})
        assert exc_info.value.error_code == 404

    def test_send_raises_connection_error_when_not_connected(self):
        client = WebSocketClient()
        with pytest.raises(AmariConnectionError, match="Not connected"):
            client.send({"message": "stats"})

    @patch("amarisoft.client.websocket.WebSocket")
    def test_send_raises_after_max_skip(self, MockWS):
        ready = json.dumps({"message": "ready"})
        unsolicited = json.dumps({"message": "event"})
        ws = _make_ws_mock([ready] + [unsolicited] * (_MAX_SKIP + 1))
        MockWS.return_value = ws

        client = WebSocketClient()
        client.connect()
        with pytest.raises(AmariConnectionError, match="No matching response"):
            client.send({"message": "stats"})


# ── send_raw() ───────────────────────────────────────────────────────


class TestSendRaw:
    @patch("amarisoft.client.websocket.WebSocket")
    def test_send_raw_no_message_id(self, MockWS):
        ready = json.dumps({"message": "ready"})
        resp = json.dumps({"message": "ok"})
        ws = _make_ws_mock([ready, resp])
        MockWS.return_value = ws

        client = WebSocketClient()
        client.connect()
        result = client.send_raw({"message": "test"})

        sent = json.loads(ws.send.call_args[0][0])
        assert "message_id" not in sent
        assert result["message"] == "ok"


# ── send_batch() ─────────────────────────────────────────────────────


class TestSendBatch:
    @patch("amarisoft.client.websocket.WebSocket")
    def test_send_batch_collects_matching_responses(self, MockWS):
        ready = json.dumps({"message": "ready"})
        r1 = json.dumps({"message_id": 1, "data": "a"})
        r2 = json.dumps({"message_id": 2, "data": "b"})
        ws = _make_ws_mock([ready, r1, r2])
        MockWS.return_value = ws

        client = WebSocketClient()
        client.connect()
        results = client.send_batch(
            [
                {"message": "stats"},
                {"message": "version"},
            ]
        )

        assert len(results) == 2
        assert results[0]["data"] == "a"
        assert results[1]["data"] == "b"

        # Verify the batch was sent as a JSON array
        sent = json.loads(ws.send.call_args[0][0])
        assert isinstance(sent, list)
        assert len(sent) == 2


# ── listen() ─────────────────────────────────────────────────────────


class TestListen:
    @patch("amarisoft.client.websocket.WebSocket")
    def test_listen_calls_callback_and_stops_on_false(self, MockWS):
        ready = json.dumps({"message": "ready"})
        e1 = json.dumps({"message": "event1"})
        e2 = json.dumps({"message": "event2"})
        ws = _make_ws_mock([ready, e1, e2])
        MockWS.return_value = ws

        client = WebSocketClient()
        client.connect()

        received = []

        def cb(msg):
            received.append(msg)
            return False  # stop immediately

        client.listen(cb)
        assert len(received) == 1
        assert received[0]["message"] == "event1"

    @patch("amarisoft.client.websocket.WebSocket")
    @patch("amarisoft.client.time.monotonic")
    def test_listen_respects_duration(self, mock_time, MockWS):
        import websocket as _ws_mod

        ready = json.dumps({"message": "ready"})
        ws = _make_ws_mock([ready])
        MockWS.return_value = ws

        # monotonic is called: once on connect (not used), once at listen start,
        # then once per loop iteration to check duration
        mock_time.side_effect = [0.0, 0.0, 5.0]

        client = WebSocketClient()
        client.connect()

        # After connect, switch recv to raise timeout
        ws.recv.side_effect = _ws_mod.WebSocketTimeoutException("timeout")
        client.listen(lambda msg: True, duration=3.0)
        # Should exit because 5.0 >= 3.0


# ── _ensure_connected() ─────────────────────────────────────────────


class TestEnsureConnected:
    @patch("amarisoft.client.websocket.WebSocket")
    def test_auto_reconnect(self, MockWS):
        ready = json.dumps({"message": "ready"})
        resp = json.dumps({"message_id": 1, "data": "ok"})
        ws = _make_ws_mock([ready, ready, resp])
        MockWS.return_value = ws

        client = WebSocketClient(auto_reconnect=True)
        client.connect()

        # Simulate a disconnection
        ws.connected = False
        # Now send should trigger auto-reconnect
        ws.connected = True
        result = client.send({"message": "test"})
        assert result["data"] == "ok"


# ── Context manager ──────────────────────────────────────────────────


class TestContextManager:
    @patch("amarisoft.client.websocket.WebSocket")
    def test_enter_connects_exit_closes(self, MockWS):
        ready = json.dumps({"message": "ready"})
        ws = _make_ws_mock([ready])
        MockWS.return_value = ws

        with WebSocketClient() as client:
            assert client._ready is True
        assert client._ready is False


# ── __repr__ ─────────────────────────────────────────────────────────


class TestRepr:
    def test_repr_disconnected(self):
        client = WebSocketClient("10.0.0.1", 9001)
        assert repr(client) == "WebSocketClient(ws://10.0.0.1:9001, disconnected)"

    @patch("amarisoft.client.websocket.WebSocket")
    def test_repr_connected(self, MockWS):
        ready = json.dumps({"message": "ready"})
        ws = _make_ws_mock([ready])
        MockWS.return_value = ws

        client = WebSocketClient("10.0.0.1", 9001)
        client.connect()
        assert repr(client) == "WebSocketClient(ws://10.0.0.1:9001, connected)"


# ── is_listening() ──────────────────────────────────────────────────


class TestIsListening:
    @patch("client.websocket.client._socket.create_connection")
    def test_is_listening_returns_true_when_service_available(self, mock_conn):
        """Test is_listening returns True when service accepts connections."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = WebSocketClient("192.168.1.80", 9001)
        result = client.is_listening()

        assert result is True
        mock_conn.assert_called_once_with(("192.168.1.80", 9001), timeout=2.0)

    @patch("client.websocket.client._socket.create_connection")
    def test_is_listening_returns_false_on_connection_refused(self, mock_conn):
        """Test is_listening returns False when connection is refused."""
        mock_conn.side_effect = OSError("Connection refused")

        client = WebSocketClient("192.168.1.80", 9001)
        result = client.is_listening()

        assert result is False

    @patch("client.websocket.client._socket.create_connection")
    def test_is_listening_returns_false_on_timeout(self, mock_conn):
        """Test is_listening returns False on timeout."""
        import socket

        mock_conn.side_effect = socket.timeout("Connection timed out")

        client = WebSocketClient("192.168.1.80", 9001)
        result = client.is_listening()

        assert result is False

    @patch("client.websocket.client._socket.create_connection")
    def test_is_listening_with_custom_timeout(self, mock_conn):
        """Test is_listening uses custom timeout."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = WebSocketClient("192.168.1.80", 9001)
        client.is_listening(timeout=5.0)

        mock_conn.assert_called_once_with(("192.168.1.80", 9001), timeout=5.0)

    @patch("client.websocket.client._socket.create_connection")
    def test_is_listening_uses_client_host_and_port(self, mock_conn):
        """Test is_listening uses the client's configured host and port."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = WebSocketClient("10.0.0.1", 9003)
        client.is_listening()

        mock_conn.assert_called_once_with(("10.0.0.1", 9003), timeout=2.0)

    @patch("client.websocket.client._socket.create_connection")
    def test_is_listening_does_not_require_connection(self, mock_conn):
        """Test is_listening works without establishing WebSocket connection."""
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock()

        client = WebSocketClient("192.168.1.80", 9001)
        assert client.connected is False

        result = client.is_listening()

        assert result is True
        assert client.connected is False
