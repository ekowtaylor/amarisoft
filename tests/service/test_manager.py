"""Tests for CallboxManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from client.websocket.exceptions import AmariConnectionError
from service.config import Settings
from service.manager import (
    CallboxManager,
    CallboxStatus,
    clear_manager,
    get_manager,
    ServiceStatus,
    set_manager,
)


@pytest.fixture
def settings():
    """Return default Settings instance."""
    return Settings()


@pytest.fixture
def mock_ws_client():
    """Return a mock WebSocketClient."""
    client = MagicMock()
    client.connected = True
    client.connect.return_value = {"message": "ready"}
    return client


class TestServiceStatus:
    """Tests for ServiceStatus dataclass."""

    def test_default_values(self):
        status = ServiceStatus(name="eNB/gNB", port=9001)
        assert status.name == "eNB/gNB"
        assert status.port == 9001
        assert status.connected is False
        assert status.version is None
        assert status.error is None

    def test_to_dict(self):
        status = ServiceStatus(
            name="eNB/gNB",
            port=9001,
            connected=True,
            version="2024-06-01",
            error=None,
        )
        result = status.to_dict()
        assert result == {
            "name": "eNB/gNB",
            "port": 9001,
            "connected": True,
            "version": "2024-06-01",
            "error": None,
        }


class TestCallboxStatus:
    """Tests for CallboxStatus dataclass."""

    def test_healthy_when_one_connected(self):
        status = CallboxStatus(host="127.0.0.1")
        status.services["enb"] = ServiceStatus("eNB", 9001, connected=True)
        status.services["mme"] = ServiceStatus("MME", 9000, connected=False)
        assert status.healthy is True

    def test_not_healthy_when_none_connected(self):
        status = CallboxStatus(host="127.0.0.1")
        status.services["enb"] = ServiceStatus("eNB", 9001, connected=False)
        status.services["mme"] = ServiceStatus("MME", 9000, connected=False)
        assert status.healthy is False

    def test_all_connected(self):
        status = CallboxStatus(host="127.0.0.1")
        status.services["enb"] = ServiceStatus("eNB", 9001, connected=True)
        status.services["mme"] = ServiceStatus("MME", 9000, connected=True)
        assert status.all_connected is True

    def test_not_all_connected(self):
        status = CallboxStatus(host="127.0.0.1")
        status.services["enb"] = ServiceStatus("eNB", 9001, connected=True)
        status.services["mme"] = ServiceStatus("MME", 9000, connected=False)
        assert status.all_connected is False

    def test_connected_count(self):
        status = CallboxStatus(host="127.0.0.1")
        status.services["enb"] = ServiceStatus("eNB", 9001, connected=True)
        status.services["mme"] = ServiceStatus("MME", 9000, connected=False)
        status.services["ims"] = ServiceStatus("IMS", 9002, connected=True)
        assert status.connected_count == 2

    def test_to_dict(self):
        status = CallboxStatus(host="127.0.0.1")
        status.services["enb"] = ServiceStatus("eNB", 9001, connected=True)
        result = status.to_dict()
        assert result["host"] == "127.0.0.1"
        assert result["healthy"] is True
        assert result["connected_count"] == 1
        assert "enb" in result["services"]


class TestCallboxManager:
    """Tests for CallboxManager."""

    def test_init(self, settings):
        manager = CallboxManager(settings)
        assert manager._settings == settings
        assert manager._enb_client is None
        assert manager._mme_client is None
        assert manager._ims_client is None
        assert manager._ue_client is None

    @patch("service.manager.WebSocketClient")
    def test_enb_property_creates_connection(self, MockClient, settings):
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.connect.return_value = {"message": "ready"}
        MockClient.return_value = mock_client

        manager = CallboxManager(settings)
        enb = manager.enb

        MockClient.assert_called_once_with(
            host=settings.callbox_host,
            port=settings.enb_port,
            password=settings.ws_password,
            ssl=settings.ssl,
            ssl_verify=settings.ssl_verify,
            timeout=settings.ws_timeout,
            auto_reconnect=settings.auto_reconnect,
        )
        mock_client.connect.assert_called_once()
        assert enb is not None

    @patch("service.manager.WebSocketClient")
    def test_enb_property_reuses_connection(self, MockClient, settings):
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.connect.return_value = {"message": "ready"}
        MockClient.return_value = mock_client

        manager = CallboxManager(settings)
        enb1 = manager.enb
        enb2 = manager.enb

        # Should only create one client
        assert MockClient.call_count == 1
        assert enb1 is enb2

    @patch("service.manager.WebSocketClient")
    def test_mme_property_creates_connection(self, MockClient, settings):
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.connect.return_value = {"message": "ready"}
        MockClient.return_value = mock_client

        manager = CallboxManager(settings)
        mme = manager.mme

        MockClient.assert_called_once_with(
            host=settings.callbox_host,
            port=settings.mme_port,
            password=settings.ws_password,
            ssl=settings.ssl,
            ssl_verify=settings.ssl_verify,
            timeout=settings.ws_timeout,
            auto_reconnect=settings.auto_reconnect,
        )
        assert mme is not None

    @patch("service.manager.WebSocketClient")
    def test_connection_failure_raises_api_error(self, MockClient, settings):
        mock_client = MagicMock()
        mock_client.connected = False
        mock_client.connect.side_effect = AmariConnectionError("Connection refused")
        MockClient.return_value = mock_client

        manager = CallboxManager(settings)

        from service.exceptions import ServiceUnavailableError

        with pytest.raises(ServiceUnavailableError):
            _ = manager.enb

    def test_get_status_no_connections(self, settings):
        manager = CallboxManager(settings)
        status = manager.get_status()

        assert status.host == settings.callbox_host
        assert len(status.services) == 4
        assert status.healthy is False
        assert status.connected_count == 0
        for svc in status.services.values():
            assert svc.connected is False
            assert svc.error == "Not connected"

    @patch("service.manager.WebSocketClient")
    def test_check_service_valid(self, MockClient, settings):
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.connect.return_value = {"message": "ready"}
        MockClient.return_value = mock_client

        manager = CallboxManager(settings)

        # Mock the version call
        with patch.object(manager, "_ensure_client") as mock_ensure:
            mock_api = MagicMock()
            mock_api.version.return_value = {"version": "2024-06-01"}
            mock_ensure.return_value = mock_api

            status = manager.check_service("enb")

        assert status.connected is True
        assert status.version == "2024-06-01"

    def test_check_service_invalid_name(self, settings):
        manager = CallboxManager(settings)
        with pytest.raises(ValueError, match="Unknown service"):
            manager.check_service("invalid")

    @patch("service.manager.WebSocketClient")
    def test_disconnect_service(self, MockClient, settings):
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.connect.return_value = {"message": "ready"}
        MockClient.return_value = mock_client

        manager = CallboxManager(settings)
        # First connect
        _ = manager.enb

        # Now disconnect
        manager.disconnect_service("enb")

        mock_client.close.assert_called_once()
        assert manager._enb_client is None
        assert manager._enb_api is None

    def test_disconnect_service_invalid_name(self, settings):
        manager = CallboxManager(settings)
        with pytest.raises(ValueError, match="Unknown service"):
            manager.disconnect_service("invalid")

    @patch("service.manager.WebSocketClient")
    def test_close_all(self, MockClient, settings):
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.connect.return_value = {"message": "ready"}
        MockClient.return_value = mock_client

        manager = CallboxManager(settings)
        # Connect to multiple services
        _ = manager.enb
        _ = manager.mme

        manager.close_all()

        assert manager._enb_client is None
        assert manager._mme_client is None

    @patch("service.manager.WebSocketClient")
    def test_context_manager(self, MockClient, settings):
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.connect.return_value = {"message": "ready"}
        MockClient.return_value = mock_client

        with CallboxManager(settings) as manager:
            assert manager is not None

    def test_repr(self, settings):
        manager = CallboxManager(settings)
        repr_str = repr(manager)
        assert "CallboxManager" in repr_str
        assert settings.callbox_host in repr_str
        assert "0/4 connected" in repr_str


class TestGlobalManager:
    """Tests for global manager functions."""

    def test_get_manager_not_initialized(self):
        clear_manager()
        with pytest.raises(RuntimeError, match="not initialized"):
            get_manager()

    def test_set_and_get_manager(self, settings):
        clear_manager()
        manager = CallboxManager(settings)
        set_manager(manager)

        result = get_manager()
        assert result is manager

        clear_manager()

    def test_clear_manager(self, settings):
        manager = CallboxManager(settings)
        set_manager(manager)

        clear_manager()

        with pytest.raises(RuntimeError, match="not initialized"):
            get_manager()
