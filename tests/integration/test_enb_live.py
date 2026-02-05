"""Integration tests for eNB/gNB service (read-only operations)."""

import pytest


pytestmark = pytest.mark.integration


class TestENBStats:
    """Tests for eNB statistics retrieval."""

    def test_stats_returns_dict(self, callbox):
        result = callbox.enb.stats()
        assert isinstance(result, dict)
        assert result.get("message") == "stats"

    def test_stats_with_samples(self, callbox):
        result = callbox.enb.stats(samples=True)
        assert isinstance(result, dict)
        assert result.get("message") == "stats"

    def test_stats_with_rf(self, callbox):
        result = callbox.enb.stats(rf=True)
        assert isinstance(result, dict)
        assert result.get("message") == "stats"


class TestENBSystemInfo:
    """Tests for eNB system information."""

    def test_system_info_returns_dict(self, callbox):
        result = callbox.enb.system_info()
        assert isinstance(result, dict)


class TestENBCellList:
    """Tests for cell listing."""

    def test_cell_list_returns_dict(self, callbox):
        result = callbox.enb.cell_list()
        assert isinstance(result, dict)


class TestENBUEGet:
    """Tests for UE queries from eNB."""

    def test_ue_get_returns_dict(self, callbox):
        result = callbox.enb.ue_get()
        assert isinstance(result, dict)
        # Should contain a UE list (possibly empty)
        assert "ue_list" in result or "message" in result


class TestENBConfig:
    """Tests for eNB configuration retrieval."""

    def test_config_get_returns_dict(self, callbox):
        result = callbox.enb.config_get()
        assert isinstance(result, dict)


class TestENBInterfaceStatus:
    """Tests for S1/NG interface status queries."""

    def test_s1_status(self, callbox):
        try:
            result = callbox.enb.s1_status()
            assert isinstance(result, dict)
        except Exception:
            # S1 may not be configured in all setups
            pytest.skip("S1 interface not available")

    def test_ng_status(self, callbox):
        try:
            result = callbox.enb.ng_status()
            assert isinstance(result, dict)
        except Exception:
            # NG may not be configured in all setups
            pytest.skip("NG interface not available")


class TestENBERAB:
    """Tests for E-RAB queries."""

    def test_erab_get_returns_dict(self, callbox):
        result = callbox.enb.erab_get()
        assert isinstance(result, dict)
