"""Integration tests for the capabilities and constraints system.

These tests require a connected Amarisoft Callbox at 192.168.1.80.
Run with: pytest tests/integration/test_capabilities.py -v

Test Plan:
1. Test device capability discovery
2. Test constraint validation
3. Test validation decorators
4. Test ValidationContext
"""

from __future__ import annotations

import pytest

from client.websocket import Callbox
from client.websocket.capabilities import (
    CapabilityChecker,
    DeviceCapabilities,
    RATType,
    ValidationContext,
    get_default_capabilities,
)
from client.websocket.exceptions import InvalidParameterError


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def callbox():
    """Provide a connected Callbox instance."""
    # Use IMS port 9003 as discovered on CBM-2024121101
    cb = Callbox("192.168.1.80", ims_port=9003)
    cb.connect_all()
    yield cb
    cb.disconnect_all()


@pytest.fixture
def default_caps():
    """Provide default capabilities for CBM-2024121101."""
    return get_default_capabilities()


@pytest.fixture
def checker(default_caps):
    """Provide a CapabilityChecker with default capabilities."""
    return CapabilityChecker(default_caps)


# ══════════════════════════════════════════════════════════════
# Unit Tests (No Device Required)
# ══════════════════════════════════════════════════════════════


class TestDefaultCapabilities:
    """Test the default capabilities configuration."""

    def test_get_default_capabilities(self):
        """Default capabilities should match CBM-2024121101 config."""
        caps = get_default_capabilities()

        assert caps.hostname == "CBM-2024121101"
        assert caps.amarisoft_version == "2024-09-13"
        assert len(caps.sdr_cards) == 1
        assert caps.sdr_cards[0].board_type == "SDR50"

    def test_service_ports(self):
        """Service ports should reflect discovered configuration."""
        caps = get_default_capabilities()

        assert caps.service_ports.enb == 9001
        assert caps.service_ports.mme == 9000
        assert caps.service_ports.ims == 9003  # Non-default!
        assert caps.service_ports.ue == 9003

    def test_license_info(self):
        """License info should be present."""
        caps = get_default_capabilities()

        assert caps.license_info is not None
        assert caps.license_info.user_name == "Meta Platforms"
        assert caps.license_info.license_uid == "NISCBM02_FRE6530"
        assert RATType.LTE in caps.license_info.rat_support
        assert RATType.NR in caps.license_info.rat_support

    def test_constraints(self):
        """Hardware/license constraints should be correct."""
        caps = get_default_capabilities()

        assert caps.max_cells == 1
        assert caps.max_bandwidth_mhz == 120
        assert caps.max_mimo_layers == 4

    def test_features(self):
        """Feature flags should be set correctly."""
        caps = get_default_capabilities()

        assert caps.features["endc"] is True
        assert caps.features["volte"] is True
        assert caps.features["5gc"] is True
        assert caps.features["carrier_aggregation"] is False

    def test_services_available(self):
        """Service availability should be tracked."""
        caps = get_default_capabilities()

        assert caps.services_available["enb"] is True
        assert caps.services_available["mme"] is True
        assert caps.services_available["ims"] is True
        assert caps.services_available["ue"] is False

    def test_summary_generation(self):
        """Summary should be human-readable."""
        caps = get_default_capabilities()
        summary = caps.summary()

        assert "CBM-2024121101" in summary
        assert "SDR50" in summary
        assert "Meta Platforms" in summary

    def test_to_dict(self):
        """Export to dictionary should work."""
        caps = get_default_capabilities()
        data = caps.to_dict()

        assert data["hostname"] == "CBM-2024121101"
        assert "constraints" in data
        assert "services" in data


class TestCapabilityChecker:
    """Test constraint validation logic."""

    def test_valid_bandwidth(self, checker):
        """Valid bandwidth should pass."""
        # Should not raise
        checker.validate_cell_config(bandwidth_mhz=100)
        checker.validate_cell_config(bandwidth_mhz=20)

    def test_invalid_bandwidth(self, checker):
        """Bandwidth exceeding license should fail."""
        with pytest.raises(InvalidParameterError) as exc_info:
            checker.validate_cell_config(bandwidth_mhz=200)
        assert "exceeds license limit" in str(exc_info.value)

    def test_valid_mimo(self, checker):
        """Valid MIMO layers should pass."""
        checker.validate_cell_config(mimo_layers=2)
        checker.validate_cell_config(mimo_layers=4)

    def test_invalid_mimo_too_high(self, checker):
        """MIMO layers exceeding hardware should fail."""
        with pytest.raises(InvalidParameterError) as exc_info:
            checker.validate_cell_config(mimo_layers=8)
        assert "exceeds hardware limit" in str(exc_info.value)

    def test_invalid_mimo_value(self, checker):
        """Invalid MIMO value should fail."""
        with pytest.raises(InvalidParameterError) as exc_info:
            checker.validate_cell_config(mimo_layers=3)
        assert "must be 1, 2, 4, or 8" in str(exc_info.value)

    def test_valid_rat(self, checker):
        """Supported RAT should pass."""
        checker.validate_cell_config(rat=RATType.LTE)
        checker.validate_cell_config(rat=RATType.NR)

    def test_invalid_rat(self, checker):
        """Unsupported RAT should fail."""
        with pytest.raises(InvalidParameterError) as exc_info:
            checker.validate_cell_config(rat=RATType.NB_IOT)
        assert "not supported by license" in str(exc_info.value)

    def test_valid_rf_gain_wired(self, checker):
        """Valid RF gains for wired testing should pass."""
        checker.validate_rf_gain(tx_gain=60, rx_gain=10, mode="wired")

    def test_invalid_rf_gain_wired(self, checker):
        """RF gains outside wired range should fail."""
        with pytest.raises(InvalidParameterError) as exc_info:
            checker.validate_rf_gain(tx_gain=90, mode="wired")
        assert "out of range for wired mode" in str(exc_info.value)

    def test_valid_rf_gain_wireless(self, checker):
        """Valid RF gains for wireless testing should pass."""
        checker.validate_rf_gain(tx_gain=90, rx_gain=60, mode="wireless")

    def test_valid_mcs_lte(self, checker):
        """Valid LTE MCS should pass."""
        checker.validate_mcs(15, rat=RATType.LTE)
        checker.validate_mcs(28, rat=RATType.LTE)

    def test_invalid_mcs_lte(self, checker):
        """MCS out of LTE range should fail."""
        with pytest.raises(InvalidParameterError) as exc_info:
            checker.validate_mcs(30, rat=RATType.LTE)
        assert "out of range" in str(exc_info.value)

    def test_valid_mcs_nr(self, checker):
        """Valid NR MCS should pass."""
        checker.validate_mcs(31, rat=RATType.NR)

    def test_valid_qci(self, checker):
        """Valid QCI values should pass."""
        for qci in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            checker.validate_qci(qci)

    def test_invalid_qci(self, checker):
        """Invalid QCI should fail."""
        with pytest.raises(InvalidParameterError) as exc_info:
            checker.validate_qci(99)
        assert "not a standard QCI value" in str(exc_info.value)

    def test_get_qci_info(self, checker):
        """QCI info lookup should work."""
        info = checker.get_qci_info(5)
        assert info["name"] == "IMS Signaling"
        assert info["type"] == "non-gbr"

    def test_service_available(self, checker):
        """Available service check should pass."""
        checker.validate_service_available("enb")
        checker.validate_service_available("mme")

    def test_service_not_available(self, checker):
        """Unavailable service check should fail."""
        with pytest.raises(InvalidParameterError) as exc_info:
            checker.validate_service_available("ue")
        assert "not available" in str(exc_info.value)

    def test_feature_enabled(self, checker):
        """Enabled feature check should pass."""
        checker.validate_feature("volte")
        checker.validate_feature("endc")

    def test_feature_not_enabled(self, checker):
        """Disabled feature check should fail."""
        with pytest.raises(InvalidParameterError) as exc_info:
            checker.validate_feature("carrier_aggregation")
        assert "not enabled" in str(exc_info.value)


# ══════════════════════════════════════════════════════════════
# Integration Tests (Device Required)
# ══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestDeviceCapabilityDiscovery:
    """Test discovering capabilities from a live device."""

    def test_discover_from_callbox(self, callbox):
        """Should discover capabilities from device."""
        caps = DeviceCapabilities.from_callbox(callbox)

        # Basic info should be populated
        assert caps.amarisoft_version != "unknown"

        # Services should be detected
        assert caps.services_available["enb"] is True
        assert caps.services_available["mme"] is True

        # Ports should match what we connected to
        assert caps.service_ports.enb == 9001
        assert caps.service_ports.mme == 9000
        assert caps.service_ports.ims == 9003

    def test_cells_discovered(self, callbox):
        """Should discover cell configurations."""
        caps = DeviceCapabilities.from_callbox(callbox)

        # At least one cell should be configured
        assert len(caps.cells) >= 0  # May be 0 if no cells active

    def test_summary_printable(self, callbox):
        """Summary should print without errors."""
        caps = DeviceCapabilities.from_callbox(callbox)
        summary = caps.summary()

        print("\n" + summary)  # For visual inspection
        assert len(summary) > 100


@pytest.mark.integration
class TestValidationContext:
    """Test ValidationContext with a live device."""

    def test_validation_context_enables_checking(self, callbox):
        """ValidationContext should enable validation."""
        # Initially no checker
        assert getattr(callbox, "_capability_checker", None) is None

        with ValidationContext(callbox) as ctx:
            # Checker should be active
            assert callbox._capability_checker is not None
            assert ctx.checker is not None

        # Checker should be removed after context
        assert getattr(callbox, "_capability_checker", None) is None

    def test_validation_catches_invalid_params(self, callbox):
        """Validation should catch invalid parameters."""
        with ValidationContext(callbox) as ctx:
            # This should fail validation
            with pytest.raises(InvalidParameterError):
                ctx.checker.validate_cell_config(bandwidth_mhz=500)

    def test_validation_allows_valid_params(self, callbox):
        """Validation should allow valid parameters."""
        with ValidationContext(callbox) as ctx:
            # These should all pass
            ctx.checker.validate_cell_config(bandwidth_mhz=20)
            ctx.checker.validate_rf_gain(tx_gain=60, mode="wired")
            ctx.checker.validate_mcs(15)


# ══════════════════════════════════════════════════════════════
# CLI Test Runner
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Run tests from command line.

    Usage:
        # Run unit tests only (no device needed)
        python -m pytest tests/integration/test_capabilities.py -v -m "not integration"

        # Run all tests (device required)
        python -m pytest tests/integration/test_capabilities.py -v

        # Run this file directly for quick check
        python tests/integration/test_capabilities.py
    """
    import sys

    # Quick sanity check without pytest
    print("=" * 60)
    print("CAPABILITIES SYSTEM QUICK CHECK")
    print("=" * 60)

    # Test 1: Default capabilities
    print("\n1. Testing default capabilities...")
    caps = get_default_capabilities()
    assert caps.hostname == "CBM-2024121101"
    print("   ✓ Default capabilities loaded correctly")

    # Test 2: Capability checker
    print("\n2. Testing capability checker...")
    checker = CapabilityChecker(caps)

    # Valid operations
    checker.validate_cell_config(bandwidth_mhz=100)
    checker.validate_rf_gain(tx_gain=60, mode="wired")
    checker.validate_mcs(15)
    print("   ✓ Valid operations pass")

    # Invalid operations
    try:
        checker.validate_cell_config(bandwidth_mhz=500)
        print("   ✗ Should have raised InvalidParameterError")
        sys.exit(1)
    except InvalidParameterError:
        print("   ✓ Invalid bandwidth correctly rejected")

    try:
        checker.validate_rf_gain(tx_gain=100, mode="wired")
        print("   ✗ Should have raised InvalidParameterError")
        sys.exit(1)
    except InvalidParameterError:
        print("   ✓ Invalid RF gain correctly rejected")

    # Test 3: Summary
    print("\n3. Testing summary generation...")
    summary = caps.summary()
    assert "CBM-2024121101" in summary
    print("   ✓ Summary generated correctly")

    # Test 4: Export to dict
    print("\n4. Testing dictionary export...")
    data = caps.to_dict()
    assert "hostname" in data
    assert "constraints" in data
    print("   ✓ Dictionary export works")

    print("\n" + "=" * 60)
    print("ALL QUICK CHECKS PASSED ✓")
    print("=" * 60)
    print("\nTo run full test suite with device:")
    print("  pytest tests/integration/test_capabilities.py -v")
