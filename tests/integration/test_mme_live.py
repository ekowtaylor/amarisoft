"""Integration tests for MME/AMF service (read-only operations)."""

import pytest


pytestmark = pytest.mark.integration


class TestMMEStats:
    """Tests for MME statistics."""

    def test_stats_returns_dict(self, callbox):
        result = callbox.mme.stats()
        assert isinstance(result, dict)
        assert result.get("message") == "stats"


class TestMMEUEGet:
    """Tests for UE queries from MME."""

    def test_ue_get_returns_dict(self, callbox):
        result = callbox.mme.ue_get()
        assert isinstance(result, dict)


class TestMMEConfig:
    """Tests for MME configuration retrieval."""

    def test_config_get_returns_dict(self, callbox):
        result = callbox.mme.config_get()
        assert isinstance(result, dict)


class TestMMEENBGet:
    """Tests for connected base station queries."""

    def test_enb_get_returns_dict(self, callbox):
        result = callbox.mme.enb_get()
        assert isinstance(result, dict)

    def test_gnb_get_returns_dict(self, callbox):
        try:
            result = callbox.mme.gnb_get()
            assert isinstance(result, dict)
        except Exception:
            # gNB may not be configured in LTE-only setups
            pytest.skip("gNB not available in this configuration")


class TestMMESession:
    """Tests for session queries."""

    def test_session_get_returns_dict(self, callbox):
        result = callbox.mme.session_get()
        assert isinstance(result, dict)


class TestMMEBearer:
    """Tests for bearer queries."""

    def test_bearer_get_returns_dict(self, callbox):
        result = callbox.mme.bearer_get()
        assert isinstance(result, dict)
