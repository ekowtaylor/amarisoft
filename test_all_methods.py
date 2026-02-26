#!/usr/bin/env python3
"""Test all REST API methods against the live Amarisoft callbox via HTTP over SSH.

This script tests the HTTP REST API endpoints through an SSH tunnel.

Usage:
    python test_all_methods.py [--verbose]

Requirements:
    - sshpass must be installed for password authentication
    - Network access to the Amarisoft callbox
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

sys.path.insert(0, ".")

from client.http_ssh import HTTPOverSSHClient, SSHConnectionError

# Configuration
SSH_HOST = "2620:10d:c052:12a:aaa1:59ff:fe88:d39"
SSH_USERNAME = "root"
SSH_PASSWORD = "toor"
REMOTE_API_PORT = 9010


def test_endpoint(
    client: HTTPOverSSHClient,
    method: str,
    endpoint: str,
    params: dict | None = None,
) -> tuple[bool, Any]:
    """Test a single endpoint and return success/failure with result."""
    try:
        if method == "GET":
            result = client.get(endpoint, params=params)
        elif method == "POST":
            result = client.post(endpoint, data=params)
        else:
            return False, f"Unsupported method: {method}"
        return True, result
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def print_result(name: str, success: bool, result: Any, verbose: bool = False) -> None:
    """Print test result."""
    status = "✓" if success else "✗"
    if success:
        if verbose and isinstance(result, dict):
            preview = json.dumps(result, default=str)[:80]
            print(f"  {status} {name}: {preview}...")
        else:
            print(f"  {status} {name}")
    else:
        # Truncate error message if too long
        error_msg = str(result)[:100]
        print(f"  {status} {name}: {error_msg}")


def test_general_endpoints(
    client: HTTPOverSSHClient, verbose: bool = False
) -> dict[str, bool]:
    """Test general REST API endpoints."""
    print("\n" + "=" * 60)
    print("TESTING GENERAL ENDPOINTS")
    print("=" * 60)

    results = {}
    tests = [
        ("GET /health", "GET", "/health", None),
        ("GET /services", "GET", "/services", None),
        ("GET /version", "GET", "/version", None),
        ("POST /services/connect", "POST", "/services/connect", None),
    ]

    for name, method, endpoint, params in tests:
        success, result = test_endpoint(client, method, endpoint, params)
        results[name] = success
        print_result(name, success, result, verbose)

    return results


def test_enb_endpoints(
    client: HTTPOverSSHClient, verbose: bool = False
) -> dict[str, bool]:
    """Test eNB REST API endpoints."""
    print("\n" + "=" * 60)
    print("TESTING ENB ENDPOINTS")
    print("=" * 60)

    results = {}
    tests = [
        # Base endpoints
        ("GET /enb/help", "GET", "/enb/help", None),
        ("GET /enb/config", "GET", "/enb/config", None),
        ("GET /enb/stats", "GET", "/enb/stats", None),
        ("GET /enb/stats?rf=true", "GET", "/enb/stats", {"rf": "true"}),
        ("GET /enb/ue", "GET", "/enb/ue", None),
        ("GET /enb/cells", "GET", "/enb/cells", None),
        ("GET /enb/logs", "GET", "/enb/logs", None),
        # New endpoints
        ("GET /enb/erab", "GET", "/enb/erab", None),
        ("GET /enb/qos-flow", "GET", "/enb/qos-flow", None),
        ("GET /enb/rf", "GET", "/enb/rf", None),
        ("GET /enb/rf/gain", "GET", "/enb/rf/gain", None),
        ("GET /enb/rf/power", "GET", "/enb/rf/power", None),
        ("GET /enb/snr", "GET", "/enb/snr", None),
        ("GET /enb/noise-level", "GET", "/enb/noise-level", None),
        ("GET /enb/trx", "GET", "/enb/trx", None),
        ("GET /enb/kpi", "GET", "/enb/kpi", None),
        # Interface endpoints
        ("GET /enb/interface/s1", "GET", "/enb/interface/s1", None),
        ("GET /enb/interface/ng", "GET", "/enb/interface/ng", None),
        ("GET /enb/interface/x2", "GET", "/enb/interface/x2", None),
        ("GET /enb/interface/xn", "GET", "/enb/interface/xn", None),
        ("GET /enb/interface/m2", "GET", "/enb/interface/m2", None),
    ]

    for name, method, endpoint, params in tests:
        success, result = test_endpoint(client, method, endpoint, params)
        results[name] = success
        print_result(name, success, result, verbose)

    return results


def test_mme_endpoints(
    client: HTTPOverSSHClient, verbose: bool = False
) -> dict[str, bool]:
    """Test MME REST API endpoints."""
    print("\n" + "=" * 60)
    print("TESTING MME ENDPOINTS")
    print("=" * 60)

    results = {}
    tests = [
        # Base endpoints
        ("GET /mme/help", "GET", "/mme/help", None),
        ("GET /mme/config", "GET", "/mme/config", None),
        ("GET /mme/stats", "GET", "/mme/stats", None),
        ("GET /mme/ue", "GET", "/mme/ue", None),
        ("GET /mme/logs", "GET", "/mme/logs", None),
        ("GET /mme/apn", "GET", "/mme/apn", None),
        # Status endpoints
        ("GET /mme/enb", "GET", "/mme/enb", None),
        ("GET /mme/gnb", "GET", "/mme/gnb", None),
        ("GET /mme/ng-ran", "GET", "/mme/ng-ran", None),
        # Interface endpoints
        ("GET /mme/interface/s6", "GET", "/mme/interface/s6", None),
        ("GET /mme/interface/s13", "GET", "/mme/interface/s13", None),
        ("GET /mme/interface/sgs", "GET", "/mme/interface/sgs", None),
        ("GET /mme/interface/n8", "GET", "/mme/interface/n8", None),
        ("GET /mme/interface/n12", "GET", "/mme/interface/n12", None),
        ("GET /mme/interface/n13", "GET", "/mme/interface/n13", None),
        ("GET /mme/interface/n17", "GET", "/mme/interface/n17", None),
        ("GET /mme/interface/sbc", "GET", "/mme/interface/sbc", None),
    ]

    for name, method, endpoint, params in tests:
        success, result = test_endpoint(client, method, endpoint, params)
        results[name] = success
        print_result(name, success, result, verbose)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test all REST API methods via HTTP over SSH"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output with response previews",
    )
    parser.add_argument(
        "--host", default=SSH_HOST, help=f"SSH host (default: {SSH_HOST})"
    )
    parser.add_argument("--password", default=SSH_PASSWORD, help="SSH password")
    args = parser.parse_args()

    print("=" * 60)
    print("AMARISOFT REST API METHOD TEST")
    print("=" * 60)
    print(f"\nTarget: {SSH_USERNAME}@{args.host}")
    print(f"API Port: {REMOTE_API_PORT}")

    # Create client
    client = HTTPOverSSHClient(
        ssh_host=args.host,
        ssh_username=SSH_USERNAME,
        ssh_password=args.password,
        remote_port=REMOTE_API_PORT,
    )

    # Check SSH connectivity
    print("\n[1] Checking SSH connectivity...")
    if not client.is_listening():
        print("    ✗ SSH service not reachable")
        return 1
    print("    ✓ SSH service reachable")

    # Connect
    print("\n[2] Establishing SSH tunnel...")
    try:
        client.connect()
        print(f"    ✓ Tunnel established: localhost:{client.local_port}")
    except SSHConnectionError as e:
        print(f"    ✗ Failed: {e}")
        return 1

    try:
        # Run all tests
        all_results: dict[str, dict[str, bool]] = {}

        all_results["general"] = test_general_endpoints(client, args.verbose)
        all_results["enb"] = test_enb_endpoints(client, args.verbose)
        all_results["mme"] = test_mme_endpoints(client, args.verbose)

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        total_pass = 0
        total_fail = 0

        for category, results in all_results.items():
            passed = sum(1 for v in results.values() if v)
            failed = sum(1 for v in results.values() if not v)
            total_pass += passed
            total_fail += failed
            status = "✓" if failed == 0 else "⚠"
            print(
                f"  {status} {category.upper():10} {passed:2} passed, {failed:2} failed"
            )

        print(f"\n  TOTAL: {total_pass} passed, {total_fail} failed")

        # Calculate pass rate
        total = total_pass + total_fail
        if total > 0:
            pass_rate = (total_pass / total) * 100
            print(f"  Pass Rate: {pass_rate:.1f}%")

        return 0 if total_fail == 0 else 1

    finally:
        print("\n[3] Closing tunnel...")
        client.close()
        print("    ✓ Done")


if __name__ == "__main__":
    sys.exit(main())
