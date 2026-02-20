#!/usr/bin/env python3
"""Standalone live test script for Amarisoft Callbox.

Uses WebSocket directly - no external dependencies on amarisoft package.

Requirements:
    pip install websocket-client

Usage:
    1. Edit the configuration section below (HOST, ports, etc.)
    2. Run: python live_test.py
"""

import json
import ssl
import sys
import time
from typing import Any

try:
    import websocket
except ImportError:
    print("ERROR: websocket-client is required")
    print("Install with: pip install websocket-client")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════
# CONFIGURATION - MODIFY THESE VALUES FOR YOUR SETUP
# ══════════════════════════════════════════════════════════════

HOST = "2620:10d:c052:12a:aaa1:59ff:fe88:d39"  # Callbox IPv6 address (devserver)
PASSWORD = None              # WebSocket password (None if not required)
USE_SSL = False              # Use WSS (TLS) connection

# WebSocket ports (Amarisoft defaults)
ENB_PORT = 9001              # eNB/gNB WebSocket port
MME_PORT = 9000              # MME/AMF WebSocket port
IMS_PORT = 9002              # IMS WebSocket port

# Timeouts
CONNECT_TIMEOUT = 10.0       # Connection timeout (seconds)


# ══════════════════════════════════════════════════════════════
# WEBSOCKET CLIENT
# ══════════════════════════════════════════════════════════════

class AmariWebSocket:
    """Simple WebSocket client for Amarisoft API."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.ws = None
        self._msg_id = 0

    def connect(self) -> bool:
        """Connect to the WebSocket server."""
        scheme = "wss" if USE_SSL else "ws"
        # IPv6 addresses need brackets in URLs
        host = f"[{self.host}]" if ":" in self.host else self.host
        url = f"{scheme}://{host}:{self.port}"

        sslopt = None
        if USE_SSL:
            sslopt = {"cert_reqs": ssl.CERT_NONE, "check_hostname": False}

        self.ws = websocket.create_connection(url, timeout=CONNECT_TIMEOUT, sslopt=sslopt)

        if PASSWORD:
            result = self.send("authenticate", {"password": PASSWORD})
            if not result.get("authenticated"):
                raise ConnectionError("Authentication failed")
        return True

    def close(self):
        """Close connection."""
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

    def send(self, method: str, params: dict | None = None) -> dict:
        """Send message and wait for response."""
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


# ══════════════════════════════════════════════════════════════
# TEST IMPLEMENTATION
# ══════════════════════════════════════════════════════════════

class LiveTest:
    """Live test runner for Amarisoft Callbox."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.enb: AmariWebSocket | None = None
        self.mme: AmariWebSocket | None = None
        self.ims: AmariWebSocket | None = None
        self.results: dict[str, Any] = {}

    def log(self, msg: str, level: str = "info"):
        """Print log message."""
        prefix = {"info": "  ", "ok": "  ✓", "warn": "  ⚠", "error": "  ✗"}.get(level, "  ")
        if level == "header":
            print(f"\n{'═' * 60}\n  {msg}\n{'═' * 60}")
        else:
            print(f"{prefix} {msg}")

    def vlog(self, msg: str):
        """Print verbose log message."""
        if self.verbose:
            print(f"    → {msg}")

    def connect(self) -> bool:
        """Connect to the Callbox services."""
        self.log("CONNECTING TO CALLBOX", "header")
        self.log(f"Host: {HOST}")

        # Connect to eNB
        try:
            self.enb = AmariWebSocket(HOST, ENB_PORT)
            self.enb.connect()
            self.log("eNB connected", "ok")
        except Exception as e:
            self.log(f"eNB connection failed: {e}", "error")
            self.results["connection"] = "FAIL"
            return False

        # Connect to MME
        try:
            self.mme = AmariWebSocket(HOST, MME_PORT)
            self.mme.connect()
            self.log("MME connected", "ok")
        except Exception as e:
            self.log(f"MME connection failed: {e}", "warn")

        # Connect to IMS
        try:
            self.ims = AmariWebSocket(HOST, IMS_PORT)
            self.ims.connect()
            self.log("IMS connected", "ok")
        except Exception as e:
            self.log(f"IMS connection failed: {e}", "warn")

        self.results["connection"] = "PASS"
        return True

    def disconnect(self):
        """Disconnect from all services."""
        for ws in [self.enb, self.mme, self.ims]:
            if ws:
                ws.close()

    def test_enb_status(self) -> bool:
        """Test eNB/gNB status."""
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
        """Test eNB configuration."""
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
        """Test MME/AMF status."""
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
        """Test IMS status."""
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
        """Print test summary."""
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
        """Run all tests."""
        print(f"\n{'═' * 60}")
        print(f"  AMARISOFT CALLBOX LIVE TEST")
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


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test = LiveTest()
    success = test.run()
    sys.exit(0 if success else 1)
