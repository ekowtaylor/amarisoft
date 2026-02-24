"""Tests for REST API routers.

Tests the FastAPI router endpoints using TestClient with mocked
CallboxManager to avoid actual WebSocket connections.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from amarisoft.exceptions import AmariError, AmariConnectionError, AmariTimeoutError
from service import __version__
from service.app import create_app
from service.config import Settings
from service.manager import (
    CallboxManager,
    CallboxStatus,
    ServiceStatus,
    set_manager,
    clear_manager,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        host="127.0.0.1",
        port=9010,
        callbox_host="192.168.1.100",
        enb_port=9001,
        mme_port=9000,
        ims_port=9002,
        ue_port=9003,
    )


@pytest.fixture
def mock_manager(settings: Settings) -> MagicMock:
    """Create a mocked CallboxManager."""
    manager = MagicMock(spec=CallboxManager)
    manager.settings = settings

    # Mock service APIs
    manager.enb = MagicMock()
    manager.mme = MagicMock()
    manager.ims = MagicMock()
    manager.ue = MagicMock()

    # Mock status methods
    manager.get_status.return_value = CallboxStatus(
        host="192.168.1.100",
        services={
            "enb": ServiceStatus(name="enb", host="192.168.1.100", port=9001, connected=True, version="2023-12-15"),
            "mme": ServiceStatus(name="mme", host="192.168.1.100", port=9000, connected=True, version="2023-12-15"),
            "ims": ServiceStatus(name="ims", host="192.168.1.100", port=9002, connected=False, version=None),
            "ue": ServiceStatus(name="ue", host="192.168.1.100", port=9003, connected=False, version=None),
        },
    )

    return manager


@pytest.fixture
def client(settings: Settings, mock_manager: MagicMock) -> TestClient:
    """Create a test client with mocked manager."""
    # Set the global manager to our mock
    set_manager(mock_manager)

    app = create_app(settings)
    yield TestClient(app)

    # Clean up
    clear_manager()


# ──────────────────────────────────────────────
# System Router Tests
# ──────────────────────────────────────────────


class TestSystemHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check_healthy(self, client: TestClient, mock_manager: MagicMock):
        """Test health check returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == __version__
        assert "timestamp" in data
        assert data["callbox"]["host"] == "192.168.1.100"
        assert data["callbox"]["connected_services"] == 2
        assert data["callbox"]["total_services"] == 4

    def test_health_check_unhealthy(self, client: TestClient, mock_manager: MagicMock):
        """Test health check returns unhealthy when no services connected."""
        mock_manager.get_status.return_value = CallboxStatus(
            host="192.168.1.100",
            services={
                "enb": ServiceStatus(name="enb", host="192.168.1.100", port=9001, connected=False, version=None),
                "mme": ServiceStatus(name="mme", host="192.168.1.100", port=9000, connected=False, version=None),
                "ims": ServiceStatus(name="ims", host="192.168.1.100", port=9002, connected=False, version=None),
                "ue": ServiceStatus(name="ue", host="192.168.1.100", port=9003, connected=False, version=None),
            },
        )

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"


class TestSystemLivenessEndpoint:
    """Tests for /health/live endpoint."""

    def test_liveness_always_ok(self, client: TestClient, _mock_manager: MagicMock):
        """Test liveness probe always returns ok."""
        response = client.get("/health/live")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestSystemReadinessEndpoint:
    """Tests for /health/ready endpoint."""

    def test_readiness_ready(self, client: TestClient, mock_manager: MagicMock):
        """Test readiness when services are connected."""
        response = client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert data["services"]["enb"] is True
        assert data["services"]["mme"] is True
        assert data["services"]["ims"] is False
        assert data["services"]["ue"] is False


class TestSystemVersionEndpoint:
    """Tests for /version endpoint."""

    def test_get_version(self, client: TestClient, mock_manager: MagicMock):
        """Test version endpoint returns API and service versions."""
        response = client.get("/version")

        assert response.status_code == 200
        data = response.json()
        assert data["api_version"] == __version__
        assert "services" in data
        assert data["services"]["enb"]["version"] == "2023-12-15"
        assert data["services"]["enb"]["connected"] is True


class TestSystemServicesEndpoint:
    """Tests for /services endpoints."""

    def test_get_all_services(self, client: TestClient, mock_manager: MagicMock):
        """Test getting all service statuses."""
        response = client.get("/services")

        assert response.status_code == 200
        data = response.json()
        assert data["host"] == "192.168.1.100"
        assert "services" in data

    def test_get_single_service(self, client: TestClient, _mock_manager: MagicMock):
        """Test getting a single service status."""
        response = client.get("/services/enb")

        assert response.status_code == 200

    def test_get_single_service_with_connect(self, client: TestClient, mock_manager: MagicMock):
        """Test getting service status with connect=true."""
        mock_manager.check_service.return_value = ServiceStatus(
            name="enb",
            host="192.168.1.100",
            port=9001,
            connected=True,
            version="2023-12-15",
        )

        response = client.get("/services/enb?connect=true")

        assert response.status_code == 200
        mock_manager.check_service.assert_called_once_with("enb")

    def test_connect_service(self, client: TestClient, mock_manager: MagicMock):
        """Test connecting to a service."""
        mock_manager.check_service.return_value = ServiceStatus(
            name="enb",
            host="192.168.1.100",
            port=9001,
            connected=True,
            version="2023-12-15",
        )

        response = client.post("/services/enb/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "connect"
        mock_manager.check_service.assert_called_once_with("enb")

    def test_disconnect_service(self, client: TestClient, mock_manager: MagicMock):
        """Test disconnecting from a service."""
        response = client.post("/services/enb/disconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "disconnect"
        mock_manager.disconnect_service.assert_called_once_with("enb")

    def test_reconnect_service(self, client: TestClient, mock_manager: MagicMock):
        """Test reconnecting to a service."""
        mock_manager.reconnect_service.return_value = ServiceStatus(
            name="enb",
            host="192.168.1.100",
            port=9001,
            connected=True,
            version="2023-12-15",
        )

        response = client.post("/services/enb/reconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "reconnect"
        mock_manager.reconnect_service.assert_called_once_with("enb")

    def test_connect_all_services(self, client: TestClient, mock_manager: MagicMock):
        """Test connecting to all services."""
        mock_manager.connect_all.return_value = mock_manager.get_status.return_value

        response = client.post("/services/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "connect_all"
        mock_manager.connect_all.assert_called_once()

    def test_disconnect_all_services(self, client: TestClient, mock_manager: MagicMock):
        """Test disconnecting from all services."""
        response = client.post("/services/disconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "disconnect_all"
        mock_manager.close_all.assert_called_once()


# ──────────────────────────────────────────────
# eNB Router Tests
# ──────────────────────────────────────────────


class TestEnbVersionEndpoint:
    """Tests for /enb/version endpoint."""

    def test_get_version(self, client: TestClient, mock_manager: MagicMock):
        """Test getting eNB version."""
        mock_manager.enb.version.return_value = {"version": "2023-12-15", "build": "1234"}

        response = client.get("/enb/version")

        assert response.status_code == 200
        assert response.json() == {"version": "2023-12-15", "build": "1234"}

    def test_get_version_connection_error(self, client: TestClient, mock_manager: MagicMock):
        """Test version endpoint with connection error."""
        mock_manager.enb.version.side_effect = AmariConnectionError("Connection refused")

        response = client.get("/enb/version")

        assert response.status_code == 503


class TestEnbStatsEndpoint:
    """Tests for /enb/stats endpoint."""

    def test_get_stats(self, client: TestClient, mock_manager: MagicMock):
        """Test getting eNB statistics."""
        mock_manager.enb.stats.return_value = {"cells": [], "ues": []}

        response = client.get("/enb/stats")

        assert response.status_code == 200
        mock_manager.enb.stats.assert_called_once_with(samples=False, rf=False)

    def test_get_stats_with_options(self, client: TestClient, mock_manager: MagicMock):
        """Test getting stats with query parameters."""
        mock_manager.enb.stats.return_value = {"cells": [], "ues": [], "samples": []}

        response = client.get("/enb/stats?samples=true&rf=true")

        assert response.status_code == 200
        mock_manager.enb.stats.assert_called_once_with(samples=True, rf=True)


class TestEnbConfigEndpoint:
    """Tests for /enb/config endpoints."""

    def test_get_config(self, client: TestClient, mock_manager: MagicMock):
        """Test getting eNB configuration."""
        mock_manager.enb.config_get.return_value = {"rf_driver": "sdr"}

        response = client.get("/enb/config")

        assert response.status_code == 200

    def test_set_config(self, client: TestClient, mock_manager: MagicMock):
        """Test setting eNB configuration."""
        mock_manager.enb.config_set.return_value = {"success": True}

        response = client.post("/enb/config", json={"config": {"rf_driver": "sdr"}})

        assert response.status_code == 200
        mock_manager.enb.config_set.assert_called_once_with(rf_driver="sdr")


class TestEnbUeEndpoints:
    """Tests for /enb/ue endpoints."""

    def test_list_ues(self, client: TestClient, mock_manager: MagicMock):
        """Test listing UEs connected to eNB."""
        mock_manager.enb.ue_get.return_value = {"ue_list": []}

        response = client.get("/enb/ue")

        assert response.status_code == 200
        mock_manager.enb.ue_get.assert_called_once()

    def test_list_ues_with_filter(self, client: TestClient, mock_manager: MagicMock):
        """Test listing UEs with IMSI filter."""
        mock_manager.enb.ue_get.return_value = {"ue_list": [{"imsi": "001010123456789"}]}

        response = client.get("/enb/ue?imsi=001010123456789")

        assert response.status_code == 200
        mock_manager.enb.ue_get.assert_called_once_with(imsi="001010123456789")

    def test_get_ue_by_id(self, client: TestClient, mock_manager: MagicMock):
        """Test getting UE by eNB UE ID."""
        mock_manager.enb.ue_get.return_value = {"enb_ue_id": 1}

        response = client.get("/enb/ue/1")

        assert response.status_code == 200
        mock_manager.enb.ue_get.assert_called_once_with(enb_ue_id=1)

    def test_rrc_release(self, client: TestClient, mock_manager: MagicMock):
        """Test RRC release."""
        mock_manager.enb.rrc_release.return_value = {"success": True}

        response = client.post("/enb/ue/1/rrc-release")

        assert response.status_code == 200
        mock_manager.enb.rrc_release.assert_called_once_with(enb_ue_id=1)

    def test_rrc_release_with_cause(self, client: TestClient, mock_manager: MagicMock):
        """Test RRC release with cause."""
        mock_manager.enb.rrc_release.return_value = {"success": True}

        response = client.post("/enb/ue/1/rrc-release", json={"cause": "other"})

        assert response.status_code == 200
        mock_manager.enb.rrc_release.assert_called_once_with(enb_ue_id=1, cause="other")

    def test_handover(self, client: TestClient, mock_manager: MagicMock):
        """Test triggering handover."""
        mock_manager.enb.handover.return_value = {"success": True}

        response = client.post("/enb/ue/1/handover", json={"target_cell_id": 2})

        assert response.status_code == 200
        mock_manager.enb.handover.assert_called_once_with(enb_ue_id=1, target_cell_id=2)


class TestEnbCellEndpoints:
    """Tests for /enb/cells endpoints."""

    def test_list_cells(self, client: TestClient, mock_manager: MagicMock):
        """Test listing cells."""
        mock_manager.enb.cells_get.return_value = {"cells": []}

        response = client.get("/enb/cells")

        assert response.status_code == 200

    def test_get_cell(self, client: TestClient, mock_manager: MagicMock):
        """Test getting specific cell."""
        mock_manager.enb.cells_get.return_value = {"cell_id": 1}

        response = client.get("/enb/cells/1")

        assert response.status_code == 200
        mock_manager.enb.cells_get.assert_called_once_with(cell_id=1)

    def test_set_cell_gain(self, client: TestClient, mock_manager: MagicMock):
        """Test setting cell gain."""
        mock_manager.enb.cell_gain.return_value = {"success": True}

        response = client.post("/enb/cells/1/gain", json={"gain": -20.0})

        assert response.status_code == 200
        mock_manager.enb.cell_gain.assert_called_once_with(cell_id=1, gain=-20.0)

    def test_set_cell_gain_validation(self, client: TestClient, _mock_manager: MagicMock):
        """Test cell gain validation (must be between -140 and 0)."""
        response = client.post("/enb/cells/1/gain", json={"gain": 10.0})

        assert response.status_code == 422  # Validation error

    def test_activate_cell(self, client: TestClient, mock_manager: MagicMock):
        """Test activating cell."""
        mock_manager.enb.cell_activate.return_value = {"success": True}

        response = client.post("/enb/cells/1/activate")

        assert response.status_code == 200
        mock_manager.enb.cell_activate.assert_called_once_with(cell_id=1)

    def test_deactivate_cell(self, client: TestClient, mock_manager: MagicMock):
        """Test deactivating cell."""
        mock_manager.enb.cell_deactivate.return_value = {"success": True}

        response = client.post("/enb/cells/1/deactivate")

        assert response.status_code == 200
        mock_manager.enb.cell_deactivate.assert_called_once_with(cell_id=1)


class TestEnbPagingEndpoint:
    """Tests for /enb/paging endpoint."""

    def test_send_paging(self, client: TestClient, mock_manager: MagicMock):
        """Test sending paging."""
        mock_manager.enb.paging.return_value = {"success": True}

        response = client.post("/enb/paging", json={"imsi": "001010123456789", "domain": "ps"})

        assert response.status_code == 200
        mock_manager.enb.paging.assert_called_once_with(imsi="001010123456789", domain="ps")


class TestEnbLogsEndpoints:
    """Tests for /enb/logs endpoints."""

    def test_get_logs(self, client: TestClient, mock_manager: MagicMock):
        """Test getting logs."""
        mock_manager.enb.log_get.return_value = {"logs": []}

        response = client.get("/enb/logs")

        assert response.status_code == 200
        mock_manager.enb.log_get.assert_called_once_with(
            min_=None, max_=None, layer=None, timeout=None
        )

    def test_get_logs_with_params(self, client: TestClient, mock_manager: MagicMock):
        """Test getting logs with parameters."""
        mock_manager.enb.log_get.return_value = {"logs": []}

        response = client.get("/enb/logs?min=0&max=100&layer=PHY")

        assert response.status_code == 200
        mock_manager.enb.log_get.assert_called_once_with(
            min_=0, max_=100, layer="PHY", timeout=None
        )

    def test_configure_logs(self, client: TestClient, mock_manager: MagicMock):
        """Test configuring logs."""
        mock_manager.enb.log_set.return_value = {"success": True}

        response = client.post(
            "/enb/logs/config",
            json={"layers": {"PHY": {"level": "debug"}}, "max_size": 1000},
        )

        assert response.status_code == 200


# ──────────────────────────────────────────────
# MME Router Tests
# ──────────────────────────────────────────────


class TestMmeVersionEndpoint:
    """Tests for /mme/version endpoint."""

    def test_get_version(self, client: TestClient, mock_manager: MagicMock):
        """Test getting MME version."""
        mock_manager.mme.version.return_value = {"version": "2023-12-15"}

        response = client.get("/mme/version")

        assert response.status_code == 200


class TestMmeUeEndpoints:
    """Tests for /mme/ue endpoints."""

    def test_list_ues(self, client: TestClient, mock_manager: MagicMock):
        """Test listing UEs registered with MME."""
        mock_manager.mme.ue_get.return_value = {"ue_list": []}

        response = client.get("/mme/ue")

        assert response.status_code == 200

    def test_get_ue_by_id(self, client: TestClient, mock_manager: MagicMock):
        """Test getting UE by MME UE ID."""
        mock_manager.mme.ue_get.return_value = {"mme_ue_id": 1}

        response = client.get("/mme/ue/1")

        assert response.status_code == 200
        mock_manager.mme.ue_get.assert_called_once_with(mme_ue_id=1)

    def test_get_ue_by_imsi(self, client: TestClient, mock_manager: MagicMock):
        """Test getting UE by IMSI."""
        mock_manager.mme.ue_get.return_value = {"imsi": "001010123456789"}

        response = client.get("/mme/ue/imsi/001010123456789")

        assert response.status_code == 200
        mock_manager.mme.ue_get.assert_called_once_with(imsi="001010123456789")

    def test_release_ue(self, client: TestClient, mock_manager: MagicMock):
        """Test releasing UE."""
        mock_manager.mme.ue_release.return_value = {"success": True}

        response = client.post("/mme/ue/1/release")

        assert response.status_code == 200
        mock_manager.mme.ue_release.assert_called_once_with(mme_ue_id=1)

    def test_release_ue_by_imsi(self, client: TestClient, mock_manager: MagicMock):
        """Test releasing UE by IMSI."""
        mock_manager.mme.ue_release.return_value = {"success": True}

        response = client.post("/mme/ue/imsi/001010123456789/release")

        assert response.status_code == 200
        mock_manager.mme.ue_release.assert_called_once_with(imsi="001010123456789")


class TestMmePdnEndpoints:
    """Tests for /mme/ue/{id}/pdn endpoints."""

    def test_create_pdn(self, client: TestClient, mock_manager: MagicMock):
        """Test creating PDN connection."""
        mock_manager.mme.pdn_connect.return_value = {"pdn_id": 1}

        response = client.post(
            "/mme/ue/1/pdn",
            json={"apn": "internet", "pdn_type": "ipv4"},
        )

        assert response.status_code == 200
        mock_manager.mme.pdn_connect.assert_called_once_with(
            mme_ue_id=1, apn="internet", pdn_type="ipv4"
        )

    def test_disconnect_pdn(self, client: TestClient, mock_manager: MagicMock):
        """Test disconnecting PDN."""
        mock_manager.mme.pdn_disconnect.return_value = {"success": True}

        response = client.delete("/mme/ue/1/pdn/5")

        assert response.status_code == 200
        mock_manager.mme.pdn_disconnect.assert_called_once_with(mme_ue_id=1, pdn_id=5)


class TestMmeBearerEndpoints:
    """Tests for /mme/ue/{id}/bearer endpoints."""

    def test_create_bearer(self, client: TestClient, mock_manager: MagicMock):
        """Test creating dedicated bearer."""
        mock_manager.mme.bearer_activate.return_value = {"bearer_id": 6}

        response = client.post("/mme/ue/1/bearer", json={"qci": 1})

        assert response.status_code == 200
        mock_manager.mme.bearer_activate.assert_called_once_with(mme_ue_id=1, qci=1)

    def test_create_bearer_full(self, client: TestClient, _mock_manager: MagicMock):
        """Test creating dedicated bearer with all parameters."""
        mock_manager.mme.bearer_activate.return_value = {"bearer_id": 6}

        response = client.post(
            "/mme/ue/1/bearer",
            json={
                "qci": 1,
                "gbr_dl": 1000,
                "gbr_ul": 500,
                "mbr_dl": 2000,
                "mbr_ul": 1000,
                "arp_priority": 5,
            },
        )

        assert response.status_code == 200

    def test_delete_bearer(self, client: TestClient, mock_manager: MagicMock):
        """Test deleting bearer."""
        mock_manager.mme.bearer_deactivate.return_value = {"success": True}

        response = client.delete("/mme/ue/1/bearer/6")

        assert response.status_code == 200
        mock_manager.mme.bearer_deactivate.assert_called_once_with(mme_ue_id=1, bearer_id=6)


class TestMmeSmsEndpoint:
    """Tests for /mme SMS endpoints."""

    def test_send_sms(self, client: TestClient, mock_manager: MagicMock):
        """Test sending SMS via MME."""
        mock_manager.mme.sms_send.return_value = {"success": True}

        response = client.post("/mme/ue/1/sms?message=Hello")

        assert response.status_code == 200
        mock_manager.mme.sms_send.assert_called_once_with(mme_ue_id=1, message="Hello")

    def test_send_sms_by_imsi(self, client: TestClient, mock_manager: MagicMock):
        """Test sending SMS by IMSI."""
        mock_manager.mme.sms_send.return_value = {"success": True}

        response = client.post("/mme/ue/imsi/001010123456789/sms?message=Hello")

        assert response.status_code == 200
        mock_manager.mme.sms_send.assert_called_once_with(imsi="001010123456789", message="Hello")


class TestMmePagingEndpoint:
    """Tests for /mme/paging endpoint."""

    def test_page_ue(self, client: TestClient, mock_manager: MagicMock):
        """Test paging UE."""
        mock_manager.mme.paging.return_value = {"success": True}

        response = client.post("/mme/paging?imsi=001010123456789")

        assert response.status_code == 200
        mock_manager.mme.paging.assert_called_once_with(imsi="001010123456789")


# ──────────────────────────────────────────────
# IMS Router Tests
# ──────────────────────────────────────────────


class TestImsVersionEndpoint:
    """Tests for /ims/version endpoint."""

    def test_get_version(self, client: TestClient, mock_manager: MagicMock):
        """Test getting IMS version."""
        mock_manager.ims.version.return_value = {"version": "2023-12-15"}

        response = client.get("/ims/version")

        assert response.status_code == 200


class TestImsCallEndpoints:
    """Tests for /ims/calls endpoints."""

    def test_list_calls(self, client: TestClient, mock_manager: MagicMock):
        """Test listing active calls."""
        mock_manager.ims.call_get.return_value = {"calls": []}

        response = client.get("/ims/calls")

        assert response.status_code == 200

    def test_get_call(self, client: TestClient, mock_manager: MagicMock):
        """Test getting specific call."""
        mock_manager.ims.call_get.return_value = {"call_id": 1}

        response = client.get("/ims/calls/1")

        assert response.status_code == 200
        mock_manager.ims.call_get.assert_called_once_with(call_id=1)

    def test_initiate_call(self, client: TestClient, mock_manager: MagicMock):
        """Test initiating a call."""
        mock_manager.ims.call_start.return_value = {"call_id": 1}

        response = client.post(
            "/ims/calls?from_imsi=001010123456789&to_imsi=001010123456780"
        )

        assert response.status_code == 200
        mock_manager.ims.call_start.assert_called_once_with(
            from_imsi="001010123456789",
            to_imsi="001010123456780",
            audio=True,
            video=False,
        )

    def test_initiate_video_call(self, client: TestClient, mock_manager: MagicMock):
        """Test initiating a video call."""
        mock_manager.ims.call_start.return_value = {"call_id": 1}

        response = client.post(
            "/ims/calls?from_imsi=001010123456789&to_imsi=001010123456780&video=true"
        )

        assert response.status_code == 200
        mock_manager.ims.call_start.assert_called_once_with(
            from_imsi="001010123456789",
            to_imsi="001010123456780",
            audio=True,
            video=True,
        )

    def test_answer_call(self, client: TestClient, mock_manager: MagicMock):
        """Test answering a call."""
        mock_manager.ims.call_answer.return_value = {"success": True}

        response = client.post("/ims/calls/1/answer")

        assert response.status_code == 200
        mock_manager.ims.call_answer.assert_called_once_with(call_id=1)

    def test_hangup_call(self, client: TestClient, mock_manager: MagicMock):
        """Test hanging up a call."""
        mock_manager.ims.call_hangup.return_value = {"success": True}

        response = client.post("/ims/calls/1/hangup")

        assert response.status_code == 200
        mock_manager.ims.call_hangup.assert_called_once_with(call_id=1)

    def test_hold_call(self, client: TestClient, mock_manager: MagicMock):
        """Test putting call on hold."""
        mock_manager.ims.call_hold.return_value = {"success": True}

        response = client.post("/ims/calls/1/hold")

        assert response.status_code == 200
        mock_manager.ims.call_hold.assert_called_once_with(call_id=1)

    def test_resume_call(self, client: TestClient, mock_manager: MagicMock):
        """Test resuming a held call."""
        mock_manager.ims.call_resume.return_value = {"success": True}

        response = client.post("/ims/calls/1/resume")

        assert response.status_code == 200
        mock_manager.ims.call_resume.assert_called_once_with(call_id=1)


class TestImsSmsEndpoint:
    """Tests for /ims/sms endpoint."""

    def test_send_sms(self, client: TestClient, mock_manager: MagicMock):
        """Test sending IMS SMS."""
        mock_manager.ims.sms_send.return_value = {"success": True}

        response = client.post(
            "/ims/sms?from_imsi=001010123456789&to_imsi=001010123456780&message=Hello"
        )

        assert response.status_code == 200
        mock_manager.ims.sms_send.assert_called_once_with(
            from_imsi="001010123456789",
            to_imsi="001010123456780",
            message="Hello",
        )


# ──────────────────────────────────────────────
# UE Simulator Router Tests
# ──────────────────────────────────────────────


class TestUeVersionEndpoint:
    """Tests for /ue/version endpoint."""

    def test_get_version(self, client: TestClient, mock_manager: MagicMock):
        """Test getting UE Simulator version."""
        mock_manager.ue.version.return_value = {"version": "2023-12-15"}

        response = client.get("/ue/version")

        assert response.status_code == 200


class TestUeListEndpoint:
    """Tests for /ue/list endpoint."""

    def test_list_ues(self, client: TestClient, mock_manager: MagicMock):
        """Test listing simulated UEs."""
        mock_manager.ue.ue_get.return_value = {"ue_list": []}

        response = client.get("/ue/list")

        assert response.status_code == 200

    def test_list_ues_with_filter(self, client: TestClient, mock_manager: MagicMock):
        """Test listing UEs with filter."""
        mock_manager.ue.ue_get.return_value = {"ue_list": []}

        response = client.get("/ue/list?ue_id=1&imsi=001010123456789")

        assert response.status_code == 200
        mock_manager.ue.ue_get.assert_called_once_with(ue_id=1, imsi="001010123456789")


class TestUePowerEndpoints:
    """Tests for /ue/power endpoints."""

    def test_power_on_all(self, client: TestClient, mock_manager: MagicMock):
        """Test powering on all UEs."""
        mock_manager.ue.power_on.return_value = {"success": True}

        response = client.post("/ue/power/on")

        assert response.status_code == 200
        mock_manager.ue.power_on.assert_called_once_with(ue_id=None)

    def test_power_on_specific(self, client: TestClient, mock_manager: MagicMock):
        """Test powering on specific UE."""
        mock_manager.ue.power_on.return_value = {"success": True}

        response = client.post("/ue/power/on", json={"ue_id": 1})

        assert response.status_code == 200
        mock_manager.ue.power_on.assert_called_once_with(ue_id=1)

    def test_power_off_all(self, client: TestClient, mock_manager: MagicMock):
        """Test powering off all UEs."""
        mock_manager.ue.power_off.return_value = {"success": True}

        response = client.post("/ue/power/off")

        assert response.status_code == 200
        mock_manager.ue.power_off.assert_called_once_with(ue_id=None)

    def test_power_on_ue_endpoint(self, client: TestClient, mock_manager: MagicMock):
        """Test powering on specific UE via path."""
        mock_manager.ue.power_on.return_value = {"success": True}

        response = client.post("/ue/1/power/on")

        assert response.status_code == 200
        mock_manager.ue.power_on.assert_called_once_with(ue_id=1)

    def test_power_off_ue_endpoint(self, client: TestClient, mock_manager: MagicMock):
        """Test powering off specific UE via path."""
        mock_manager.ue.power_off.return_value = {"success": True}

        response = client.post("/ue/1/power/off")

        assert response.status_code == 200
        mock_manager.ue.power_off.assert_called_once_with(ue_id=1)


class TestUeBearerEndpoint:
    """Tests for /ue/{id}/bearer endpoints."""

    def test_activate_dedicated_bearer(self, client: TestClient, mock_manager: MagicMock):
        """Test activating dedicated bearer."""
        mock_manager.ue.ue_activate_dedicated_bearer.return_value = {"success": True}

        response = client.post("/ue/1/bearer/dedicated?def_bearer_id=5&qci=1")

        assert response.status_code == 200
        mock_manager.ue.ue_activate_dedicated_bearer.assert_called_once_with(
            ue_id=1, def_bearer_id=5, qci=1
        )

    def test_activate_dedicated_bearer_invalid_qci(self, client: TestClient, _mock_manager: MagicMock):
        """Test activating bearer with invalid QCI."""
        response = client.post("/ue/1/bearer/dedicated?def_bearer_id=5&qci=15")

        assert response.status_code == 422  # Validation error


class TestUeRrcEndpoint:
    """Tests for /ue/{id}/rrc endpoints."""

    def test_ue_assistance_info(self, client: TestClient, mock_manager: MagicMock):
        """Test sending UE assistance information."""
        mock_manager.ue.ue_assistance_information.return_value = {"success": True}

        response = client.post("/ue/1/rrc/assistance?preferred_state=idle")

        assert response.status_code == 200
        mock_manager.ue.ue_assistance_information.assert_called_once_with(
            ue_id=1, preferred_rrc_state="idle"
        )


# ──────────────────────────────────────────────
# Error Handling Tests
# ──────────────────────────────────────────────


class TestErrorHandling:
    """Tests for error handling in routers."""

    def test_connection_error_returns_503(self, client: TestClient, mock_manager: MagicMock):
        """Test that connection errors return 503."""
        mock_manager.enb.version.side_effect = AmariConnectionError("Connection refused")

        response = client.get("/enb/version")

        assert response.status_code == 503
        data = response.json()
        assert data["error_type"] == "ServiceUnavailableError"

    def test_timeout_error_returns_504(self, client: TestClient, mock_manager: MagicMock):
        """Test that timeout errors return 504."""
        mock_manager.enb.version.side_effect = AmariTimeoutError("Request timed out")

        response = client.get("/enb/version")

        assert response.status_code == 504
        data = response.json()
        assert data["error_type"] == "GatewayTimeoutError"

    def test_amari_error_returns_400(self, client: TestClient, mock_manager: MagicMock):
        """Test that general Amari errors return 400."""
        mock_manager.enb.version.side_effect = AmariError("Invalid parameter")

        response = client.get("/enb/version")

        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "BadRequestError"

    def test_validation_error(self, client: TestClient, _mock_manager: MagicMock):
        """Test that validation errors return 422."""
        # Missing required field
        response = client.post("/enb/config", json={})

        assert response.status_code == 422

    def test_unknown_service_error(self, client: TestClient, mock_manager: MagicMock):
        """Test error for unknown service."""
        mock_manager.get_status.return_value = CallboxStatus(
            host="192.168.1.100",
            services={
                "enb": ServiceStatus(name="enb", host="192.168.1.100", port=9001, connected=True, version="2023-12-15"),
            },
        )

        response = client.get("/services/unknown")

        assert response.status_code == 500  # Internal server error from ValueError
