#!/usr/bin/env python3
"""Test all WebSocket methods against the live Amarisoft callbox.

Run this script from the devserver:
    cd /home/ekowtaylor/amarisoft
    source venv/bin/activate
    python test_all_ws_methods.py
"""

import json
import sys
from typing import Any

from client.websocket import AmariError, Callbox, CommandError


def test_method(name: str, func) -> tuple[bool, Any]:
    """Test a single method and return success/failure with result."""
    try:
        result = func()
        return True, result
    except CommandError as e:
        return False, f"CommandError: {e}"
    except AmariError as e:
        return False, f"AmariError: {e}"
    except Exception as e:
        return False, f"Exception: {type(e).__name__}: {e}"


def print_result(name: str, success: bool, result: Any, verbose: bool = False):
    """Print test result."""
    status = "✓" if success else "✗"
    if success:
        if verbose and isinstance(result, dict):
            preview = json.dumps(result, default=str)[:80]
            print(f"  {status} {name}: {preview}...")
        else:
            print(f"  {status} {name}")
    else:
        print(f"  {status} {name}: {result}")


def test_enb_methods(cb: Callbox, verbose: bool = False) -> dict[str, bool]:
    """Test ENB methods."""
    print("\n" + "=" * 60)
    print("TESTING ENB METHODS")
    print("=" * 60)

    results = {}

    tests = [
        # Base methods
        ("help", lambda: cb.enb.help()),
        ("config_get", lambda: cb.enb.config_get()),
        ("stats", lambda: cb.enb.stats()),
        ("stats(rf=True)", lambda: cb.enb.stats(rf=True)),
        ("ue_get", lambda: cb.enb.ue_get()),
        ("log_get", lambda: cb.enb.log_get()),
        # ENB specific
        ("erab_get", lambda: cb.enb.erab_get()),
        ("qos_flow_get", lambda: cb.enb.qos_flow_get()),
        ("rf", lambda: cb.enb.rf()),
        ("s1_status", lambda: cb.enb.s1_status()),
        ("ng_status", lambda: cb.enb.ng_status()),
        ("x2_status", lambda: cb.enb.x2_status()),
        ("xn_status", lambda: cb.enb.xn_status()),
        ("m2_status", lambda: cb.enb.m2_status()),
        ("echo", lambda: cb.enb.echo({"test": "data"})),
        ("monitor", lambda: cb.enb.monitor()),
    ]

    for name, func in tests:
        success, result = test_method(name, func)
        results[name] = success
        print_result(name, success, result, verbose)

    return results


def test_mme_methods(cb: Callbox, verbose: bool = False) -> dict[str, bool]:
    """Test MME methods."""
    print("\n" + "=" * 60)
    print("TESTING MME METHODS")
    print("=" * 60)

    results = {}

    tests = [
        # Base methods
        ("help", lambda: cb.mme.help()),
        ("config_get", lambda: cb.mme.config_get()),
        ("stats", lambda: cb.mme.stats()),
        ("ue_get", lambda: cb.mme.ue_get()),
        ("log_get", lambda: cb.mme.log_get()),
        # MME specific
        ("enb_status", lambda: cb.mme.enb_status()),
        ("gnb_status", lambda: cb.mme.gnb_status()),
        ("ng_ran_status", lambda: cb.mme.ng_ran_status()),
        ("s6_status", lambda: cb.mme.s6_status()),
        ("s13_status", lambda: cb.mme.s13_status()),
        ("sgs_status", lambda: cb.mme.sgs_status()),
        ("n8_status", lambda: cb.mme.n8_status()),
        ("n12_status", lambda: cb.mme.n12_status()),
        ("n13_status", lambda: cb.mme.n13_status()),
        ("n17_status", lambda: cb.mme.n17_status()),
        ("sbc_status", lambda: cb.mme.sbc_status()),
        ("echo", lambda: cb.mme.echo({"test": "data"})),
    ]

    for name, func in tests:
        success, result = test_method(name, func)
        results[name] = success
        print_result(name, success, result, verbose)

    return results


def test_ims_methods(cb: Callbox, verbose: bool = False) -> dict[str, bool]:
    """Test IMS methods."""
    print("\n" + "=" * 60)
    print("TESTING IMS METHODS")
    print("=" * 60)

    if not cb.status.get("ims"):
        print("  IMS service not connected - skipping")
        return {}

    results = {}

    tests = [
        ("help", lambda: cb.ims.help()),
        ("config_get", lambda: cb.ims.config_get()),
        ("stats", lambda: cb.ims.stats()),
        ("users_get", lambda: cb.ims.users_get()),
        ("dialog_get", lambda: cb.ims.dialog_get()),
        ("license", lambda: cb.ims.license()),
        ("echo", lambda: cb.ims.echo({"test": "data"})),
    ]

    for name, func in tests:
        success, result = test_method(name, func)
        results[name] = success
        print_result(name, success, result, verbose)

    return results


def test_ue_methods(cb: Callbox, verbose: bool = False) -> dict[str, bool]:
    """Test UE simulator methods."""
    print("\n" + "=" * 60)
    print("TESTING UE SIMULATOR METHODS")
    print("=" * 60)

    if not cb.status.get("ue"):
        print("  UE simulator service not connected - skipping")
        return {}

    results = {}

    tests = [
        ("help", lambda: cb.ue.help()),
        ("config_get", lambda: cb.ue.config_get()),
        ("stats", lambda: cb.ue.stats()),
        ("ue_get", lambda: cb.ue.ue_get()),
        ("log_get", lambda: cb.ue.log_get()),
        ("echo", lambda: cb.ue.echo({"test": "data"})),
    ]

    for name, func in tests:
        success, result = test_method(name, func)
        results[name] = success
        print_result(name, success, result, verbose)

    return results


def main():
    print("=" * 60)
    print("AMARISOFT WEBSOCKET METHOD TEST")
    print("=" * 60)

    # Connect - use IPv6 with square brackets
    host = "2620:10d:c052:12a:aaa1:59ff:fe88:d39"
    print(f"\nConnecting to {host}...")

    try:
        cb = Callbox(host, password="toor")
        cb.connect_all()
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return 1

    try:
        print("\n" + "=" * 60)
        print("CONNECTION STATUS")
        print("=" * 60)
        print(f"  ENB: {'✓' if cb.status.get('enb') else '✗'}")
        print(f"  MME: {'✓' if cb.status.get('mme') else '✗'}")
        print(f"  IMS: {'✓' if cb.status.get('ims') else '✗'}")
        print(f"  UE:  {'✓' if cb.status.get('ue') else '✗'}")

        # Get help from each service to see supported messages
        if cb.status.get("enb"):
            help_result = cb.enb.help()
            messages = help_result.get("messages", [])
            print(f"\n  ENB supported messages ({len(messages)}):")
            for msg in sorted(messages):
                print(f"    - {msg}")

        if cb.status.get("mme"):
            help_result = cb.mme.help()
            messages = help_result.get("messages", [])
            print(f"\n  MME supported messages ({len(messages)}):")
            for msg in sorted(messages):
                print(f"    - {msg}")

        # Run tests
        all_results = {}

        if cb.status.get("enb"):
            all_results["enb"] = test_enb_methods(cb, verbose=True)

        if cb.status.get("mme"):
            all_results["mme"] = test_mme_methods(cb, verbose=True)

        if cb.status.get("ims"):
            all_results["ims"] = test_ims_methods(cb, verbose=True)

        if cb.status.get("ue"):
            all_results["ue"] = test_ue_methods(cb, verbose=True)

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        total_pass = 0
        total_fail = 0

        for service, results in all_results.items():
            passed = sum(1 for v in results.values() if v)
            failed = sum(1 for v in results.values() if not v)
            total_pass += passed
            total_fail += failed
            print(f"  {service.upper()}: {passed} passed, {failed} failed")

        print(f"\n  TOTAL: {total_pass} passed, {total_fail} failed")

        return 0 if total_fail == 0 else 1

    finally:
        cb.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    sys.exit(main())
