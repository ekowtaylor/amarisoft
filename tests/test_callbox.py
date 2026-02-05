"""Tests for the Callbox orchestrator class."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from amarisoft.callbox import Callbox
from amarisoft.client import WebSocketClient
from amarisoft.enb import ENBApi
from amarisoft.mme import MMEApi
from amarisoft.ims import IMSApi
from amarisoft.ue import UEApi


class TestConstructor:
    def test_defaults(self):
        cb = Callbox("10.0.0.1")
        assert cb.host == "10.0.0.1"
        assert cb._enb_client.port == 9001
        assert cb._mme_client.port == 9000
        assert cb._ims_client.port == 9002
        assert cb._ue_client.port == 9003

    def test_custom_ports(self):
        cb = Callbox(
            "10.0.0.1",
            enb_port=8001,
            mme_port=8000,
            ims_port=8002,
            ue_port=8003,
        )
        assert cb._enb_client.port == 8001
        assert cb._mme_client.port == 8000
        assert cb._ims_client.port == 8002
        assert cb._ue_client.port == 8003

    def test_api_instances_created(self):
        cb = Callbox()
        assert isinstance(cb.enb, ENBApi)
        assert isinstance(cb.mme, MMEApi)
        assert isinstance(cb.ims, IMSApi)
        assert isinstance(cb.ue, UEApi)


class TestConnectAll:
    def test_all_succeed(self):
        cb = Callbox()
        ready = {"message": "ready"}
        for client in cb._clients.values():
            client.connect = MagicMock(return_value=ready)

        results = cb.connect_all()
        assert all(r["message"] == "ready" for r in results.values())
        for client in cb._clients.values():
            client.connect.assert_called_once()

    def test_partial_failure(self):
        cb = Callbox()
        ready = {"message": "ready"}

        cb._enb_client.connect = MagicMock(return_value=ready)
        cb._mme_client.connect = MagicMock(
            side_effect=ConnectionError("refused")
        )
        cb._ims_client.connect = MagicMock(return_value=ready)
        cb._ue_client.connect = MagicMock(return_value=ready)

        results = cb.connect_all()
        assert results["enb"]["message"] == "ready"
        assert "error" in results["mme"]
        assert results["ims"]["message"] == "ready"
        assert results["ue"]["message"] == "ready"


class TestIndividualConnect:
    def test_connect_enb(self):
        cb = Callbox()
        cb._enb_client.connect = MagicMock(return_value={"message": "ready"})
        result = cb.connect_enb()
        assert result["message"] == "ready"
        cb._enb_client.connect.assert_called_once()

    def test_connect_mme(self):
        cb = Callbox()
        cb._mme_client.connect = MagicMock(return_value={"message": "ready"})
        result = cb.connect_mme()
        assert result["message"] == "ready"

    def test_connect_ims(self):
        cb = Callbox()
        cb._ims_client.connect = MagicMock(return_value={"message": "ready"})
        result = cb.connect_ims()
        assert result["message"] == "ready"

    def test_connect_ue(self):
        cb = Callbox()
        cb._ue_client.connect = MagicMock(return_value={"message": "ready"})
        result = cb.connect_ue()
        assert result["message"] == "ready"


class TestClose:
    def test_close_calls_all(self):
        cb = Callbox()
        for client in cb._clients.values():
            client.close = MagicMock()

        cb.close()
        for client in cb._clients.values():
            client.close.assert_called_once()

    def test_close_handles_exceptions(self):
        cb = Callbox()
        cb._enb_client.close = MagicMock(side_effect=RuntimeError("boom"))
        cb._mme_client.close = MagicMock()
        cb._ims_client.close = MagicMock()
        cb._ue_client.close = MagicMock()

        cb.close()  # should not raise
        cb._mme_client.close.assert_called_once()


class TestStatus:
    def test_status_property(self):
        cb = Callbox()
        status = cb.status
        assert set(status.keys()) == {"enb", "mme", "ims", "ue"}
        # All disconnected by default
        assert all(v is False for v in status.values())


class TestSendRaw:
    def test_valid_service(self):
        cb = Callbox()
        cb._enb_client.send = MagicMock(return_value={"ok": True})
        result = cb.send_raw("enb", {"message": "test"})
        assert result["ok"] is True
        cb._enb_client.send.assert_called_once_with({"message": "test"})

    def test_invalid_service_raises(self):
        cb = Callbox()
        with pytest.raises(ValueError, match="Unknown service"):
            cb.send_raw("invalid", {"message": "test"})


class TestContextManager:
    def test_enter_calls_connect_all_exit_calls_close(self):
        cb = Callbox()
        ready = {"message": "ready"}
        for client in cb._clients.values():
            client.connect = MagicMock(return_value=ready)
            client.close = MagicMock()

        with cb as ctx:
            assert ctx is cb
            for client in cb._clients.values():
                client.connect.assert_called_once()

        for client in cb._clients.values():
            client.close.assert_called_once()


class TestRepr:
    def test_repr_disconnected(self):
        cb = Callbox("10.0.0.1")
        assert repr(cb) == "Callbox(10.0.0.1, 0/4 connected)"
