"""Integration tests for UE Simulator service (read-only operations)."""

import pytest


pytestmark = pytest.mark.integration


class TestUEGet:
    """Tests for UE Simulator queries."""

    def test_ue_get_returns_dict(self, callbox):
        result = callbox.ue.ue_get()
        assert isinstance(result, dict)


class TestUEConfig:
    """Tests for UE Simulator configuration retrieval."""

    def test_config_get_returns_dict(self, callbox):
        result = callbox.ue.config_get()
        assert isinstance(result, dict)


class TestUEStats:
    """Tests for UE Simulator statistics."""

    def test_stats_returns_dict(self, callbox):
        result = callbox.ue.stats()
        assert isinstance(result, dict)
