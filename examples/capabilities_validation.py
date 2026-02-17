#!/usr/bin/env python3
"""Capabilities and validation example for the Amarisoft Callbox.

Demonstrates:
- Discovering device capabilities from a connected Callbox
- Using ValidationContext for automatic parameter validation
- Using enable_validation() for persistent validation
- Manual capability checking before operations
- Using get_default_capabilities() for offline work
- Custom validation with decorators

This example shows how to ensure your code only sends valid
configurations to the target device, preventing errors from
invalid parameters like unsupported bandwidths, MCS values,
or RF gain settings.
"""

import argparse
from pprint import pprint

from amarisoft import (
    Callbox,
    AmariError,
    InvalidParameterError,
    # Capabilities
    CapabilityChecker,
    ValidationContext,
    RATType,
    get_default_capabilities,
    # Validation decorators
    validate_rf_params,
    validate_mcs_param,
    validate_qci_param,
    require_service,
    require_feature,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Device capabilities and validation examples"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    parser.add_argument(
        "--ims-port", type=int, default=9002,
        help="IMS port (use 9003 for CBM-2024121101)",
    )
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

    # Get default capabilities for CBM-2024121101
    caps = get_default_capabilities()

    print("\nDevice capabilities summary:")
    print(caps.summary())

    # Create a checker for validation
    checker = CapabilityChecker(caps)

    # Validate parameters before use
    print("\n--- Validation Examples ---")

    # Valid parameters
    print("\nChecking valid parameters:")
    try:
        checker.validate_cell_config(bandwidth_mhz=100, mimo_layers=4)
        print("  ✓ bandwidth=100MHz, mimo=4x4 - Valid")
    except InvalidParameterError as e:
        print(f"  ✗ {e}")

    try:
        checker.validate_rf_gain(tx_gain=60, rx_gain=10, mode="wired")
        print("  ✓ tx_gain=60, rx_gain=10 (wired) - Valid")
    except InvalidParameterError as e:
        print(f"  ✗ {e}")

    try:
        checker.validate_mcs(15, rat=RATType.LTE)
        print("  ✓ MCS=15 (LTE) - Valid")
    except InvalidParameterError as e:
        print(f"  ✗ {e}")

    # Invalid parameters - will be caught
    print("\nChecking invalid parameters (should fail):")

    try:
        checker.validate_cell_config(bandwidth_mhz=500)
        print("  ✗ Should have failed!")
    except InvalidParameterError as e:
        print(f"  ✓ Caught: {e}")

    try:
        checker.validate_rf_gain(tx_gain=100, mode="wired")
        print("  ✗ Should have failed!")
    except InvalidParameterError as e:
        print(f"  ✓ Caught: {e}")

    try:
        checker.validate_mcs(35, rat=RATType.LTE)
        print("  ✗ Should have failed!")
    except InvalidParameterError as e:
        print(f"  ✓ Caught: {e}")

    # Export capabilities as dict
    print("\nCapabilities as dictionary:")
    pprint(caps.to_dict())


def example_discover_capabilities(cb):
    """Discover capabilities from a connected Callbox."""
    print("\n" + "=" * 60)
    print("Example 2: Discover Capabilities from Device")
    print("=" * 60)

    # Discover capabilities from the connected device
    caps = cb.discover_capabilities()

    print("\nDiscovered capabilities:")
    print(caps.summary())

    # Capabilities are now cached on the Callbox
    print(f"\nCached on Callbox: {cb.capabilities is not None}")

    return caps


def example_validation_context(cb):
    """Use ValidationContext for automatic validation."""
    print("\n" + "=" * 60)
    print("Example 3: ValidationContext for Automatic Validation")
    print("=" * 60)

    print("\nUsing ValidationContext for scoped validation:")

    with ValidationContext(cb) as ctx:
        print(f"  Validation enabled: {cb.validation_enabled}")

        # The checker is available for manual checks
        checker = ctx.checker

        # Validate before making API calls
        print("\n  Pre-validating RF parameters...")
        try:
            checker.validate_rf_gain(tx_gain=60, mode="wired")
            print("  ✓ RF gain validated")

            # Now safe to make the call
            # rf_result = cb.enb.rf(tx_gain=60)
            print("  (Would call cb.enb.rf(tx_gain=60) here)")
        except InvalidParameterError as e:
            print(f"  ✗ Invalid: {e}")

        # Check service availability before IMS operations
        print("\n  Checking IMS availability...")
        try:
            checker.validate_service_available("ims")
            checker.validate_feature("volte")
            print("  ✓ IMS and VoLTE available")
        except InvalidParameterError as e:
            print(f"  ⚠ {e}")

    print(f"\nOutside context - validation enabled: {cb.validation_enabled}")


def example_enable_validation(cb):
    """Use enable_validation() for persistent validation."""
    print("\n" + "=" * 60)
    print("Example 4: Persistent Validation with enable_validation()")
    print("=" * 60)

    # Enable validation - automatically discovers capabilities
    checker = cb.enable_validation()
    print(f"Validation enabled: {cb.validation_enabled}")

    # Validate an MCS value
    print("\nValidating MCS values:")
    for mcs in [0, 15, 28, 30]:
        try:
            checker.validate_mcs(mcs, rat=RATType.LTE)
            print(f"  MCS {mcs}: ✓ Valid")
        except InvalidParameterError as e:
            print(f"  MCS {mcs}: ✗ {e}")

    # Validate QCI values
    print("\nValidating QCI values:")
    for qci in [1, 5, 9, 99]:
        try:
            checker.validate_qci(qci)
            info = checker.get_qci_info(qci)
            print(f"  QCI {qci}: ✓ {info.get('name', 'Valid')}")
        except InvalidParameterError as e:
            print(f"  QCI {qci}: ✗ {e}")

    # Disable validation when done
    cb.disable_validation()
    print(f"\nValidation disabled: {not cb.validation_enabled}")


def example_safe_rf_configuration(cb):
    """Demonstrate safe RF configuration with validation."""
    print("\n" + "=" * 60)
    print("Example 5: Safe RF Configuration")
    print("=" * 60)

    # This example shows how to safely configure RF parameters
    # by validating them before sending to the device

    with ValidationContext(cb) as ctx:
        # Define test configurations
        test_configs = [
            {"tx_gain": 60, "rx_gain": 10, "mode": "wired", "desc": "Wired test"},
            {"tx_gain": 90, "rx_gain": 60, "mode": "wireless", "desc": "Wireless test"},
            {"tx_gain": 100, "rx_gain": 10, "mode": "wired", "desc": "Invalid wired"},
        ]

        for config in test_configs:
            print(f"\n  Testing: {config['desc']}")
            print(f"    tx_gain={config['tx_gain']}, rx_gain={config['rx_gain']}")

            try:
                ctx.checker.validate_rf_gain(
                    tx_gain=config["tx_gain"],
                    rx_gain=config["rx_gain"],
                    mode=config["mode"],
                )
                print(f"    ✓ Valid - safe to apply")
                # Would apply: cb.enb.rf(tx_gain=config["tx_gain"], rx_gain=config["rx_gain"])
            except InvalidParameterError as e:
                print(f"    ✗ Rejected: {e}")


class SafeCallboxController:
    """Example controller class using validation decorators."""

    def __init__(self, callbox):
        self._callbox = callbox
        # Enable validation on the callbox
        self._callbox.enable_validation()

    @validate_rf_params(mode="wired")
    def configure_rf_wired(self, tx_gain=None, rx_gain=None):
        """Configure RF for wired testing (gains validated)."""
        print(f"    Configuring RF: tx_gain={tx_gain}, rx_gain={rx_gain}")
        # In real usage: return self._callbox.enb.rf(tx_gain=tx_gain, rx_gain=rx_gain)
        return {"status": "ok", "tx_gain": tx_gain, "rx_gain": rx_gain}

    @validate_mcs_param(mcs_param="pdsch_mcs", rat=RATType.LTE)
    def set_dl_mcs(self, cell_id, pdsch_mcs=None):
        """Set downlink MCS (validated for LTE range)."""
        print(f"    Setting DL MCS={pdsch_mcs} on cell {cell_id}")
        # In real usage: return self._callbox.enb.set_dl_config(cell_id, pdsch_mcs=pdsch_mcs)
        return {"status": "ok", "pdsch_mcs": pdsch_mcs}

    @validate_qci_param()
    def activate_bearer(self, enb_ue_id, qci=5):
        """Activate a bearer with validated QCI."""
        print(f"    Activating bearer: enb_ue_id={enb_ue_id}, qci={qci}")
        # In real usage: return self._callbox.enb.ue_activate_dedicated_bearer(enb_ue_id=enb_ue_id, qci=qci)
        return {"status": "ok", "qci": qci}

    @require_service("ims")
    @require_feature("volte")
    def make_volte_call(self, impu):
        """Make a VoLTE call (requires IMS service and VoLTE feature)."""
        print(f"    Making VoLTE call to {impu}")
        # In real usage: return self._callbox.ims.mt_call(impu)
        return {"status": "ok", "impu": impu}


def example_decorator_validation(cb):
    """Demonstrate validation decorators on a controller class."""
    print("\n" + "=" * 60)
    print("Example 6: Validation Decorators")
    print("=" * 60)

    # Create controller with validation enabled
    controller = SafeCallboxController(cb)

    # Test RF configuration
    print("\n  Testing RF configuration:")
    try:
        result = controller.configure_rf_wired(tx_gain=60, rx_gain=10)
        print(f"    ✓ Success: {result}")
    except InvalidParameterError as e:
        print(f"    ✗ Rejected: {e}")

    try:
        result = controller.configure_rf_wired(tx_gain=95, rx_gain=10)
        print(f"    ✓ Success: {result}")
    except InvalidParameterError as e:
        print(f"    ✗ Rejected: {e}")

    # Test MCS setting
    print("\n  Testing MCS setting:")
    try:
        result = controller.set_dl_mcs(cell_id=1, pdsch_mcs=15)
        print(f"    ✓ Success: {result}")
    except InvalidParameterError as e:
        print(f"    ✗ Rejected: {e}")

    try:
        result = controller.set_dl_mcs(cell_id=1, pdsch_mcs=35)
        print(f"    ✓ Success: {result}")
    except InvalidParameterError as e:
        print(f"    ✗ Rejected: {e}")

    # Test QCI validation
    print("\n  Testing QCI validation:")
    try:
        result = controller.activate_bearer(enb_ue_id=1, qci=5)
        print(f"    ✓ Success: {result}")
    except InvalidParameterError as e:
        print(f"    ✗ Rejected: {e}")

    try:
        result = controller.activate_bearer(enb_ue_id=1, qci=99)
        print(f"    ✓ Success: {result}")
    except InvalidParameterError as e:
        print(f"    ✗ Rejected: {e}")

    # Test feature requirement
    print("\n  Testing VoLTE feature requirement:")
    try:
        result = controller.make_volte_call(impu="sip:user@ims.local")
        print(f"    ✓ Success: {result}")
    except InvalidParameterError as e:
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
        with Callbox(
            args.host,
            password=args.password,
            ssl=args.ssl,
            ssl_verify=args.ssl_verify,
            ims_port=args.ims_port,
        ) as cb:
            example_discover_capabilities(cb)
            example_validation_context(cb)
            example_enable_validation(cb)
            example_safe_rf_configuration(cb)
            example_decorator_validation(cb)

    except AmariError as e:
        print(f"\nError: {e}")
        print("Run with --offline to see offline examples only.")


if __name__ == "__main__":
    main()
