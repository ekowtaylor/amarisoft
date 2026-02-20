#!/usr/bin/env python3
"""
Amarisoft WebSocket Test Script
Using raw Python sockets (no external dependencies)
"""

import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import time
from typing import Any


class RawWebSocket:
    """
    Minimal WebSocket client implementation using raw sockets.
    Implements RFC 6455 WebSocket protocol.
    """

    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, host: str, port: int, use_ssl: bool = False, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.sock = None

    def connect(self) -> bool:
        """Establish WebSocket connection with handshake."""
        # Create socket
        if ":" in self.host:
            # IPv6
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        else:
            # IPv4
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.settimeout(self.timeout)

        # Wrap with SSL if needed
        if self.use_ssl:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.sock = context.wrap_socket(self.sock, server_hostname=self.host)

        # Connect
        self.sock.connect((self.host, self.port))

        # Perform WebSocket handshake
        self._handshake()
        return True

    def _handshake(self):
        """Perform the WebSocket opening handshake."""
        # Generate random key
        key = base64.b64encode(os.urandom(16)).decode("ascii")

        # Format host for HTTP header (brackets for IPv6)
        if ":" in self.host:
            http_host = f"[{self.host}]:{self.port}"
        else:
            http_host = f"{self.host}:{self.port}"

        # Build HTTP upgrade request
        request = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {http_host}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )

        self.sock.sendall(request.encode("utf-8"))

        # Read response
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("Connection closed during handshake")
            response += chunk

        # Verify response
        response_str = response.decode("utf-8", errors="ignore")
        if "101" not in response_str:
            raise ConnectionError(f"WebSocket handshake failed: {response_str[:200]}")

        # Verify accept key
        expected_accept = base64.b64encode(
            hashlib.sha1((key + self.GUID).encode("utf-8")).digest()
        ).decode("ascii")

        if expected_accept not in response_str:
            raise ConnectionError("Invalid Sec-WebSocket-Accept in handshake")

    def send(self, data: str) -> None:
        """Send a text message over the WebSocket."""
        payload = data.encode("utf-8")
        self._send_frame(0x1, payload)  # 0x1 = text frame

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        """Send a WebSocket frame with masking (required for client-to-server)."""
        length = len(payload)

        # First byte: FIN bit + opcode
        frame = bytearray([0x80 | opcode])

        # Second byte: MASK bit + payload length
        if length <= 125:
            frame.append(0x80 | length)
        elif length <= 65535:
            frame.append(0x80 | 126)
            frame.extend(struct.pack(">H", length))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack(">Q", length))

        # Masking key (4 random bytes)
        mask = os.urandom(4)
        frame.extend(mask)

        # Masked payload
        masked_payload = bytearray(length)
        for i in range(length):
            masked_payload[i] = payload[i] ^ mask[i % 4]
        frame.extend(masked_payload)

        self.sock.sendall(bytes(frame))

    def recv(self) -> str:
        """Receive a text message from the WebSocket."""
        data = self._recv_frame()
        return data.decode("utf-8")

    def _recv_frame(self) -> bytes:
        """Receive and decode a WebSocket frame."""
        # Read first 2 bytes
        header = self._recv_exact(2)

        _fin = (header[0] >> 7) & 1  # FIN bit (unused but kept for protocol completeness)
        opcode = header[0] & 0x0F
        masked = (header[1] >> 7) & 1
        length = header[1] & 0x7F

        # Extended payload length
        if length == 126:
            length = struct.unpack(">H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._recv_exact(8))[0]

        # Masking key (if present, usually not for server-to-client)
        mask = None
        if masked:
            mask = self._recv_exact(4)

        # Payload
        payload = self._recv_exact(length)

        # Unmask if needed
        if mask:
            payload = bytearray(payload)
            for i in range(len(payload)):
                payload[i] ^= mask[i % 4]
            payload = bytes(payload)

        # Handle control frames
        if opcode == 0x8:
            # Close frame
            raise ConnectionError("WebSocket closed by server")
        elif opcode == 0x9:
            # Ping - send pong
            self._send_frame(0xA, payload)
            return self._recv_frame()
        elif opcode == 0xA:
            # Pong - ignore and read next frame
            return self._recv_frame()

        return payload

    def _recv_exact(self, n: int) -> bytes:
        """Receive exactly n bytes."""
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data

    def close(self):
        """Close the WebSocket connection."""
        if self.sock:
            try:
                # Send close frame
                self._send_frame(0x8, b"")
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


class AmariWebSocket:
    """Amarisoft API client using raw WebSocket."""

    def __init__(self, host: str, port: int, use_ssl: bool = False):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.ws = None
        self._msg_id = 0

    def connect(self, timeout: float = 10.0, password: str = None) -> bool:
        self.ws = RawWebSocket(self.host, self.port, self.use_ssl, timeout)
        self.ws.connect()

        if password:
            result = self.send("authenticate", {"password": password})
            if not result.get("authenticated"):
                raise ConnectionError("Authentication failed")
        return True

    def close(self):
        if self.ws:
            self.ws.close()
            self.ws = None

    def send(self, method: str, params: dict | None = None) -> dict:
        if not self.ws:
            raise ConnectionError("Not connected")

        self._msg_id += 1
        message = {"message": method, "message_id": self._msg_id}
        if params:
            message.update(params)

        self.ws.send(json.dumps(message))

        while True:
            data = json.loads(self.ws.recv())
            if data.get("message_id") == self._msg_id:
                if "error" in data:
                    raise RuntimeError(f"API error: {data['error']}")
                return data


# Configuration
HOST = "2620:10d:c052:12a:aaa1:59ff:fe88:d39"
PASSWORD = None
USE_SSL = False

ENB_PORT = 9001
MME_PORT = 9000
IMS_PORT = 9002

CONNECT_TIMEOUT = 10.0


class LiveTest:

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.enb: AmariWebSocket | None = None
        self.mme: AmariWebSocket | None = None
        self.ims: AmariWebSocket | None = None
        self.results: dict[str, Any] = {}

    def log(self, msg: str, level: str = "info"):
        prefix = {"info": "  ", "ok": "  ✓", "warn": "  ⚠", "error": "  ✗"}.get(level, "  ")
        if level == "header":
            print(f"\n{'═' * 60}\n  {msg}\n{'═' * 60}")
        else:
            print(f"{prefix} {msg}")

    def vlog(self, msg: str):
        if self.verbose:
            print(f"    → {msg}")

    def connect(self) -> bool:
        self.log("CONNECTING TO CALLBOX", "header")
        self.log(f"Host: {HOST}")

        try:
            self.enb = AmariWebSocket(HOST, ENB_PORT, USE_SSL)
            self.enb.connect(CONNECT_TIMEOUT, PASSWORD)
            self.log("eNB connected", "ok")
        except Exception as e:
            self.log(f"eNB connection failed: {e}", "error")
            self.results["connection"] = "FAIL"
            return False

        try:
            self.mme = AmariWebSocket(HOST, MME_PORT, USE_SSL)
            self.mme.connect(CONNECT_TIMEOUT, PASSWORD)
            self.log("MME connected", "ok")
        except Exception as e:
            self.log(f"MME connection failed: {e}", "warn")

        try:
            self.ims = AmariWebSocket(HOST, IMS_PORT, USE_SSL)
            self.ims.connect(CONNECT_TIMEOUT, PASSWORD)
            self.log("IMS connected", "ok")
        except Exception as e:
            self.log(f"IMS connection failed: {e}", "warn")

        self.results["connection"] = "PASS"
        return True

    def disconnect(self):
        for ws in [self.enb, self.mme, self.ims]:
            if ws:
                ws.close()

    def test_enb_status(self) -> bool:
        self.log("ENB/GNB STATUS", "header")

        if not self.enb:
            self.results["enb_status"] = "FAIL"
            return False

        try:
            response = self.enb.send("stats")
            self.vlog(f"Response: {json.dumps(response, indent=2)[:500]}")

            cells = response.get("cells", {})
            if cells:
                self.log(f"Active cells: {len(cells)}", "ok")
                for cell_id, data in cells.items():
                    dl = data.get("dl_bitrate", 0) / 1e6
                    ul = data.get("ul_bitrate", 0) / 1e6
                    self.log(f"  Cell {cell_id}: {data.get('rat', '?').upper()}, "
                            f"Rate={dl:.1f}/{ul:.1f} Mbps")
                self.results["enb_status"] = "PASS"
                self.results["cell_count"] = len(cells)
            else:
                self.log("No active cells", "warn")
                self.results["enb_status"] = "WARN"
            return True
        except Exception as e:
            self.log(f"Failed: {e}", "error")
            self.results["enb_status"] = "FAIL"
            return False

    def test_enb_config(self) -> bool:
        self.log("ENB CONFIGURATION", "header")

        if not self.enb:
            self.results["config_status"] = "FAIL"
            return False

        try:
            response = self.enb.send("config_get")
            self.vlog(f"Config keys: {list(response.keys())}")

            version = response.get("version", "unknown")
            rf = response.get("rf_driver", {})
            rf_name = rf.get("name", "unknown") if isinstance(rf, dict) else str(rf)

            self.log(f"Version: {version}", "ok")
            self.log(f"RF Driver: {rf_name}")
            self.results["config_status"] = "PASS"
            self.results["version"] = version
            return True
        except Exception as e:
            self.log(f"Failed: {e}", "error")
            self.results["config_status"] = "FAIL"
            return False

    def test_mme_status(self) -> bool:
        self.log("MME/AMF STATUS", "header")

        if not self.mme:
            self.results["mme_status"] = "SKIP"
            return True

        try:
            response = self.mme.send("ue_get")
            self.vlog(f"Response: {json.dumps(response, indent=2)[:500]}")

            ue_list = response.get("ue_list", [])
            if ue_list:
                self.log(f"Attached UEs: {len(ue_list)}", "ok")
                for ue in ue_list:
                    self.log(f"  UE: IMSI={ue.get('imsi', 'N/A')}")
                self.results["mme_status"] = "PASS"
            else:
                self.log("No UEs attached", "warn")
                self.results["mme_status"] = "WARN"
            self.results["ue_count"] = len(ue_list)
            return True
        except Exception as e:
            self.log(f"Failed: {e}", "error")
            self.results["mme_status"] = "FAIL"
            return False

    def test_ims_status(self) -> bool:
        self.log("IMS STATUS", "header")

        if not self.ims:
            self.results["ims_status"] = "SKIP"
            return True

        try:
            response = self.ims.send("ue_get")
            ue_list = response.get("ue_list", [])
            if ue_list:
                self.log(f"IMS users: {len(ue_list)}", "ok")
            else:
                self.log("No IMS users", "info")
            self.results["ims_status"] = "PASS"
            return True
        except Exception as e:
            self.log(f"Failed: {e}", "error")
            self.results["ims_status"] = "FAIL"
            return False

    def print_summary(self) -> bool:
        print(f"\n{'═' * 60}\n  TEST SUMMARY\n{'═' * 60}")

        icon = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "SKIP": "○"}
        tests = [("Connection", "connection"), ("eNB Config", "config_status"),
                 ("eNB Status", "enb_status"), ("MME Status", "mme_status"),
                 ("IMS Status", "ims_status")]

        passed = failed = 0
        for name, key in tests:
            status = self.results.get(key, "N/A")
            print(f"  {icon.get(status, '?')} {name}: {status}")
            if status == "PASS": passed += 1
            elif status == "FAIL": failed += 1

        print("-" * 60)
        if "version" in self.results:
            print(f"  Version: {self.results['version']}")
        print("-" * 60)

        if failed > 0:
            print("\n  ✗ OVERALL: FAIL")
            return False
        print("\n  ✓ OVERALL: PASS")
        return True

    def run(self) -> bool:
        print(f"\n{'═' * 60}")
        print(f"  AMARISOFT CALLBOX LIVE TEST")
        print(f"  (Using raw Python sockets - no external dependencies)")
        print(f"{'═' * 60}")
        print(f"  Host: {HOST}")
        print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.connect():
            return self.print_summary()

        try:
            self.test_enb_config()
            self.test_enb_status()
            self.test_mme_status()
            self.test_ims_status()
        finally:
            self.disconnect()

        return self.print_summary()


# Run the test
test = LiveTest()
success = test.run()
print(f"\nTest completed with status: {'SUCCESS' if success else 'FAILURE'}")
