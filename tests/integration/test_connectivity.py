"""Integration tests for basic Callbox connectivity."""

import pytest

from amarisoft import Callbox


pytestmark = pytest.mark.integration


class TestConnectAll:
    """Tests for connecting to all services at once."""

    def test_connect_all_returns_ready(self, callbox):
        """connect_all() should leave all services connected."""
        status = callbox.status
        assert status["enb"] is True
        assert status["mme"] is True
        assert status["ims"] is True
        assert status["ue"] is True


class TestIndividualConnections:
    """Tests for connecting to each service individually."""

    def test_connect_enb(self, callbox_factory):
        cb = callbox_factory()
        ready = cb.connect_enb()
        assert isinstance(ready, dict)
        assert cb.status["enb"] is True

    def test_connect_mme(self, callbox_factory):
        cb = callbox_factory()
        ready = cb.connect_mme()
        assert isinstance(ready, dict)
        assert cb.status["mme"] is True

    def test_connect_ims(self, callbox_factory):
        cb = callbox_factory()
        ready = cb.connect_ims()
        assert isinstance(ready, dict)
        assert cb.status["ims"] is True

    def test_connect_ue(self, callbox_factory):
        cb = callbox_factory()
        ready = cb.connect_ue()
        assert isinstance(ready, dict)
        assert cb.status["ue"] is True


class TestVersion:
    """Tests for version() on each service."""

    def test_enb_version(self, callbox):
        result = callbox.enb.version()
        assert isinstance(result, dict)
        assert result.get("message") == "version"

    def test_mme_version(self, callbox):
        result = callbox.mme.version()
        assert isinstance(result, dict)
        assert result.get("message") == "version"

    def test_ims_version(self, callbox):
        result = callbox.ims.version()
        assert isinstance(result, dict)
        assert result.get("message") == "version"

    def test_ue_version(self, callbox):
        result = callbox.ue.version()
        assert isinstance(result, dict)
        assert result.get("message") == "version"


class TestHelp:
    """Tests for help() on each service."""

    def test_enb_help(self, callbox):
        result = callbox.enb.help()
        assert isinstance(result, dict)

    def test_mme_help(self, callbox):
        result = callbox.mme.help()
        assert isinstance(result, dict)

    def test_ims_help(self, callbox):
        result = callbox.ims.help()
        assert isinstance(result, dict)

    def test_ue_help(self, callbox):
        result = callbox.ue.help()
        assert isinstance(result, dict)


class TestContextManager:
    """Test context manager usage."""

    def test_context_manager_connects_and_closes(
        self, callbox_host, callbox_password, callbox_ssl, callbox_ssl_verify
    ):
        with Callbox(
            callbox_host,
            password=callbox_password,
            ssl=callbox_ssl,
            ssl_verify=callbox_ssl_verify,
        ) as cb:
            assert cb.status["enb"] is True
            assert cb.status["mme"] is True
        # After exiting, connections should be closed
        assert cb.status["enb"] is False
        assert cb.status["mme"] is False
