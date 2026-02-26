#!/usr/bin/env python3
"""Test all WebSocket methods against the live Amarisoft callbox."""

import json
import sys
from typing import Any

# Add the project to path
sys.path.insert(0, "/Users/ekowtaylor/Documents/Personal/Github/amarisoft")

from client.websocket import AmariError, Callbox, CommandError


def test_method(name: str, func, *args, **kwargs) -> tuple[bool, Any]:
    """Test a single method and return success/failure with result."""
    try:
        result = func(*args, **kwargs)
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
        if verbose:
            print(f"  {status} {name}: {json.dumps(result, default=str)[:100]}...")
        else:
            print(f"  {status} {name}")
    else:
        print(f"  {status} {name}: {result}")


def test_enb_methods(cb: Callbox, verbose: bool = False) -> dict[str, bool]:
    """Test all ENB methods."""
    print("\n" + "=" * 60)
    print("TESTING ENB METHODS")
    print("=" * 60)

    results = {}

    # Base methods (inherited)
    tests = [
        ("help", lambda: cb.enb.help()),
        ("config_get", lambda: cb.enb.config_get()),
        ("stats", lambda: cb.enb.stats()),
        ("stats(rf=True)", lambda: cb.enb.stats(rf=True)),
        ("stats(samples=True)", lambda: cb.enb.stats(samples=True)),
        ("ue_get", lambda: cb.enb.ue_get()),
        ("log_get", lambda: cb.enb.log_get()),
        ("erab_get", lambda: cb.enb.erab_get()),
        ("qos_flow_get", lambda: cb.enb.qos_flow_get()),
        ("rf", lambda: cb.enb.rf()),
        ("s1_status", lambda: cb.enb.s1_status()),
        ("ng_status", lambda: cb.enb.ng_status()),
        ("x2_status", lambda: cb.enb.x2_status()),
        ("xn_status", lambda: cb.enb.xn_status()),
        ("m2_status", lambda: cb.enb.m2_status()),
        ("echo", lambda: cb.enb.echo({"test": "data"})),
    ]

    for name, func in tests:
        success, result = test_method(name, func)
        results[name] = success
        print_result(name, success, result, verbose)

    return results


def test_mme_methods(cb: Callbox, verbose: bool = False) -> dict[str, bool]:
    """Test all MME methods."""
    print("\n" + "=" * 60)
    print("TESTING MME METHODS")
    print("=" * 60)

    results = {}

    tests = [
        ("help", lambda: cb.mme.help()),
        ("config_get", lambda: cb.mme.config_get()),
        ("stats", lambda: cb.mme.stats()),
        ("ue_get", lambda: cb.mme.ue_get()),
        ("log_get", lambda: cb.mme.log_get()),
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
    """Test IMS methods (if available)."""
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
    """Test UE simulator methods (if available)."""
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
    # Amarisoft box connection details
    # Try direct connection first - IPv6 needs square brackets
    hosts = [
        ("[2620:10d:c052:12a:aaa1:59ff:fe88:d39]", "IPv6 direct"),
        ("192.168.1.80", "IPv4 default"),
        ("127.0.0.1", "localhost"),
    ]

    cb = None
    connected_host = None

    for host, desc in hosts:
        print(f"\nTrying to connect to {desc} ({host})...")
        try:
            cb = Callbox(host, password="toor")
            cb.connect_all()
            connected_host = host
            print(f"✓ Connected to {desc}")
            break
        except Exception as e:
            print(f"✗ Failed: {e}")
            if cb:
                try:
                    cb.close()
                except:
                    pass
                cb = None

    if not cb:
        print("\n✗ Could not connect to any Amarisoft host")
        return 1

    try:
        print("\n" + "=" * 60)
        print("CONNECTION STATUS")
        print("=" * 60)
        print(f"  Host: {connected_host}")
        print(f"  ENB: {'✓' if cb.status.get('enb') else '✗'}")
        print(f"  MME: {'✓' if cb.status.get('mme') else '✗'}")
        print(f"  IMS: {'✓' if cb.status.get('ims') else '✗'}")
        print(f"  UE:  {'✓' if cb.status.get('ue') else '✗'}")

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


if __name__ == "__main__":
    sys.exit(main())
