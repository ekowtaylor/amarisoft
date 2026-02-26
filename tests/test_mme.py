"""Tests for MMEApi-specific methods."""

from __future__ import annotations


class TestEnbStatus:
    def test_basic(self, mock_client, mme):
        mme.enb_status()
        mock_client.send.assert_called_once_with({"message": "enb"})


class TestGnbStatus:
    def test_basic(self, mock_client, mme):
        mme.gnb_status()
        mock_client.send.assert_called_once_with({"message": "gnb"})


class TestNgRanStatus:
    def test_basic(self, mock_client, mme):
        mme.ng_ran_status()
        mock_client.send.assert_called_once_with({"message": "ng_ran"})


class TestUeDetach:
    def test_with_imsi(self, mock_client, mme):
        mme.ue_detach(imsi="001010123456789")
        mock_client.send.assert_called_once_with(
            {
                "message": "ue_detach",
                "imsi": "001010123456789",
            }
        )

    def test_with_imei(self, mock_client, mme):
        mme.ue_detach(imei="123456789012345")
        mock_client.send.assert_called_once_with(
            {
                "message": "ue_detach",
                "imei": "123456789012345",
            }
        )

    def test_with_both(self, mock_client, mme):
        mme.ue_detach(imsi="001", imei="123")
        sent = mock_client.send.call_args[0][0]
        assert sent["message"] == "ue_detach"
        assert sent["imsi"] == "001"
        assert sent["imei"] == "123"


class TestUeDeactivateBearer:
    def test_basic(self, mock_client, mme):
        mme.ue_deactivate_bearer(erab_id=5)
        mock_client.send.assert_called_once_with(
            {
                "message": "ue_deactivate_bearer",
                "erab_id": 5,
            }
        )

    def test_with_imsi(self, mock_client, mme):
        mme.ue_deactivate_bearer(erab_id=5, imsi="001")
        mock_client.send.assert_called_once_with(
            {
                "message": "ue_deactivate_bearer",
                "erab_id": 5,
                "imsi": "001",
            }
        )


class TestUeModifyBearer:
    def test_minimal(self, mock_client, mme):
        mme.ue_modify_bearer(imsi="001", erab_id=5, qci=9)
        mock_client.send.assert_called_once_with(
            {
                "message": "ue_modify_bearer",
                "imsi": "001",
                "erab_id": 5,
                "qos": {"qci": 9},
            }
        )

    def test_with_all_qos(self, mock_client, mme):
        mme.ue_modify_bearer(
            imsi="001",
            erab_id=5,
            qci=1,
            priority_level=2,
            pre_emption_capability="may_trigger",
            pre_emption_vulnerability="pre_emptable",
        )
        mock_client.send.assert_called_once_with(
            {
                "message": "ue_modify_bearer",
                "imsi": "001",
                "erab_id": 5,
                "qos": {
                    "qci": 1,
                    "priority_level": 2,
                    "pre_emption_capability": "may_trigger",
                    "pre_emption_vulnerability": "pre_emptable",
                },
            }
        )


class TestMtCsPaging:
    def test_sends(self, mock_client, mme):
        mme.mt_cs_paging(imsi="001")
        mock_client.send.assert_called_once_with(
            {
                "message": "mt_cs_paging",
                "imsi": "001",
            }
        )


class TestAttachRejectFilter:
    def test_sends(self, mock_client, mme):
        mme.attach_reject_filter(imsi="001", emm_cause=11)
        mock_client.send.assert_called_once_with(
            {
                "message": "attach_reject_filter",
                "imsi": "001",
                "emm_cause": 11,
            }
        )


class TestAttachRejectFilterClear:
    def test_sends(self, mock_client, mme):
        mme.attach_reject_filter_clear()
        mock_client.send.assert_called_once_with(
            {
                "message": "attach_reject_filter",
                "clear": True,
            }
        )


class TestRegistrationRejectFilter:
    def test_sends(self, mock_client, mme):
        mme.registration_reject_filter(imsi="001", cause=5)
        mock_client.send.assert_called_once_with(
            {
                "message": "registration_mobility_periodic",
                "imsi": "001",
                "reject": True,
                "cause": 5,
            }
        )


class TestSetT3512:
    def test_sends(self, mock_client, mme):
        mme.set_t3512(value=3600)
        mock_client.send.assert_called_once_with(
            {
                "message": "t3512",
                "value": 3600,
            }
        )


class TestPdnList:
    def test_basic(self, mock_client, mme):
        mme.pdn_list(apn="internet")
        mock_client.send.assert_called_once_with(
            {
                "message": "pdn_list",
                "apn": "internet",
            }
        )

    def test_with_extra_params(self, mock_client, mme):
        mme.pdn_list(apn="ims", esm_procedure_filter="skip")
        mock_client.send.assert_called_once_with(
            {
                "message": "pdn_list",
                "apn": "ims",
                "esm_procedure_filter": "skip",
            }
        )


class TestSetDefaultApn:
    def test_minimal(self, mock_client, mme):
        mme.set_default_apn()
        mock_client.send.assert_called_once_with(
            {
                "message": "pdn_list",
                "apn": "default",
                "pdn_type": "ipv4",
                "qci": 9,
                "priority_level": 15,
            }
        )

    def test_custom_apn_name(self, mock_client, mme):
        mme.set_default_apn(apn="internet")
        sent = mock_client.send.call_args[0][0]
        assert sent["apn"] == "internet"

    def test_with_ip_pool(self, mock_client, mme):
        mme.set_default_apn(
            apn="internet",
            first_ip="192.168.3.2",
            last_ip="192.168.3.254",
        )
        sent = mock_client.send.call_args[0][0]
        assert sent["first_ip_addr"] == "192.168.3.2"
        assert sent["last_ip_addr"] == "192.168.3.254"

    def test_with_dns_string(self, mock_client, mme):
        mme.set_default_apn(dns="8.8.8.8")
        sent = mock_client.send.call_args[0][0]
        assert sent["dns_addr"] == "8.8.8.8"

    def test_with_dns_list(self, mock_client, mme):
        mme.set_default_apn(dns=["8.8.8.8", "8.8.4.4"])
        sent = mock_client.send.call_args[0][0]
        assert sent["dns_addr"] == ["8.8.8.8", "8.8.4.4"]

    def test_ipv4v6_type(self, mock_client, mme):
        mme.set_default_apn(apn="ims", pdn_type="ipv4v6")
        sent = mock_client.send.call_args[0][0]
        assert sent["pdn_type"] == "ipv4v6"

    def test_custom_qos(self, mock_client, mme):
        mme.set_default_apn(apn="ims", qci=5, priority_level=1)
        sent = mock_client.send.call_args[0][0]
        assert sent["qci"] == 5
        assert sent["priority_level"] == 1

    def test_full_config(self, mock_client, mme):
        mme.set_default_apn(
            apn="internet",
            pdn_type="ipv4",
            first_ip="192.168.3.2",
            last_ip="192.168.3.254",
            dns="8.8.8.8",
            qci=9,
            priority_level=15,
        )
        mock_client.send.assert_called_once_with(
            {
                "message": "pdn_list",
                "apn": "internet",
                "pdn_type": "ipv4",
                "first_ip_addr": "192.168.3.2",
                "last_ip_addr": "192.168.3.254",
                "dns_addr": "8.8.8.8",
                "qci": 9,
                "priority_level": 15,
            }
        )
