"""Integration tests for IMS service (read-only operations)."""

import pytest


pytestmark = pytest.mark.integration


class TestIMSUsers:
    """Tests for IMS user queries."""

    def test_users_get_returns_dict(self, callbox):
        result = callbox.ims.users_get()
        assert isinstance(result, dict)

    def test_users_get_registered_only(self, callbox):
        result = callbox.ims.users_get(registered_only=True)
        assert isinstance(result, dict)


class TestIMSLicense:
    """Tests for IMS license information."""

    def test_license_returns_dict(self, callbox):
        result = callbox.ims.license()
        assert isinstance(result, dict)


class TestIMSIPsec:
    """Tests for IPsec SA queries."""

    def test_ipsec_returns_dict(self, callbox):
        result = callbox.ims.ipsec()
        assert isinstance(result, dict)


class TestIMSDialog:
    """Tests for dialog queries."""

    def test_dialog_get_returns_dict(self, callbox):
        result = callbox.ims.dialog_get()
        assert isinstance(result, dict)
