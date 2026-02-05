"""Tests for ENBApi-specific methods."""

from __future__ import annotations


class TestSystemInfo:
    def test_sends_system_info(self, mock_client, enb):
        enb.system_info()
        mock_client.send.assert_called_once_with({"message": "system_info"})


class TestConfigSetCell:
    def test_sends_config_set_cell(self, mock_client, enb):
        enb.config_set_cell(1, pdsch_mcs=15)
        mock_client.send.assert_called_once_with({
            "message": "config_set",
            "cells": {"1": {"pdsch_mcs": 15}},
        })


class TestStatsOverride:
    def test_stats_default(self, mock_client, enb):
        enb.stats()
        mock_client.send.assert_called_once_with({"message": "stats"})

    def test_stats_with_samples(self, mock_client, enb):
        enb.stats(samples=True)
        mock_client.send.assert_called_once_with(
            {"message": "stats", "samples": True}
        )

    def test_stats_with_rf(self, mock_client, enb):
        enb.stats(rf=True)
        mock_client.send.assert_called_once_with(
            {"message": "stats", "rf": True}
        )

    def test_stats_with_both(self, mock_client, enb):
        enb.stats(samples=True, rf=True)
        mock_client.send.assert_called_once_with(
            {"message": "stats", "samples": True, "rf": True}
        )


class TestErabGet:
    def test_basic(self, mock_client, enb):
        enb.erab_get()
        mock_client.send.assert_called_once_with({"message": "erab_get"})

    def test_with_filter(self, mock_client, enb):
        enb.erab_get(enb_ue_id=5)
        mock_client.send.assert_called_once_with(
            {"message": "erab_get", "enb_ue_id": 5}
        )


class TestQosFlowGet:
    def test_basic(self, mock_client, enb):
        enb.qos_flow_get()
        mock_client.send.assert_called_once_with({"message": "qos_flow_get"})


class TestCellGain:
    def test_sends_cell_gain(self, mock_client, enb):
        enb.cell_gain(cell_id=1, gain=-10)
        mock_client.send.assert_called_once_with({
            "message": "cell_gain",
            "cell_id": 1,
            "gain": -10,
        })


class TestCellList:
    def test_sends_cell_list(self, mock_client, enb):
        enb.cell_list()
        mock_client.send.assert_called_once_with({"message": "cell_list"})


class TestRf:
    def test_rf_no_params(self, mock_client, enb):
        enb.rf()
        mock_client.send.assert_called_once_with({"message": "rf"})

    def test_rf_tx_gain(self, mock_client, enb):
        enb.rf(tx_gain=20.0)
        mock_client.send.assert_called_once_with(
            {"message": "rf", "tx_gain": 20.0}
        )

    def test_rf_rx_gain(self, mock_client, enb):
        enb.rf(rx_gain=30.0)
        mock_client.send.assert_called_once_with(
            {"message": "rf", "rx_gain": 30.0}
        )

    def test_rf_rx_agc(self, mock_client, enb):
        enb.rf(rx_agc=True)
        mock_client.send.assert_called_once_with(
            {"message": "rf", "rx_agc": True}
        )

    def test_rf_all_params(self, mock_client, enb):
        enb.rf(tx_gain=10, rx_gain=20, rx_agc=False)
        mock_client.send.assert_called_once_with({
            "message": "rf",
            "tx_gain": 10,
            "rx_gain": 20,
            "rx_agc": False,
        })


class TestRrcCnxRelease:
    def test_sends_rrc_cnx_release(self, mock_client, enb):
        enb.rrc_cnx_release(42)
        mock_client.send.assert_called_once_with({
            "message": "rrc_cnx_release",
            "enb_ue_id": 42,
        })


class TestRrcCnxReconf:
    def test_sends_rrc_cnx_reconf(self, mock_client, enb):
        enb.rrc_cnx_reconf(42, dl_bwp_id=1)
        mock_client.send.assert_called_once_with({
            "message": "rrc_cnx_reconf",
            "enb_ue_id": 42,
            "dl_bwp_id": 1,
        })


class TestRrcUeInfoReq:
    def test_sends_rrc_ue_info_req(self, mock_client, enb):
        enb.rrc_ue_info_req(42, req_mask=3)
        mock_client.send.assert_called_once_with({
            "message": "rrc_ue_info_req",
            "enb_ue_id": 42,
            "req_mask": 3,
        })


class TestRrcUeCapEnquiry:
    def test_sends_rrc_ue_cap_enquiry(self, mock_client, enb):
        enb.rrc_ue_cap_enquiry(42)
        mock_client.send.assert_called_once_with({
            "message": "rrc_ue_cap_enquiry",
            "enb_ue_id": 42,
        })


class TestRrcProcedureFilter:
    def test_sends_rrc_procedure_filter(self, mock_client, enb):
        enb.rrc_procedure_filter(reject=True)
        mock_client.send.assert_called_once_with({
            "message": "rrc_procedure_filter",
            "reject": True,
        })


class TestPageUe:
    def test_sends_page_ue(self, mock_client, enb):
        enb.page_ue(cell_ids=[1, 2], imsi="001010000000001")
        mock_client.send.assert_called_once_with({
            "message": "page_ue",
            "cell_id": [1, 2],
            "imsi": "001010000000001",
            "type": "s1",
            "cn_domain": "ps",
        })


class TestSibSet:
    def test_sends_sib_set(self, mock_client, enb):
        enb.sib_set(1, {"sib1": {"tac": 1}})
        mock_client.send.assert_called_once_with({
            "message": "sib_set",
            "cell_id": 1,
            "sib1": {"tac": 1},
        })


class TestDciBwpSwitch:
    def test_sends_with_dl_bwp(self, mock_client, enb):
        enb.dci_bwp_switch(42, dl_bwp_id=2)
        mock_client.send.assert_called_once_with({
            "message": "dci_bwp_switch",
            "enb_ue_id": 42,
            "dl_bwp_id": 2,
        })

    def test_sends_with_both_bwp(self, mock_client, enb):
        enb.dci_bwp_switch(42, dl_bwp_id=2, ul_bwp_id=3)
        mock_client.send.assert_called_once_with({
            "message": "dci_bwp_switch",
            "enb_ue_id": 42,
            "dl_bwp_id": 2,
            "ul_bwp_id": 3,
        })

    def test_sends_minimal(self, mock_client, enb):
        enb.dci_bwp_switch(42)
        mock_client.send.assert_called_once_with({
            "message": "dci_bwp_switch",
            "enb_ue_id": 42,
        })


class TestS1Connect:
    def test_sends(self, mock_client, enb):
        enb.s1_connect()
        mock_client.send.assert_called_once_with({"message": "s1connect"})


class TestS1Disconnect:
    def test_sends(self, mock_client, enb):
        enb.s1_disconnect()
        mock_client.send.assert_called_once_with({"message": "s1disconnect"})


class TestNgConnect:
    def test_sends(self, mock_client, enb):
        enb.ng_connect()
        mock_client.send.assert_called_once_with({"message": "ngconnect"})


class TestNgDisconnect:
    def test_sends(self, mock_client, enb):
        enb.ng_disconnect()
        mock_client.send.assert_called_once_with({"message": "ngdisconnect"})


class TestX2Status:
    def test_sends(self, mock_client, enb):
        enb.x2_status()
        mock_client.send.assert_called_once_with({"message": "x2"})


class TestNgStatus:
    def test_sends(self, mock_client, enb):
        enb.ng_status()
        mock_client.send.assert_called_once_with({"message": "ng"})


class TestS1Status:
    def test_sends(self, mock_client, enb):
        enb.s1_status()
        mock_client.send.assert_called_once_with({"message": "s1"})


class TestSetDlConfig:
    def test_sends_with_pdsch_mcs(self, mock_client, enb):
        enb.set_dl_config(1, pdsch_mcs=15)
        mock_client.send.assert_called_once_with({
            "message": "config_set",
            "cells": {"1": {"pdsch_mcs": 15}},
        })

    def test_sends_with_all_params(self, mock_client, enb):
        enb.set_dl_config(
            1,
            pdsch_mcs=15,
            force_dl_schedule=True,
            pdsch_fixed_rb_alloc=True,
            pdsch_fixed_rb_start=0,
            pdsch_fixed_l_crb=10,
        )
        mock_client.send.assert_called_once_with({
            "message": "config_set",
            "cells": {
                "1": {
                    "pdsch_mcs": 15,
                    "force_dl_schedule": True,
                    "pdsch_fixed_rb_alloc": True,
                    "pdsch_fixed_rb_start": 0,
                    "pdsch_fixed_l_crb": 10,
                }
            },
        })


class TestSetUlConfig:
    def test_sends_with_pusch_mcs(self, mock_client, enb):
        enb.set_ul_config(1, pusch_mcs=10)
        mock_client.send.assert_called_once_with({
            "message": "config_set",
            "cells": {"1": {"pusch_mcs": 10}},
        })

    def test_sends_with_all_params(self, mock_client, enb):
        enb.set_ul_config(
            1,
            pusch_mcs=10,
            force_full_bsr=True,
            pusch_fixed_rb_alloc=True,
            pusch_fixed_rb_start=5,
            pusch_fixed_l_crb=20,
        )
        mock_client.send.assert_called_once_with({
            "message": "config_set",
            "cells": {
                "1": {
                    "pusch_mcs": 10,
                    "force_full_bsr": True,
                    "pusch_fixed_rb_alloc": True,
                    "pusch_fixed_rb_start": 5,
                    "pusch_fixed_l_crb": 20,
                }
            },
        })


class TestTrxIqDump:
    def test_minimal(self, mock_client, enb):
        enb.trx_iq_dump(duration=1.0)
        mock_client.send.assert_called_once_with({
            "message": "trx_iq_dump",
            "duration": 1.0,
        })

    def test_with_filenames(self, mock_client, enb):
        enb.trx_iq_dump(1.0, rx_filename="/tmp/rx.bin", tx_filename="/tmp/tx.bin")
        mock_client.send.assert_called_once_with({
            "message": "trx_iq_dump",
            "duration": 1.0,
            "rx_filename": "/tmp/rx.bin",
            "tx_filename": "/tmp/tx.bin",
        })


class TestRegisterChannel:
    def test_sends(self, mock_client, enb):
        enb.register_channel("pusch")
        mock_client.send.assert_called_once_with({
            "message": "register",
            "register": "pusch",
        })


class TestUnregisterChannel:
    def test_sends(self, mock_client, enb):
        enb.unregister_channel("pusch")
        mock_client.send.assert_called_once_with({
            "message": "register",
            "register": "pusch",
            "enable": False,
        })


class TestPdcchOrderPrach:
    def test_sends(self, mock_client, enb):
        enb.pdcch_order_prach(42)
        mock_client.send.assert_called_once_with({
            "message": "pdcch_order_prach",
            "enb_ue_id": 42,
        })


class TestUeActivateDedicatedBearer:
    def test_minimal(self, mock_client, enb):
        enb.ue_activate_dedicated_bearer(42, qci=5)
        mock_client.send.assert_called_once_with({
            "message": "ue_activate_dedicated_bearer",
            "enb_ue_id": 42,
            "qci": 5,
        })

    def test_with_extra_params(self, mock_client, enb):
        enb.ue_activate_dedicated_bearer(42, qci=5, gbr={"dl_gbr": 128})
        mock_client.send.assert_called_once_with({
            "message": "ue_activate_dedicated_bearer",
            "enb_ue_id": 42,
            "qci": 5,
            "gbr": {"dl_gbr": 128},
        })
