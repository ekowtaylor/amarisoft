"""Low-level WebSocket client for Amarisoft Remote API communication."""

from __future__ import annotations

import json
import logging
import socket as _socket
import ssl as _ssl
import threading
import time
from typing import Any, Callable

import websocket

from .exceptions import (
    AmariConnectionError,
    AmariTimeoutError,
    AuthenticationError,
    CommandError,
)

logger = logging.getLogger(__name__)

# Maximum number of unsolicited messages to skip before giving up
_MAX_SKIP = 200


class WebSocketClient:
    """WebSocket client for communicating with an Amarisoft service.

    Handles connection lifecycle, message serialization, and response routing.
    Each instance targets a single Amarisoft service (eNB, MME, IMS, or UE).

    Not thread-safe: callers sharing a single client across threads must
    synchronize externally. For single-threaded use the internal lock ensures
    message-id uniqueness across interleaved ``send`` / ``send_batch`` calls.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9001,
        password: str | None = None,
        ssl: bool = False,
        timeout: float = 10.0,
        ssl_context: _ssl.SSLContext | None = None,
        auto_reconnect: bool = False,
        ssl_verify: bool = False,
    ):
        """
        Args:
            host: Hostname or IP of the Amarisoft service.
            port: WebSocket port.
            password: Optional authentication password (com_auth).
            ssl: Use ``wss://`` instead of ``ws://``.
            timeout: Default timeout in seconds for send/receive.
            ssl_context: Custom :class:`ssl.SSLContext` for TLS (e.g. to
                trust self-signed certificates). If *None* and *ssl* is
                True, a context is created automatically — see
                *ssl_verify*.
            auto_reconnect: Automatically reconnect on send failure.
            ssl_verify: Verify the server's TLS certificate. When
                ``False`` (the default) and no *ssl_context* is provided,
                certificate verification is disabled — convenient for
                Callboxes using self-signed certificates. Set to ``True``
                to enforce standard certificate validation.
        """
        self.host = host
        self.port = port
        self.password = password
        self.ssl = ssl
        self.timeout = timeout
        self.ssl_verify = ssl_verify
        self.auto_reconnect = auto_reconnect

        # Build ssl_context: explicit context wins, otherwise honour ssl_verify
        if ssl_context is not None:
            self.ssl_context = ssl_context
        elif ssl and not ssl_verify:
            ctx = _ssl.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE
            self.ssl_context = ctx
        else:
            self.ssl_context = None

        self._ws: websocket.WebSocket | None = None
        self._ready = False
        self._message_id = 0
        self._lock = threading.Lock()

    @property
    def uri(self) -> str:
        scheme = "wss" if self.ssl else "ws"
        return f"{scheme}://{self.host}:{self.port}"

    @property
    def connected(self) -> bool:
        ws = self._ws
        return ws is not None and ws.connected

    def is_listening(self, timeout: float = 2.0) -> bool:
        """Check if the WebSocket service is listening.

        Performs a lightweight TCP socket connection check to determine if
        the service is listening on the configured host and port. This does
        not establish a WebSocket handshake, making it fast and non-intrusive.

        Args:
            timeout: Connection timeout in seconds (default: 2.0).

        Returns:
            True if the service is listening (accepting connections),
            False otherwise.

        Example::

            client = WebSocketClient(host="192.168.1.80", port=9001)

            if client.is_listening():
                print("WebSocket service is listening")
                client.connect()
            else:
                print("WebSocket service is not available")
        """
        try:
            with _socket.create_connection((self.host, self.port), timeout=timeout):
                return True
        except OSError:
            return False

    def connect(self) -> dict[str, Any]:
        """Establish a WebSocket connection and wait for the ready message.

        Returns:
            The ``ready`` message from the server containing version info.

        Raises:
            AmariConnectionError: If the connection cannot be established.
            AuthenticationError: If authentication fails.
            AmariTimeoutError: If no ready message is received in time.
        """
        if self.connected:
            return {"message": "ready"}

        try:
            self._ws = websocket.WebSocket(
                sslopt={"context": self.ssl_context} if self.ssl_context else None,
            )
            self._ws.settimeout(self.timeout)
            self._ws.connect(self.uri, origin="Python-AmariClient")
        except websocket.WebSocketException as e:
            raise AmariConnectionError(f"Failed to connect to {self.uri}: {e}") from e
        except OSError as e:
            raise AmariConnectionError(f"Failed to connect to {self.uri}: {e}") from e

        # Wait for ready message
        ready_msg = self._recv()
        if ready_msg.get("message") != "ready":
            self.close()
            raise AmariConnectionError(
                f"Expected 'ready' message, got: {ready_msg.get('message')}"
            )

        # Authenticate if password is set
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
                raise AuthenticationError(
                    f"Authentication failed: {auth_resp['error']}"
                )

        self._ready = True
        logger.info("Connected to %s", self.uri)
        return ready_msg

    def reconnect(self) -> dict[str, Any]:
        """Close and re-establish the connection.

        Returns:
            The ``ready`` message from the server.
        """
        self.close()
        return self.connect()

    def close(self) -> None:
        """Close the WebSocket connection."""
        ws = self._ws
        if ws is not None:
            self._ws = None
            self._ready = False
            try:
                ws.close()
            except websocket.WebSocketException:
                pass
            logger.info("Disconnected from %s:%d", self.host, self.port)

    def send(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON message and return the matching response.

        Automatically assigns a ``message_id`` for request/response
        correlation.  Unsolicited messages (events, logs) received before
        the matching response are silently skipped (up to an internal
        limit to prevent infinite loops).

        Args:
            message: The message dictionary to send.

        Returns:
            The parsed JSON response from the server.

        Raises:
            AmariConnectionError: If not connected or connection lost.
            CommandError: If the server returns an error.
            AmariTimeoutError: If no response is received in time.
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
                self._ready = False
                raise AmariConnectionError(f"Send failed: {e}") from e

            return self._recv_matching(msg_id)

    def send_raw(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send a message without adding a ``message_id``.

        Returns the next message from the server (which may be
        unsolicited).
        """
        self._ensure_connected()

        payload = json.dumps(message)
        logger.debug("TX (raw) >>> %s", payload)

        try:
            self._ws.send(payload)
        except websocket.WebSocketException as e:
            self._ready = False
            raise AmariConnectionError(f"Send failed: {e}") from e

        return self._recv()

    def send_batch(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Send multiple messages as a JSON array batch.

        Args:
            messages: List of message dictionaries to send.

        Returns:
            List of response dictionaries, one per input message.
        """
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
                self._ready = False
                raise AmariConnectionError(f"Batch send failed: {e}") from e

            responses: list[dict[str, Any]] = []
            for msg in messages:
                responses.append(self._recv_matching(msg["message_id"]))
            return responses

    def listen(
        self,
        callback: Callable[[dict[str, Any]], bool | None],
        duration: float | None = None,
    ) -> None:
        """Listen for unsolicited messages (events, logs, registered data).

        Args:
            callback: Called with each received message. Return ``False``
                to stop listening.
            duration: Maximum listen time in seconds. ``None`` for
                indefinite (blocks until callback returns ``False`` or
                the connection times out).
        """
        self._ensure_connected()

        start = time.monotonic()
        while True:
            if duration is not None and (time.monotonic() - start) >= duration:
                break
            try:
                msg = self._recv()
            except AmariTimeoutError:
                if duration is not None:
                    continue
                break
            except AmariConnectionError:
                break
            if callback(msg) is False:
                break

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    def _ensure_connected(self) -> None:
        """Raise or attempt reconnect if not connected."""
        if self.connected:
            return
        if self.auto_reconnect:
            logger.info("Auto-reconnecting to %s", self.uri)
            self.reconnect()
        else:
            raise AmariConnectionError("Not connected. Call connect() first.")

    def _recv_matching(self, msg_id: int) -> dict[str, Any]:
        """Receive messages until one with a matching ``message_id`` arrives.

        Raises ``AmariConnectionError`` if too many non-matching messages
        are received (guard against infinite loop).
        """
        for _ in range(_MAX_SKIP):
            resp = self._recv()
            if resp.get("message_id") == msg_id:
                if "error" in resp:
                    raise CommandError(
                        resp["error"],
                        error_code=resp.get("error_code"),
                    )
                return resp
            logger.debug("Skipped unsolicited message: %s", resp.get("message"))
        raise AmariConnectionError(
            f"No matching response for message_id={msg_id} after "
            f"{_MAX_SKIP} messages"
        )

    def _recv(self) -> dict[str, Any]:
        """Receive and parse a single JSON message from the server."""
        try:
            raw = self._ws.recv()
        except websocket.WebSocketTimeoutException as e:
            raise AmariTimeoutError(f"Timed out waiting for response: {e}") from e
        except websocket.WebSocketException as e:
            self._ready = False
            raise AmariConnectionError(f"Receive failed: {e}") from e

        if not raw:
            raise AmariConnectionError("Received empty message from server")

        logger.debug("RX <<< %s", raw)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise AmariConnectionError(f"Invalid JSON from server: {e}") from e

        # The server may respond with a JSON array in batch mode.
        if isinstance(data, list):
            # Return first element; callers that need multi-element
            # responses should use send_batch which handles this.
            return data[0] if data else {}
        return data

    # ──────────────────────────────────────────────
    # Context manager / dunder
    # ──────────────────────────────────────────────

    def __enter__(self) -> WebSocketClient:
        self.connect()
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        status = "connected" if self.connected else "disconnected"
        return f"WebSocketClient({self.uri}, {status})"
