"""Tests for MMEApi-specific methods."""

from __future__ import annotations


class TestEnbGet:
    def test_basic(self, mock_client, mme):
        mme.enb_get()
        mock_client.send.assert_called_once_with({"message": "enb_get"})

    def test_with_filter(self, mock_client, mme):
        mme.enb_get(enb_id=1)
        mock_client.send.assert_called_once_with(
            {"message": "enb_get", "enb_id": 1}
        )


class TestGnbGet:
    def test_basic(self, mock_client, mme):
        mme.gnb_get()
        mock_client.send.assert_called_once_with({"message": "gnb_get"})


class TestSessionGet:
    def test_basic(self, mock_client, mme):
        mme.session_get()
        mock_client.send.assert_called_once_with({"message": "session_get"})

    def test_with_filter(self, mock_client, mme):
        mme.session_get(imsi="001")
        mock_client.send.assert_called_once_with(
            {"message": "session_get", "imsi": "001"}
        )


class TestBearerGet:
    def test_basic(self, mock_client, mme):
        mme.bearer_get()
        mock_client.send.assert_called_once_with({"message": "bearer_get"})


class TestUeDetach:
    def test_with_imsi(self, mock_client, mme):
        mme.ue_detach(imsi="001010123456789")
        mock_client.send.assert_called_once_with({
            "message": "ue_detach",
            "imsi": "001010123456789",
        })

    def test_with_imei(self, mock_client, mme):
        mme.ue_detach(imei="123456789012345")
        mock_client.send.assert_called_once_with({
            "message": "ue_detach",
            "imei": "123456789012345",
        })

    def test_with_both(self, mock_client, mme):
        mme.ue_detach(imsi="001", imei="123")
        sent = mock_client.send.call_args[0][0]
        assert sent["message"] == "ue_detach"
        assert sent["imsi"] == "001"
        assert sent["imei"] == "123"


class TestUeDeactivateBearer:
    def test_basic(self, mock_client, mme):
        mme.ue_deactivate_bearer(erab_id=5)
        mock_client.send.assert_called_once_with({
            "message": "ue_deactivate_bearer",
            "erab_id": 5,
        })

    def test_with_imsi(self, mock_client, mme):
        mme.ue_deactivate_bearer(erab_id=5, imsi="001")
        mock_client.send.assert_called_once_with({
            "message": "ue_deactivate_bearer",
            "erab_id": 5,
            "imsi": "001",
        })


class TestUeModifyBearer:
    def test_minimal(self, mock_client, mme):
        mme.ue_modify_bearer(imsi="001", erab_id=5, qci=9)
        mock_client.send.assert_called_once_with({
            "message": "ue_modify_bearer",
            "imsi": "001",
            "erab_id": 5,
            "qos": {"qci": 9},
        })

    def test_with_all_qos(self, mock_client, mme):
        mme.ue_modify_bearer(
            imsi="001",
            erab_id=5,
            qci=1,
            priority_level=2,
            pre_emption_capability="may_trigger",
            pre_emption_vulnerability="pre_emptable",
        )
        mock_client.send.assert_called_once_with({
            "message": "ue_modify_bearer",
            "imsi": "001",
            "erab_id": 5,
            "qos": {
                "qci": 1,
                "priority_level": 2,
                "pre_emption_capability": "may_trigger",
                "pre_emption_vulnerability": "pre_emptable",
            },
        })


class TestMtCsPaging:
    def test_sends(self, mock_client, mme):
        mme.mt_cs_paging(imsi="001")
        mock_client.send.assert_called_once_with({
            "message": "mt_cs_paging",
            "imsi": "001",
        })


class TestAttachRejectFilter:
    def test_sends(self, mock_client, mme):
        mme.attach_reject_filter(imsi="001", emm_cause=11)
        mock_client.send.assert_called_once_with({
            "message": "attach_reject_filter",
            "imsi": "001",
            "emm_cause": 11,
        })


class TestAttachRejectFilterClear:
    def test_sends(self, mock_client, mme):
        mme.attach_reject_filter_clear()
        mock_client.send.assert_called_once_with({
            "message": "attach_reject_filter",
            "clear": True,
        })


class TestRegistrationRejectFilter:
    def test_sends(self, mock_client, mme):
        mme.registration_reject_filter(imsi="001", cause=5)
        mock_client.send.assert_called_once_with({
            "message": "registration_mobility_periodic",
            "imsi": "001",
            "reject": True,
            "cause": 5,
        })


class TestSetT3512:
    def test_sends(self, mock_client, mme):
        mme.set_t3512(value=3600)
        mock_client.send.assert_called_once_with({
            "message": "t3512",
            "value": 3600,
        })


class TestPdnList:
    def test_basic(self, mock_client, mme):
        mme.pdn_list(apn="internet")
        mock_client.send.assert_called_once_with({
            "message": "pdn_list",
            "apn": "internet",
        })

    def test_with_extra_params(self, mock_client, mme):
        mme.pdn_list(apn="ims", esm_procedure_filter="skip")
        mock_client.send.assert_called_once_with({
            "message": "pdn_list",
            "apn": "ims",
            "esm_procedure_filter": "skip",
        })
