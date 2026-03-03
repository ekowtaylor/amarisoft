"""Low-level WebSocket client for Amarisoft Remote API communication."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import socket as _socket
import ssl as _ssl
import struct
import threading
import time
from enum import Enum
from typing import Any, Callable

# websocket-client is optional - only needed for direct connections
try:
    import websocket

    _WEBSOCKET_AVAILABLE = True
except ImportError:
    websocket = None  # type: ignore[assignment]
    _WEBSOCKET_AVAILABLE = False

from .exceptions import (
    AmariConnectionError,
    AmariTimeoutError,
    AuthenticationError,
    CommandError,
    ProxyConnectionError,
)

logger = logging.getLogger(__name__)

# Maximum number of unsolicited messages to skip before giving up
_MAX_SKIP = 200

# WebSocket GUID for Sec-WebSocket-Accept validation (RFC 6455)
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class ConnectionMethod(str, Enum):
    """Connection method for WebSocket client."""

    DIRECT = "direct"
    PROXY = "proxy"


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
        connection_method: ConnectionMethod | str = ConnectionMethod.DIRECT,
        proxy_host: str | None = None,
        proxy_port: int = 8082,
        proxy_tls: bool = True,
        proxy_insecure: bool = True,
        proxy_client_cert: str | None = None,
        proxy_client_key: str | None = None,
        ws_strict_handshake: bool = False,
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
            connection_method: Connection method to use. ``direct`` for
                standard WebSocket, ``proxy`` for HTTP CONNECT tunneling.
            proxy_host: Hostname of the HTTP CONNECT proxy. Required when
                ``connection_method`` is ``proxy``.
            proxy_port: Port of the HTTP CONNECT proxy (default: 8082).
            proxy_tls: Use TLS for the proxy connection (default: True).
            proxy_insecure: Skip certificate verification for proxy TLS
                (default: True).
            proxy_client_cert: Path to client certificate PEM file for
                proxy authentication.
            proxy_client_key: Path to separate client key file. If None,
                the key is expected to be in the cert file.
            ws_strict_handshake: Enforce RFC 6455 Sec-WebSocket-Accept
                validation during handshake. When ``False`` (default),
                validation is skipped for compatibility with servers that
                may not fully implement RFC 6455. Set to ``True`` to
                enforce strict compliance.
        """
        self.host = host
        self.port = port
        self.password = password
        self.ssl = ssl
        self.timeout = timeout
        self.ssl_verify = ssl_verify
        self.auto_reconnect = auto_reconnect

        # Proxy configuration
        if isinstance(connection_method, str):
            connection_method = ConnectionMethod(connection_method)
        self.connection_method = connection_method
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_tls = proxy_tls
        self.proxy_insecure = proxy_insecure
        self.proxy_client_cert = proxy_client_cert
        self.proxy_client_key = proxy_client_key
        self.ws_strict_handshake = ws_strict_handshake

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

        self._ws: Any = None
        self._tunnel_sock: _socket.socket | None = None
        self._ready = False
        self._message_id = 0
        self._lock = threading.Lock()

    @property
    def uri(self) -> str:
        scheme = "wss" if self.ssl else "ws"
        return f"{scheme}://{self.host}:{self.port}"

    @property
    def connected(self) -> bool:
        if self._tunnel_sock is not None:
            return self._ready
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
            ProxyConnectionError: If proxy tunnel cannot be established.
            AuthenticationError: If authentication fails.
            AmariTimeoutError: If no ready message is received in time.
        """
        if self.connected:
            return {"message": "ready"}

        if self.connection_method == ConnectionMethod.PROXY:
            ready_msg = self._connect_via_proxy()
        else:
            ready_msg = self._connect_direct()

        # Authenticate if password is set
        if self.password:
            self._send_frame(
                {
                    "message": "authenticate",
                    "password": self.password,
                }
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

    def _connect_direct(self) -> dict[str, Any]:
        """Connect directly using the websocket-client library."""
        if not _WEBSOCKET_AVAILABLE:
            raise AmariConnectionError(
                "Direct connection requires the 'websocket-client' package. "
                "Install it with: pip install websocket-client\n"
                "Alternatively, use connection_method='proxy' which uses raw sockets."
            )

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
        return ready_msg

    def _connect_via_proxy(self) -> dict[str, Any]:
        """Connect via HTTP CONNECT proxy tunnel with raw WebSocket handling."""
        if not self.proxy_host:
            raise ProxyConnectionError(
                "proxy_host is required when connection_method is 'proxy'"
            )

        # Establish TCP connection to proxy
        try:
            sock = _socket.create_connection(
                (self.proxy_host, self.proxy_port),
                timeout=self.timeout,
            )
        except OSError as e:
            raise ProxyConnectionError(
                f"Failed to connect to proxy {self.proxy_host}:{self.proxy_port}: {e}"
            ) from e

        # Wrap in TLS if proxy requires it
        if self.proxy_tls:
            ctx = _ssl.create_default_context()
            if self.proxy_insecure:
                ctx.check_hostname = False
                ctx.verify_mode = _ssl.CERT_NONE
            if self.proxy_client_cert:
                ctx.load_cert_chain(
                    certfile=self.proxy_client_cert,
                    keyfile=self.proxy_client_key,
                )
            try:
                server_hostname = None if self.proxy_insecure else self.proxy_host
                sock = ctx.wrap_socket(sock, server_hostname=server_hostname)
            except _ssl.SSLError as e:
                sock.close()
                raise ProxyConnectionError(f"Proxy TLS handshake failed: {e}") from e

        # Send HTTP CONNECT request
        connect_hostport = self._format_hostport(self.host, self.port)
        connect_req = (
            f"CONNECT {connect_hostport} HTTP/1.1\r\n"
            f"Host: {connect_hostport}\r\n"
            "Proxy-Connection: Keep-Alive\r\n"
            "\r\n"
        ).encode("ascii")

        try:
            sock.sendall(connect_req)
            resp = self._recv_until(sock)
        except OSError as e:
            sock.close()
            raise ProxyConnectionError(f"Proxy CONNECT request failed: {e}") from e

        # Verify CONNECT succeeded
        first_line = resp.split(b"\r\n", 1)[0]
        if b" 200 " not in first_line:
            sock.close()
            raise ProxyConnectionError(
                f"Proxy CONNECT failed: {first_line.decode('utf-8', 'replace')}"
            )

        self._tunnel_sock = sock

        # Perform WebSocket handshake over the tunnel
        try:
            self._ws_handshake(sock, connect_hostport)
        except AmariConnectionError:
            self.close()
            raise

        # Wait for ready message
        ready_msg = self._recv()
        if ready_msg.get("message") != "ready":
            self.close()
            raise AmariConnectionError(
                f"Expected 'ready' message, got: {ready_msg.get('message')}"
            )
        return ready_msg

    def _format_hostport(self, host: str, port: int) -> str:
        """Format host:port, bracketing IPv6 addresses."""
        if ":" in host:
            return f"[{host}]:{port}"
        return f"{host}:{port}"

    def _recv_until(
        self,
        sock: _socket.socket,
        marker: bytes = b"\r\n\r\n",
        limit: int = 65536,
    ) -> bytes:
        """Receive data until marker is found."""
        data = b""
        while marker not in data:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if len(data) > limit:
                raise RuntimeError("Response header too large")
        return data

    def _ws_handshake(self, sock: _socket.socket, host_header: str) -> None:
        """Perform WebSocket handshake over the given socket.

        Optionally validates the server's Sec-WebSocket-Accept header per RFC 6455
        when ws_strict_handshake is True.
        """
        key = base64.b64encode(os.urandom(16)).decode()
        handshake = (
            "GET / HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Origin: http://{host_header}\r\n"
            "\r\n"
        )
        sock.sendall(handshake.encode("utf-8"))

        resp = self._recv_until(sock)
        first_line = resp.split(b"\r\n", 1)[0]
        if b"101" not in first_line:
            raise AmariConnectionError(
                f"WebSocket handshake failed: {first_line.decode('utf-8', 'replace')}"
            )

        # Validate Sec-WebSocket-Accept per RFC 6455 (optional)
        if self.ws_strict_handshake:
            expected_accept = base64.b64encode(
                hashlib.sha1((key + _WS_GUID).encode()).digest()
            ).decode()

            # Parse headers from response
            accept_value = None
            for line in resp.split(b"\r\n"):
                if line.lower().startswith(b"sec-websocket-accept:"):
                    accept_value = line.split(b":", 1)[1].strip().decode()
                    break

            if accept_value != expected_accept:
                raise AmariConnectionError(
                    f"WebSocket handshake failed: invalid Sec-WebSocket-Accept "
                    f"(expected {expected_accept}, got {accept_value})"
                )

    def reconnect(self) -> dict[str, Any]:
        """Close and re-establish the connection.

        Returns:
            The ``ready`` message from the server.
        """
        self.close()
        return self.connect()

    def close(self) -> None:
        """Close the WebSocket connection."""
        self._ready = False

        # Close tunnel socket if using proxy
        sock = self._tunnel_sock
        if sock is not None:
            self._tunnel_sock = None
            try:
                sock.close()
            except OSError:
                pass
            logger.info("Disconnected from %s:%d (via proxy)", self.host, self.port)
            return

        # Close websocket-client connection
        ws = self._ws
        if ws is not None:
            self._ws = None
            try:
                ws.close()
            except Exception:
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

            self._send_frame(message)

            return self._recv_matching(msg_id)

    def send_raw(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send a message without adding a ``message_id``.

        Returns the next message from the server (which may be
        unsolicited).
        """
        self._ensure_connected()

        self._send_frame(message)

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

            self._send_batch_frame(messages)

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
        if self._tunnel_sock is not None:
            return self._recv_ws_frame()

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

    def _send_frame(self, message: dict[str, Any]) -> None:
        """Send a WebSocket frame (for proxy mode) or use websocket library."""
        payload = json.dumps(message)
        logger.debug("TX >>> %s", payload)

        if self._tunnel_sock is not None:
            self._send_ws_frame(payload.encode("utf-8"))
        else:
            try:
                self._ws.send(payload)
            except websocket.WebSocketException as e:
                self._ready = False
                raise AmariConnectionError(f"Send failed: {e}") from e

    def _send_batch_frame(self, messages: list[dict[str, Any]]) -> None:
        """Send multiple messages as a JSON array batch."""
        payload = json.dumps(messages)
        logger.debug("TX (batch) >>> %s", payload)

        if self._tunnel_sock is not None:
            self._send_ws_frame(payload.encode("utf-8"))
        else:
            try:
                self._ws.send(payload)
            except websocket.WebSocketException as e:
                self._ready = False
                raise AmariConnectionError(f"Batch send failed: {e}") from e

    def _send_ws_frame(self, payload: bytes) -> None:
        """Send a masked WebSocket text frame over the tunnel socket."""
        sock = self._tunnel_sock
        if sock is None:
            raise AmariConnectionError("Tunnel socket not connected")

        mask_key = os.urandom(4)
        frame = bytearray()
        frame.append(0x81)  # FIN + text opcode

        plen = len(payload)
        if plen < 126:
            frame.append(0x80 | plen)
        elif plen < 65536:
            frame.append(0x80 | 126)
            frame.extend(struct.pack(">H", plen))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack(">Q", plen))

        frame.extend(mask_key)
        frame.extend(bytearray(b ^ mask_key[i % 4] for i, b in enumerate(payload)))

        try:
            sock.sendall(frame)
        except OSError as e:
            self._ready = False
            raise AmariConnectionError(f"Send failed: {e}") from e

    def _recv_ws_frame(self) -> dict[str, Any]:
        """Receive and decode a WebSocket frame from the tunnel socket."""
        sock = self._tunnel_sock
        if sock is None:
            raise AmariConnectionError("Tunnel socket not connected")

        try:
            sock.settimeout(self.timeout)
            hdr = self._recv_exact(sock, 2)
            if len(hdr) < 2:
                raise AmariConnectionError("Connection closed by server")

            b1, b2 = hdr
            opcode = b1 & 0x0F
            masked = (b2 & 0x80) != 0
            length = b2 & 0x7F

            if length == 126:
                ext = self._recv_exact(sock, 2)
                length = struct.unpack(">H", ext)[0]
            elif length == 127:
                ext = self._recv_exact(sock, 8)
                length = struct.unpack(">Q", ext)[0]

            if masked:
                mkey = self._recv_exact(sock, 4)
            else:
                mkey = None

            payload_data = self._recv_exact(sock, length)

            if mkey:
                payload_data = bytes(
                    b ^ mkey[i % 4] for i, b in enumerate(payload_data)
                )

        except _socket.timeout as e:
            raise AmariTimeoutError(f"Timed out waiting for response: {e}") from e
        except OSError as e:
            self._ready = False
            raise AmariConnectionError(f"Receive failed: {e}") from e

        # Handle close frame
        if opcode == 8:
            self._ready = False
            raise AmariConnectionError("Server closed connection")

        # Ping frame - send pong
        if opcode == 9:
            self._send_pong(payload_data)
            return self._recv_ws_frame()

        # Text frame
        if opcode == 1:
            raw = payload_data.decode("utf-8")
            logger.debug("RX <<< %s", raw)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                raise AmariConnectionError(f"Invalid JSON from server: {e}") from e
            if isinstance(data, list):
                return data[0] if data else {}
            return data

        raise AmariConnectionError(f"Unexpected WebSocket opcode: {opcode}")

    def _recv_exact(self, sock: _socket.socket, n: int) -> bytes:
        """Receive exactly n bytes from the socket."""
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                break
            data += chunk
        return data

    def _send_pong(self, payload: bytes) -> None:
        """Send a pong frame in response to a ping."""
        sock = self._tunnel_sock
        if sock is None:
            return

        mask_key = os.urandom(4)
        frame = bytearray()
        frame.append(0x8A)  # FIN + pong opcode

        plen = len(payload)
        if plen < 126:
            frame.append(0x80 | plen)
        else:
            frame.append(0x80 | 126)
            frame.extend(struct.pack(">H", plen))

        frame.extend(mask_key)
        frame.extend(bytearray(b ^ mask_key[i % 4] for i, b in enumerate(payload)))

        try:
            sock.sendall(frame)
        except OSError:
            pass

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
