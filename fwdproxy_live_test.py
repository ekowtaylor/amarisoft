#!/usr/bin/env python3
"""
Amarisoft WebSocket Test Script via fwdproxy.corp
Routes WebSocket traffic through Meta's forward proxy to reach corp network.

This script uses HTTP CONNECT tunneling through fwdproxy.regional_corp
to establish WebSocket connections to Amarisoft Callbox devices in the
corp/lab network from production devservers.

Requirements:
    - Run on a Meta devserver with access to fwdproxy.regional_corp
    - Valid Thrift TLS certificates ($THRIFT_TLS_CL_CERT_PATH)
    - /etc/fbwhoami must be sourced for REGION_DATACENTER_PREFIX

Usage:
    python3 fwdproxy_live_test.py
"""

import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import subprocess
import time
from typing import Any


def get_region_prefix() -> str:
    """Get the region datacenter prefix from fbwhoami."""
    result = subprocess.run(
        ['bash', '-c', 'source /etc/fbwhoami && echo $REGION_DATACENTER_PREFIX'],
        capture_output=True, text=True
    )
    prefix = result.stdout.strip()
    if not prefix:
        raise RuntimeError(
            "Could not determine REGION_DATACENTER_PREFIX. "
            "Make sure /etc/fbwhoami exists and is properly configured."
        )
    return prefix


def get_thrift_cert_paths() -> tuple[str, str]:
    """Get Thrift TLS certificate paths."""
    cert_path = os.environ.get('THRIFT_TLS_CL_CERT_PATH')
    key_path = os.environ.get('THRIFT_TLS_CL_KEY_PATH', cert_path)
    
    if not cert_path:
        # Get current username
        username = os.environ.get('USER', os.environ.get('LOGNAME', 'root'))
        
        # Try common default locations (in order of preference)
        default_paths = [
            # User-specific devserver certs
            f'/var/facebook/credentials/{username}/x509/{username}.pem',
            f'/var/facebook/credentials/{username}/x509/{username}_dc.pem',
            # Agent x509 certs
            f'/var/facebook/credentials/{username}/agent_x509/client/client.pem',
            # System-wide certs
            '/var/facebook/credentials/x509/client/client.pem',
            '/var/facebook/x509_identity/client.pem',
        ]
        for path in default_paths:
            if os.path.exists(path):
                cert_path = path
                key_path = path
                print(f"    [Cert] Found certificate at: {path}")
                break
    
    if not cert_path or not os.path.exists(cert_path):
        raise RuntimeError(
            "Could not find Thrift TLS certificates. "
            "Set THRIFT_TLS_CL_CERT_PATH environment variable or ensure "
            "certificates exist at default locations."
        )
    
    return cert_path, key_path


class ProxyTunneledSocket:
    """
    Creates a TCP tunnel through fwdproxy.corp using HTTP CONNECT.

    This establishes an mTLS connection to fwdproxy.regional_corp:8082,
    sends an HTTP CONNECT request to create a tunnel to the target,
    then returns a socket that can communicate directly with the target.
    """

    PROXY_PORT = 8082

    def __init__(self, target_host: str, target_port: int, timeout: float = 30.0):
        self.target_host = target_host
        self.target_port = target_port
        self.timeout = timeout
        self.sock = None
        self._region = None
        self._cert_path = None
        self._key_path = None

    def connect(self) -> socket.socket:
        """Establish tunnel through fwdproxy and return the tunneled socket."""
        # Get configuration
        self._region = get_region_prefix()
        self._cert_path, self._key_path = get_thrift_cert_paths()

        proxy_host = f"fwdproxy-regional-corp.{self._region}.fbinfra.net"

        print(f"    [Proxy] Connecting to {proxy_host}:{self.PROXY_PORT}")
        print(f"    [Proxy] Using cert: {self._cert_path}")

        # Create socket and connect to proxy
        # fwdproxy uses IPv6
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)

        # Resolve proxy hostname
        proxy_addrs = socket.getaddrinfo(
            proxy_host, self.PROXY_PORT,
            socket.AF_INET6, socket.SOCK_STREAM
        )
        if not proxy_addrs:
            raise ConnectionError(f"Could not resolve {proxy_host}")

        proxy_addr = proxy_addrs[0][4]
        print(f"    [Proxy] Resolved to {proxy_addr[0]}")

        # Connect to proxy
        self.sock.connect(proxy_addr)

        # Wrap with mTLS
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.load_cert_chain(self._cert_path, self._key_path)

        self.sock = context.wrap_socket(self.sock, server_hostname=proxy_host)
        print(f"    [Proxy] mTLS handshake complete")

        # Send HTTP CONNECT request
        # Format target for CONNECT (brackets for IPv6)
        if ":" in self.target_host:
            connect_target = f"[{self.target_host}]:{self.target_port}"
        else:
            connect_target = f"{self.target_host}:{self.target_port}"

        connect_request = (
            f"CONNECT {connect_target} HTTP/1.1\r\n"
            f"Host: {connect_target}\r\n"
            f"User-Agent: amarisoft-live-test/1.0\r\n"
            f"Proxy-Connection: keep-alive\r\n"
            f"\r\n"
        )

        print(f"    [Proxy] Sending CONNECT to {connect_target}")
        self.sock.sendall(connect_request.encode('utf-8'))

        # Read response
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Proxy closed connection during CONNECT")
            response += chunk

        response_str = response.decode('utf-8', errors='ignore')
        print(f"    [Proxy] Response: {response_str.split(chr(13))[0]}")

        # Check for success (200 Connection Established)
        if "200" not in response_str:
            raise ConnectionError(f"Proxy CONNECT failed: {response_str[:200]}")

        print(f"    [Proxy] Tunnel established!")
        return self.sock

    def close(self):
        """Close the tunnel."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


class RawWebSocket:
    """
    Minimal WebSocket client implementation using raw sockets.
    Implements RFC 6455 WebSocket protocol.

    Can optionally use a pre-connected socket (for proxy tunneling).
    """

    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, host: str, port: int, use_ssl: bool = False,
                 timeout: float = 10.0, use_proxy: bool = False):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.use_proxy = use_proxy
        self.sock = None
        self._proxy_tunnel = None

    def connect(self) -> bool:
        """Establish WebSocket connection with handshake."""
        if self.use_proxy:
            # Use fwdproxy.corp tunnel
            self._proxy_tunnel = ProxyTunneledSocket(self.host, self.port, self.timeout)
            self.sock = self._proxy_tunnel.connect()
        else:
            # Direct connection
            if ":" in self.host:
                self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            else:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.sock.settimeout(self.timeout)

            if self.use_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.sock = context.wrap_socket(self.sock, server_hostname=self.host)

            self.sock.connect((self.host, self.port))

        # Perform WebSocket handshake
        self._handshake()
        return True

    def _handshake(self):
        """Perform the WebSocket opening handshake."""
        key = base64.b64encode(os.urandom(16)).decode("ascii")

        if ":" in self.host:
            http_host = f"[{self.host}]:{self.port}"
        else:
            http_host = f"{self.host}:{self.port}"

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

        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("Connection closed during handshake")
            response += chunk

        response_str = response.decode("utf-8", errors="ignore")
        if "101" not in response_str:
            raise ConnectionError(f"WebSocket handshake failed: {response_str[:200]}")

        expected_accept = base64.b64encode(
            hashlib.sha1((key + self.GUID).encode("utf-8")).digest()
        ).decode("ascii")

        if expected_accept not in response_str:
            raise ConnectionError("Invalid Sec-WebSocket-Accept in handshake")

    def send(self, data: str) -> None:
        """Send a text message over the WebSocket."""
        payload = data.encode("utf-8")
        self._send_frame(0x1, payload)

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        """Send a WebSocket frame with masking."""
        length = len(payload)
        frame = bytearray([0x80 | opcode])

        if length <= 125:
            frame.append(0x80 | length)
        elif length <= 65535:
            frame.append(0x80 | 126)
            frame.extend(struct.pack(">H", length))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack(">Q", length))

        mask = os.urandom(4)
        frame.extend(mask)

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
        header = self._recv_exact(2)

        _fin = (header[0] >> 7) & 1
        opcode = header[0] & 0x0F
        masked = (header[1] >> 7) & 1
        length = header[1] & 0x7F

        if length == 126:
            length = struct.unpack(">H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack(">Q", self._recv_exact(8))[0]

        mask = None
        if masked:
            mask = self._recv_exact(4)

        payload = self._recv_exact(length)

        if mask:
            payload = bytearray(payload)
            for i in range(len(payload)):
                payload[i] ^= mask[i % 4]
            payload = bytes(payload)

        if opcode == 0x8:
            raise ConnectionError("WebSocket closed by server")
        elif opcode == 0x9:
            self._send_frame(0xA, payload)
            return self._recv_frame()
        elif opcode == 0xA:
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
                self._send_frame(0x8, b"")
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

        if self._proxy_tunnel:
            self._proxy_tunnel.close()
            self._proxy_tunnel = None


class AmariWebSocket:
    """Amarisoft API client using raw WebSocket with optional proxy support."""

    def __init__(self, host: str, port: int, use_ssl: bool = False, use_proxy: bool = False):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.use_proxy = use_proxy
        self.ws = None
        self._msg_id = 0

    def connect(self, timeout: float = 10.0, password: str = None) -> bool:
        self.ws = RawWebSocket(self.host, self.port, self.use_ssl, timeout, self.use_proxy)
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


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

HOST = "2620:10d:c052:12a:aaa1:59ff:fe88:d39"  # Amarisoft Callbox IPv6
PASSWORD = None
USE_SSL = False
USE_PROXY = True  # Enable fwdproxy.corp tunneling

ENB_PORT = 9001
MME_PORT = 9000
IMS_PORT = 9002

CONNECT_TIMEOUT = 30.0  # Longer timeout for proxy connections


# ══════════════════════════════════════════════════════════════════════════════
# TEST RUNNER
# ══════════════════════════════════════════════════════════════════════════════

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
        self.log(f"Proxy: {'fwdproxy.corp (enabled)' if USE_PROXY else 'disabled'}")

        try:
            self.enb = AmariWebSocket(HOST, ENB_PORT, USE_SSL, USE_PROXY)
            self.enb.connect(CONNECT_TIMEOUT, PASSWORD)
            self.log("eNB connected", "ok")
        except Exception as e:
            self.log(f"eNB connection failed: {e}", "error")
            self.results["connection"] = "FAIL"
            return False

        try:
            self.mme = AmariWebSocket(HOST, MME_PORT, USE_SSL, USE_PROXY)
            self.mme.connect(CONNECT_TIMEOUT, PASSWORD)
            self.log("MME connected", "ok")
        except Exception as e:
            self.log(f"MME connection failed: {e}", "warn")

        try:
            self.ims = AmariWebSocket(HOST, IMS_PORT, USE_SSL, USE_PROXY)
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
        print(f"  (Via fwdproxy.corp - Meta Forward Proxy)")
        print(f"{'═' * 60}")
        print(f"  Host: {HOST}")
        print(f"  Proxy: fwdproxy.regional_corp:8082")
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


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    # Check if we're on a devserver
    if not os.path.exists('/etc/fbwhoami'):
        print("ERROR: This script must be run on a Meta devserver.")
        print("       /etc/fbwhoami not found.")
        sys.exit(1)

    test = LiveTest(verbose='-v' in sys.argv or '--verbose' in sys.argv)
    success = test.run()
    print(f"\nTest completed with status: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1)
