"""Integration tests for APN configuration.

These tests require a connected Amarisoft Callbox at 192.168.1.80.
Run with: pytest tests/integration/test_apn_config.py -v

WARNING: These tests modify the MME configuration file on the callbox.
Backups are created automatically before any modifications.
"""

from __future__ import annotations

import time

import pytest

from amarisoft import Callbox, SSHClient


pytestmark = pytest.mark.integration


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def callbox():
    """Provide a connected Callbox instance."""
    cb = Callbox("192.168.1.80", ims_port=9003)
    cb.connect_all()
    yield cb
    cb.disconnect_all()


@pytest.fixture(scope="module")
def ssh_client():
    """Provide an SSH client."""
    with SSHClient("192.168.1.80") as ssh:
        yield ssh


@pytest.fixture
def test_apn_name():
    """Generate a unique test APN name."""
    return f"test_apn_{int(time.time())}"


@pytest.fixture
def cleanup_test_apn(ssh_client, test_apn_name):
    """Cleanup fixture to remove test APN after test."""
    yield test_apn_name
    # Restore backup if it exists
    # Note: In a real scenario, you'd want more sophisticated cleanup
    # For now, we rely on the backup mechanism


# ══════════════════════════════════════════════════════════════
# Read-Only Tests (Safe to run anytime)
# ══════════════════════════════════════════════════════════════


class TestGetApnConfig:
    """Test reading APN configuration (read-only, safe)."""

    def test_get_apn_config_returns_list(self, callbox):
        """get_apn_config() should return a list of APNs."""
        apns = callbox.get_apn_config()

        assert isinstance(apns, list)
        assert len(apns) > 0, "Expected at least one APN configured"

    def test_get_apn_config_has_required_fields(self, callbox):
        """Each APN should have standard fields."""
        apns = callbox.get_apn_config()

        for apn in apns:
            # access_point_name is required
            assert "access_point_name" in apn, f"Missing access_point_name in {apn}"

    def test_get_apn_config_contains_default(self, callbox):
        """Should contain a 'default' APN."""
        apns = callbox.get_apn_config()
        apn_names = [a.get("access_point_name") for a in apns]

        assert "default" in apn_names, f"Expected 'default' APN, found: {apn_names}"

    def test_get_apn_config_contains_internet(self, callbox):
        """Should contain an 'internet' APN."""
        apns = callbox.get_apn_config()
        apn_names = [a.get("access_point_name") for a in apns]

        assert "internet" in apn_names, f"Expected 'internet' APN, found: {apn_names}"

    def test_apn_has_ip_range(self, callbox):
        """APNs should have IP address range configured."""
        apns = callbox.get_apn_config()

        # At least one APN should have IP range
        apns_with_ip = [a for a in apns if a.get("first_ip") and a.get("last_ip")]
        assert len(apns_with_ip) > 0, "Expected at least one APN with IP range"

    def test_apn_has_qci(self, callbox):
        """APNs should have QCI configured."""
        apns = callbox.get_apn_config()

        # At least one APN should have QCI
        apns_with_qci = [a for a in apns if a.get("qci") is not None]
        assert len(apns_with_qci) > 0, "Expected at least one APN with QCI"


class TestMmeSetDefaultApn:
    """Test runtime APN configuration via WebSocket (non-persistent)."""

    def test_set_default_apn_returns_response(self, callbox):
        """mme.set_default_apn() should return a response."""
        # This only affects runtime config, not persistent
        result = callbox.mme.set_default_apn(
            apn="default",
            qci=9,
        )

        assert isinstance(result, dict)

    def test_get_apn_sessions_returns_list(self, callbox):
        """mme.get_apn_sessions() should return a list."""
        sessions = callbox.mme.get_apn_sessions()

        assert isinstance(sessions, list)


# ══════════════════════════════════════════════════════════════
# Write Tests (Modifies config - use with caution)
# ══════════════════════════════════════════════════════════════


@pytest.mark.slow
class TestSetDefaultApnPersistent:
    """Test persistent APN configuration via SSH.

    WARNING: These tests modify the MME config file.
    Backups are created automatically.
    """

    def test_set_default_apn_persistent_creates_backup(self, callbox, test_apn_name):
        """Should create a backup before modifying config."""
        result = callbox.set_default_apn_persistent(
            apn=test_apn_name,
            first_ip="192.168.99.2",
            last_ip="192.168.99.254",
            dns="8.8.8.8",
            backup=True,
            restart_mme=False,  # Don't restart for test
        )

        assert result["success"] is True
        assert result["backup_path"] is not None
        assert "backup" in result["backup_path"]

    def test_set_default_apn_persistent_returns_config(self, callbox, test_apn_name):
        """Should return the APN config that was added."""
        result = callbox.set_default_apn_persistent(
            apn=test_apn_name,
            pdn_type="ipv4",
            first_ip="192.168.98.2",
            last_ip="192.168.98.254",
            dns="8.8.8.8",
            qci=9,
            priority_level=15,
            restart_mme=False,
        )

        assert result["success"] is True
        assert result["apn_config"] is not None
        assert result["apn_config"]["apn"] == test_apn_name
        assert result["apn_config"]["pdn_type"] == "ipv4"
        assert result["apn_config"]["first_ip"] == "192.168.98.2"
        assert result["apn_config"]["qci"] == 9

    def test_set_default_apn_persistent_with_dns_list(self, callbox, test_apn_name):
        """Should support DNS as a list."""
        result = callbox.set_default_apn_persistent(
            apn=test_apn_name,
            first_ip="192.168.97.2",
            last_ip="192.168.97.254",
            dns=["8.8.8.8", "8.8.4.4"],
            restart_mme=False,
        )

        assert result["success"] is True
        assert result["apn_config"]["dns"] == ["8.8.8.8", "8.8.4.4"]

    def test_set_default_apn_persistent_ipv4v6(self, callbox, test_apn_name):
        """Should support IPv4v6 PDN type."""
        result = callbox.set_default_apn_persistent(
            apn=test_apn_name,
            pdn_type="ipv4v6",
            first_ip="192.168.96.2",
            last_ip="192.168.96.254",
            restart_mme=False,
        )

        assert result["success"] is True
        assert result["apn_config"]["pdn_type"] == "ipv4v6"

    def test_set_default_apn_persistent_warns_on_duplicate(self, callbox):
        """Should warn when adding duplicate APN name."""
        # 'default' APN should already exist
        result = callbox.set_default_apn_persistent(
            apn="default",
            first_ip="192.168.95.2",
            last_ip="192.168.95.254",
            restart_mme=False,
        )

        assert result["success"] is True
        assert "already exists" in result["message"]

    def test_set_default_apn_persistent_config_path(self, callbox, test_apn_name):
        """Should report the correct config path."""
        result = callbox.set_default_apn_persistent(
            apn=test_apn_name,
            restart_mme=False,
        )

        assert result["config_path"] == "/root/mme/config/mme.cfg"


# ══════════════════════════════════════════════════════════════
# CLI Runner
# ══════════════════════════════════════════════════════════════


if __name__ == "__main__":
    """Run tests from command line.

    Usage:
        # Run read-only tests (safe)
        python -m pytest tests/integration/test_apn_config.py -v -k "TestGetApnConfig or TestMmeSetDefaultApn"

        # Run all tests including write tests
        python -m pytest tests/integration/test_apn_config.py -v

        # Quick sanity check
        python tests/integration/test_apn_config.py
    """
    import sys

    print("=" * 60)
    print("APN CONFIGURATION INTEGRATION TEST")
    print("=" * 60)

    # Quick sanity check
    print("\n1. Testing get_apn_config()...")
    with Callbox("192.168.1.80", ims_port=9003) as cb:
        apns = cb.get_apn_config()
        print(f"   Found {len(apns)} APNs:")
        for apn in apns:
            print(f"   - {apn.get('access_point_name', 'unknown')}")

    print("\n2. Testing mme.get_apn_sessions()...")
    with Callbox("192.168.1.80", ims_port=9003) as cb:
        sessions = cb.mme.get_apn_sessions()
        print(f"   Found {len(sessions)} active sessions")

    print("\n" + "=" * 60)
    print("QUICK CHECK PASSED ✓")
    print("=" * 60)
    print("\nTo run full test suite:")
    print("  pytest tests/integration/test_apn_config.py -v")
