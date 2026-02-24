#!/usr/bin/env python3
"""Basic connection example for the Amarisoft Callbox.

Demonstrates:
- Callbox constructor and connect_all()
- Connection status checking
- Version info from each service
- Context manager usage
- Individual service connections
- Capability discovery and validation
"""

import argparse
from pprint import pprint

from client.websocket import (
    Callbox,
    AmariConnectionError,
    AmariTimeoutError,
    AuthenticationError,
    get_default_capabilities,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Connect to an Amarisoft Callbox")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    return parser.parse_args()


def example_connect_all(host, password, ssl, ssl_verify):
    """Connect to all services at once and print status."""
    print("=" * 60)
    print("Example 1: connect_all()")
    print("=" * 60)

    cb = Callbox(host, password=password, ssl=ssl, ssl_verify=ssl_verify)
    try:
        ready = cb.connect_all()
        print("\nReady messages from each service:")
        pprint(ready)

        print("\nConnection status:")
        pprint(cb.status)

        # Get version from each connected service
        for name, api, connected in [
            ("eNB", cb.enb, cb.status.get("enb")),
            ("MME", cb.mme, cb.status.get("mme")),
            ("IMS", cb.ims, cb.status.get("ims")),
            ("UE", cb.ue, cb.status.get("ue")),
        ]:
            if not connected:
                print(f"\n{name}: Not connected")
                continue
            try:
                version = api.version()
                print(f"\n{name} version:")
                pprint(version)
            except Exception as e:
                print(f"\n{name}: version() not supported ({e})")
    finally:
        cb.close()
        print("\nAll connections closed.")


def example_context_manager(host, password, ssl, ssl_verify):
    """Use the Callbox as a context manager."""
    print("\n" + "=" * 60)
    print("Example 2: Context manager usage")
    print("=" * 60)

    with Callbox(host, password=password, ssl=ssl, ssl_verify=ssl_verify) as cb:
        print("\nConnected via context manager.")
        print("Status:", cb.status)

        # Call help() to list available commands on eNB
        print("\neNB available commands:")
        pprint(cb.enb.help())

    print("Context manager exited — connections closed automatically.")


def example_individual_connections(host, password, ssl, ssl_verify):
    """Connect to services one at a time."""
    print("\n" + "=" * 60)
    print("Example 3: Individual service connections")
    print("=" * 60)

    cb = Callbox(host, password=password, ssl=ssl, ssl_verify=ssl_verify)
    try:
        # Connect only to the eNB
        enb_ready = cb.connect_enb()
        print("\neNB ready message:")
        pprint(enb_ready)

        # Connect only to the MME
        mme_ready = cb.connect_mme()
        print("\nMME ready message:")
        pprint(mme_ready)

        print("\nPartial connection status:")
        pprint(cb.status)
    finally:
        cb.close()


def example_capability_discovery(host, password, ssl, ssl_verify):
    """Discover device capabilities and enable validation."""
    print("\n" + "=" * 60)
    print("Example 4: Capability discovery and validation")
    print("=" * 60)

    with Callbox(host, password=password, ssl=ssl, ssl_verify=ssl_verify) as cb:
        # Discover capabilities from the connected device
        print("\nDiscovering device capabilities...")
        caps = cb.discover_capabilities()

        print(f"\nDevice: {caps.hostname}")
        print(f"Version: {caps.amarisoft_version}")
        print(f"Max Bandwidth: {caps.max_bandwidth_mhz} MHz")
        print(f"Max MIMO: {caps.max_mimo_layers} layers")
        print(f"Supported RATs: {[r.value for r in caps.supported_rats]}")

        # Enable validation to prevent invalid configurations
        print("\nEnabling parameter validation...")
        checker = cb.enable_validation()

        # Example: validate MCS before applying
        print("\nValidating MCS=15 for LTE...")
        from client.websocket import RATType
        try:
            checker.validate_mcs(15, rat=RATType.LTE)
            print("  ✓ MCS=15 is valid")
        except Exception as e:
            print(f"  ✗ Invalid: {e}")

        print(f"\nValidation enabled: {cb.validation_enabled}")


def example_offline_validation():
    """Use default capabilities for offline validation."""
    print("\n" + "=" * 60)
    print("Example 5: Offline validation (no device required)")
    print("=" * 60)

    # Get default capabilities for CBM-2024121101
    caps = get_default_capabilities()

    print(f"\nDefault device: {caps.hostname}")
    print(f"Max Bandwidth: {caps.max_bandwidth_mhz} MHz")

    # Create a checker for validation
    from client.websocket import CapabilityChecker, InvalidParameterError
    checker = CapabilityChecker(caps)

    # Validate RF gain settings
    print("\nValidating RF gains for wired testing:")
    try:
        checker.validate_rf_gain(tx_gain=60, rx_gain=10, mode="wired")
        print("  ✓ tx_gain=60, rx_gain=10 - Valid")
    except InvalidParameterError as e:
        print(f"  ✗ {e}")

    print("\nValidating invalid RF gain:")
    try:
        checker.validate_rf_gain(tx_gain=100, mode="wired")
        print("  ✓ Valid")
    except InvalidParameterError as e:
        print(f"  ✗ Caught: {e}")


def main():
    args = parse_args()

    # Offline validation example runs without device
    example_offline_validation()

    try:
        example_connect_all(args.host, args.password, args.ssl, args.ssl_verify)
        example_context_manager(args.host, args.password, args.ssl, args.ssl_verify)
        example_individual_connections(args.host, args.password, args.ssl, args.ssl_verify)
        example_capability_discovery(args.host, args.password, args.ssl, args.ssl_verify)
    except AuthenticationError as e:
        print(f"\nAuthentication failed: {e}")
        print("Check the --password argument.")
    except AmariConnectionError as e:
        print(f"\nConnection error: {e}")
        print("Verify the Callbox is reachable at the given --host.")
    except AmariTimeoutError as e:
        print(f"\nTimeout: {e}")


if __name__ == "__main__":
    main()
