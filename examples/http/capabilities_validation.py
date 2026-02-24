#!/usr/bin/env python3
"""Capabilities and validation example for the Amarisoft Callbox (HTTP).

Demonstrates:
- Discovering device capabilities from a connected Callbox
- Using ValidationContext for automatic parameter validation
- Manual capability checking before operations
- Custom validation with the CapabilityChecker

This example shows how to ensure your code only sends valid
configurations to the target device, preventing errors from
invalid parameters like unsupported bandwidths, MCS values,
or RF gain settings.
"""

import argparse
from pprint import pprint

from client.http import (
    Callbox,
    APIError,
    ValidationError,
    CapabilityChecker,
    ValidationContext,
    DeviceCapabilities,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Device capabilities and validation examples (HTTP)"
    )
    parser.add_argument("--url", default="http://127.0.0.1:9010", help="REST API URL")
    parser.add_argument("--api-key", default=None, help="API key for authentication")
    parser.add_argument(
        "--offline", action="store_true",
        help="Run offline examples only (no device connection)",
    )
    return parser.parse_args()


def example_offline_capabilities():
    """Work with capabilities without a device connection."""
    print("=" * 60)
    print("Example 1: Offline Capabilities (No Device Required)")
    print("=" * 60)

    # Create default capabilities
    caps = DeviceCapabilities(
        model="CBM-2024121101",
        max_cells=4,
        max_ues=64,
        supported_rats=["lte", "nr"],
        supported_bandwidths=[5, 10, 15, 20, 40, 50, 100],
        max_mimo_layers=4,
    )

    print("\nDevice capabilities summary:")
    print(f"  Model: {caps.model}")
    print(f"  Max cells: {caps.max_cells}")
    print(f"  Max UEs: {caps.max_ues}")
    print(f"  Supported RATs: {caps.supported_rats}")
    print(f"  Supported BWs: {caps.supported_bandwidths} MHz")
    print(f"  Max MIMO: {caps.max_mimo_layers}x{caps.max_mimo_layers}")

    # Create a checker for validation
    checker = CapabilityChecker(caps)

    # Validate parameters before use
    print("\n--- Validation Examples ---")

    # Valid parameters
    print("\nChecking valid parameters:")
    try:
        checker.validate_bandwidth(100)
        print("  ✓ bandwidth=100MHz - Valid")
    except ValidationError as e:
        print(f"  ✗ {e}")

    try:
        checker.validate_mimo_layers(4)
        print("  ✓ mimo=4x4 - Valid")
    except ValidationError as e:
        print(f"  ✗ {e}")

    try:
        checker.validate_mcs(15)
        print("  ✓ MCS=15 - Valid")
    except ValidationError as e:
        print(f"  ✗ {e}")

    # Invalid parameters - will be caught
    print("\nChecking invalid parameters (should fail):")

    try:
        checker.validate_bandwidth(500)
        print("  ✗ Should have failed!")
    except ValidationError as e:
        print(f"  ✓ Caught: {e}")

    try:
        checker.validate_mimo_layers(8)
        print("  ✗ Should have failed!")
    except ValidationError as e:
        print(f"  ✓ Caught: {e}")

    try:
        checker.validate_mcs(35)
        print("  ✗ Should have failed!")
    except ValidationError as e:
        print(f"  ✓ Caught: {e}")


def example_discover_capabilities(cb):
    """Discover capabilities from a connected Callbox."""
    print("\n" + "=" * 60)
    print("Example 2: Discover Capabilities from Device")
    print("=" * 60)

    # Discover capabilities from the connected device
    caps = DeviceCapabilities.from_callbox(cb)

    print("\nDiscovered capabilities:")
    print(f"  Model: {caps.model}")
    print(f"  Max cells: {caps.max_cells}")
    print(f"  Max UEs: {caps.max_ues}")

    return caps


def example_validation_context(cb):
    """Use ValidationContext for automatic validation."""
    print("\n" + "=" * 60)
    print("Example 3: ValidationContext for Automatic Validation")
    print("=" * 60)

    print("\nUsing ValidationContext for scoped validation:")

    with ValidationContext(cb) as ctx:
        print(f"  Validation context active")

        # The checker is available for manual checks
        checker = ctx.checker

        # Validate before making API calls
        print("\n  Pre-validating parameters...")
        try:
            checker.validate_bandwidth(20)
            print("  ✓ Bandwidth validated")

            # Now safe to make the call
            print("  (Would configure cell with 20 MHz bandwidth here)")
        except ValidationError as e:
            print(f"  ✗ Invalid: {e}")

    print(f"\nOutside context - validation complete")


def example_safe_rf_configuration(cb):
    """Demonstrate safe RF configuration with validation."""
    print("\n" + "=" * 60)
    print("Example 4: Safe RF Configuration")
    print("=" * 60)

    # This example shows how to safely configure RF parameters
    # by validating them before sending to the device

    with ValidationContext(cb) as ctx:
        # Define test configurations
        test_configs = [
            {"tx_gain": 60, "rx_gain": 10, "desc": "Normal test"},
            {"tx_gain": 80, "rx_gain": 30, "desc": "Higher gain"},
            {"tx_gain": 150, "rx_gain": 10, "desc": "Invalid - too high"},
        ]

        for config in test_configs:
            print(f"\n  Testing: {config['desc']}")
            print(f"    tx_gain={config['tx_gain']}, rx_gain={config['rx_gain']}")

            try:
                ctx.checker.validate_rf_gain(
                    tx_gain=config["tx_gain"],
                    rx_gain=config["rx_gain"],
                )
                print(f"    ✓ Valid - safe to apply")
                # Would apply: cb.enb.rf(tx_gain=config["tx_gain"], rx_gain=config["rx_gain"])
            except ValidationError as e:
                print(f"    ✗ Rejected: {e}")


def main():
    args = parse_args()

    # Always run offline example first
    example_offline_capabilities()

    if args.offline:
        print("\n" + "=" * 60)
        print("Offline mode - skipping device examples")
        print("=" * 60)
        return

    # Online examples require device connection
    try:
        with Callbox(args.url, api_key=args.api_key) as cb:
            example_discover_capabilities(cb)
            example_validation_context(cb)
            example_safe_rf_configuration(cb)

    except APIError as e:
        print(f"\nError: {e}")
        print("Run with --offline to see offline examples only.")


if __name__ == "__main__":
    main()
