"""eNB/gNB (base station) Remote API methods."""

from __future__ import annotations

from typing import Any

from .base import ServiceApi


class ENBApi(ServiceApi):
    """API for controlling an Amarisoft eNB/gNB via the Remote API.

    Provides methods for configuration, UE management, cell control,
    RRC procedures, RF settings, and PHY/MAC parameter tuning.

    Inherits common methods from :class:`ServiceApi`:
    ``config_get``, ``config_set``, ``stats``, ``ue_get``,
    ``log_get``, ``log_set``.
    """

    DEFAULT_PORT = 9001

    # ──────────────────────────────────────────────
    # Configuration (cell-level)
    # ──────────────────────────────────────────────

    def config_set_cell(self, cell_id: int, **params: Any) -> dict[str, Any]:
        """Set configuration parameters for a specific cell.

        Args:
            cell_id: Target cell identifier.
            **params: Cell-level parameters to set.

        Example::

            enb.config_set_cell(1, inactivity_timer=6000, pdsch_mcs=15)
        """
        return self._client.send(
            {
                "message": "config_set",
                "cells": {str(cell_id): params},
            }
        )

    # ──────────────────────────────────────────────
    # Statistics (override for extra params)
    # ──────────────────────────────────────────────

    def stats(
        self,
        samples: bool = False,
        rf: bool = False,
    ) -> dict[str, Any]:
        """Retrieve eNB/gNB statistics.

        Args:
            samples: Include sample-level statistics.
            rf: Include RF statistics.
        """
        msg: dict[str, Any] = {"message": "stats"}
        if samples:
            msg["samples"] = True
        if rf:
            msg["rf"] = True
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # UE / Bearer Queries
    # ──────────────────────────────────────────────

    def erab_get(self, **filters: Any) -> dict[str, Any]:
        """Get E-RAB (Evolved Radio Access Bearer) information.

        Args:
            **filters: Optional filters (e.g., enb_ue_id).
        """
        msg: dict[str, Any] = {"message": "erab_get"}
        msg.update(filters)
        return self._client.send(msg)

    def qos_flow_get(self, **filters: Any) -> dict[str, Any]:
        """Get QoS flow information (5G NR).

        Args:
            **filters: Optional filters.
        """
        msg: dict[str, Any] = {"message": "qos_flow_get"}
        msg.update(filters)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Cell Control
    # ──────────────────────────────────────────────

    def cell_gain(self, cell_id: int, gain: float) -> dict[str, Any]:
        """Adjust the gain of a specific cell.

        Args:
            cell_id: Target cell identifier.
            gain: Gain value in dB (can be negative).
        """
        return self._client.send(
            {
                "message": "cell_gain",
                "cell_id": cell_id,
                "gain": gain,
            }
        )

    def rrc_release(
        self,
        enb_ue_id: int,
        cause: str | None = None,
        redirect_freq: int | None = None,
    ) -> dict[str, Any]:
        """Release RRC connection for a UE.

        Args:
            enb_ue_id: The eNB UE identifier.
            cause: Release cause.
            redirect_freq: Redirect frequency (EARFCN).
        """
        msg: dict[str, Any] = {
            "message": "rrc_cnx_release",
            "enb_ue_id": enb_ue_id,
        }
        if cause is not None:
            msg["cause"] = cause
        if redirect_freq is not None:
            msg["redirect_freq"] = redirect_freq
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # RF Control
    # ──────────────────────────────────────────────

    def rf(
        self,
        tx_gain: float | None = None,
        rx_gain: float | None = None,
        rx_agc: bool | None = None,
    ) -> dict[str, Any]:
        """Manage RF parameters.

        Args:
            tx_gain: Transmit gain in dB.
            rx_gain: Receive gain in dB.
            rx_agc: Enable/disable automatic gain control.
        """
        msg: dict[str, Any] = {"message": "rf"}
        if tx_gain is not None:
            msg["tx_gain"] = tx_gain
        if rx_gain is not None:
            msg["rx_gain"] = rx_gain
        if rx_agc is not None:
            msg["rx_agc"] = rx_agc
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # RRC Procedures
    # ──────────────────────────────────────────────

    def rrc_cnx_release(self, enb_ue_id: int) -> dict[str, Any]:
        """Release the RRC connection for a UE.

        Args:
            enb_ue_id: The eNB UE identifier.
        """
        return self._client.send(
            {
                "message": "rrc_cnx_release",
                "enb_ue_id": enb_ue_id,
            }
        )

    def rrc_cnx_reconf(self, enb_ue_id: int, **params: Any) -> dict[str, Any]:
        """Trigger RRC connection reconfiguration.

        Args:
            enb_ue_id: The eNB UE identifier.
            **params: Reconfiguration parameters (e.g., dl_bwp_id, ul_bwp_id).
        """
        msg: dict[str, Any] = {
            "message": "rrc_cnx_reconf",
            "enb_ue_id": enb_ue_id,
        }
        msg.update(params)
        return self._client.send(msg)

    def rrc_ue_info_req(self, enb_ue_id: int, req_mask: int) -> dict[str, Any]:
        """Request UE information via RRC.

        Args:
            enb_ue_id: The eNB UE identifier.
            req_mask: Bitmask specifying requested information.
        """
        return self._client.send(
            {
                "message": "rrc_ue_info_req",
                "enb_ue_id": enb_ue_id,
                "req_mask": req_mask,
            }
        )

    def rrc_ue_cap_enquiry(self, enb_ue_id: int) -> dict[str, Any]:
        """Query UE radio capabilities.

        Args:
            enb_ue_id: The eNB UE identifier.
        """
        return self._client.send(
            {
                "message": "rrc_ue_cap_enquiry",
                "enb_ue_id": enb_ue_id,
            }
        )

    # ──────────────────────────────────────────────
    # Paging
    # ──────────────────────────────────────────────

    def page_ue(
        self,
        cell_ids: list[int],
        imsi: str,
        paging_type: str = "s1",
        cn_domain: str = "ps",
    ) -> dict[str, Any]:
        """Initiate UE paging.

        Args:
            cell_ids: List of cell identifiers to page on.
            imsi: IMSI of the target UE.
            paging_type: Paging type (``"s1"`` or ``"x2"``).
            cn_domain: Core network domain (``"ps"`` or ``"cs"``).
        """
        return self._client.send(
            {
                "message": "page_ue",
                "cell_id": cell_ids,
                "imsi": imsi,
                "type": paging_type,
                "cn_domain": cn_domain,
            }
        )

    # ──────────────────────────────────────────────
    # SIB (System Information Block)
    # ──────────────────────────────────────────────

    def sib_set(self, cell_id: int, sib_data: dict[str, Any]) -> dict[str, Any]:
        """Configure System Information Block parameters for a cell.

        Args:
            cell_id: Target cell identifier.
            sib_data: SIB configuration data.
        """
        return self._client.send(
            {
                "message": "sib_set",
                "cell_id": cell_id,
                **sib_data,
            }
        )

    # ──────────────────────────────────────────────
    # BWP (Bandwidth Part) - 5G NR
    # ──────────────────────────────────────────────

    def dci_bwp_switch(
        self,
        enb_ue_id: int,
        dl_bwp_id: int | None = None,
        ul_bwp_id: int | None = None,
    ) -> dict[str, Any]:
        """Switch BWP via DCI for a UE (5G NR).

        Args:
            enb_ue_id: The eNB/gNB UE identifier.
            dl_bwp_id: Downlink BWP ID to switch to.
            ul_bwp_id: Uplink BWP ID to switch to.
        """
        msg: dict[str, Any] = {
            "message": "dci_bwp_switch",
            "enb_ue_id": enb_ue_id,
        }
        if dl_bwp_id is not None:
            msg["dl_bwp_id"] = dl_bwp_id
        if ul_bwp_id is not None:
            msg["ul_bwp_id"] = ul_bwp_id
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Interface Control (S1/NG/X2/Xn)
    # ──────────────────────────────────────────────

    def s1_connect(self) -> dict[str, Any]:
        """Connect to the MME via S1 interface."""
        return self._client.send({"message": "s1connect"})

    def s1_disconnect(self) -> dict[str, Any]:
        """Disconnect from the MME via S1 interface."""
        return self._client.send({"message": "s1disconnect"})

    def ng_connect(self) -> dict[str, Any]:
        """Connect to the AMF via NG interface (5G)."""
        return self._client.send({"message": "ngconnect"})

    def ng_disconnect(self) -> dict[str, Any]:
        """Disconnect from the AMF via NG interface (5G)."""
        return self._client.send({"message": "ngdisconnect"})

    def x2_status(self) -> dict[str, Any]:
        """Query X2 interface status."""
        return self._client.send({"message": "x2"})

    def ng_status(self) -> dict[str, Any]:
        """Query NG interface status."""
        return self._client.send({"message": "ng"})

    def s1_status(self) -> dict[str, Any]:
        """Query S1 interface status."""
        return self._client.send({"message": "s1"})

    # ──────────────────────────────────────────────
    # PHY/MAC Configuration
    # ──────────────────────────────────────────────

    def set_dl_config(
        self,
        cell_id: int,
        *,
        pdsch_mcs: int | None = None,
        force_dl_schedule: bool | None = None,
        pdsch_fixed_rb_alloc: bool | None = None,
        pdsch_fixed_rb_start: int | None = None,
        pdsch_fixed_l_crb: int | None = None,
    ) -> dict[str, Any]:
        """Configure downlink PHY/MAC parameters for a cell.

        Args:
            cell_id: Target cell identifier.
            pdsch_mcs: Downlink modulation and coding scheme.
            force_dl_schedule: Force PDSCH scheduling every subframe.
            pdsch_fixed_rb_alloc: Enable fixed resource block allocation.
            pdsch_fixed_rb_start: Starting resource block position.
            pdsch_fixed_l_crb: Resource block allocation length.
        """
        params: dict[str, Any] = {}
        if pdsch_mcs is not None:
            params["pdsch_mcs"] = pdsch_mcs
        if force_dl_schedule is not None:
            params["force_dl_schedule"] = force_dl_schedule
        if pdsch_fixed_rb_alloc is not None:
            params["pdsch_fixed_rb_alloc"] = pdsch_fixed_rb_alloc
        if pdsch_fixed_rb_start is not None:
            params["pdsch_fixed_rb_start"] = pdsch_fixed_rb_start
        if pdsch_fixed_l_crb is not None:
            params["pdsch_fixed_l_crb"] = pdsch_fixed_l_crb
        return self.config_set_cell(cell_id, **params)

    def set_ul_config(
        self,
        cell_id: int,
        *,
        pusch_mcs: int | None = None,
        force_full_bsr: bool | None = None,
        pusch_fixed_rb_alloc: bool | None = None,
        pusch_fixed_rb_start: int | None = None,
        pusch_fixed_l_crb: int | None = None,
    ) -> dict[str, Any]:
        """Configure uplink PHY/MAC parameters for a cell.

        Args:
            cell_id: Target cell identifier.
            pusch_mcs: Uplink modulation and coding scheme.
            force_full_bsr: Trigger aggressive uplink grant scheduling.
            pusch_fixed_rb_alloc: Enable fixed UL resource block allocation.
            pusch_fixed_rb_start: Starting UL resource block position.
            pusch_fixed_l_crb: UL resource block allocation length.
        """
        params: dict[str, Any] = {}
        if pusch_mcs is not None:
            params["pusch_mcs"] = pusch_mcs
        if force_full_bsr is not None:
            params["force_full_bsr"] = force_full_bsr
        if pusch_fixed_rb_alloc is not None:
            params["pusch_fixed_rb_alloc"] = pusch_fixed_rb_alloc
        if pusch_fixed_rb_start is not None:
            params["pusch_fixed_rb_start"] = pusch_fixed_rb_start
        if pusch_fixed_l_crb is not None:
            params["pusch_fixed_l_crb"] = pusch_fixed_l_crb
        return self.config_set_cell(cell_id, **params)

    # ──────────────────────────────────────────────
    # PDCCH
    # ──────────────────────────────────────────────

    def pdcch_order_prach(self, enb_ue_id: int) -> dict[str, Any]:
        """Issue a PDCCH order to trigger PRACH from a UE.

        Args:
            enb_ue_id: The eNB UE identifier.
        """
        return self._client.send(
            {
                "message": "pdcch_order_prach",
                "enb_ue_id": enb_ue_id,
            }
        )

    # ──────────────────────────────────────────────
    # Bearer Management
    # ──────────────────────────────────────────────

    def ue_activate_dedicated_bearer(
        self,
        enb_ue_id: int,
        qci: int,
        **params: Any,
    ) -> dict[str, Any]:
        """Activate a dedicated bearer for a UE.

        Args:
            enb_ue_id: The eNB UE identifier.
            qci: QoS Class Identifier.
            **params: Additional bearer parameters (gbr, filters, etc.).
        """
        msg: dict[str, Any] = {
            "message": "ue_activate_dedicated_bearer",
            "enb_ue_id": enb_ue_id,
            "qci": qci,
        }
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Cell Control (Additional)
    # ──────────────────────────────────────────────

    def cell_ul_disable(
        self,
        cell_id: int,
        disable: bool = True,
    ) -> dict[str, Any]:
        """Disable/enable uplink for a cell.

        Args:
            cell_id: Target cell identifier.
            disable: True to disable UL, False to enable.
        """
        return self._client.send(
            {
                "message": "cell_ul_disable",
                "cell_id": cell_id,
                "disable": disable,
            }
        )

    def noise_level(
        self,
        cell_id: int | None = None,
        noise: float | None = None,
    ) -> dict[str, Any]:
        """Get or set the noise level for a cell.

        Args:
            cell_id: Target cell identifier.
            noise: Noise level in dB to set.
        """
        msg: dict[str, Any] = {"message": "noise_level"}
        if cell_id is not None:
            msg["cell_id"] = cell_id
        if noise is not None:
            msg["noise"] = noise
        return self._client.send(msg)

    def snr(
        self,
        enb_ue_id: int | None = None,
        cell_id: int | None = None,
    ) -> dict[str, Any]:
        """Get Signal-to-Noise Ratio information.

        Args:
            enb_ue_id: Filter by UE identifier.
            cell_id: Filter by cell identifier.
        """
        msg: dict[str, Any] = {"message": "snr"}
        if enb_ue_id is not None:
            msg["enb_ue_id"] = enb_ue_id
        if cell_id is not None:
            msg["cell_id"] = cell_id
        return self._client.send(msg)

    def scells_act_deact(
        self,
        enb_ue_id: int,
        scell_ids: list[int],
        activate: bool = True,
    ) -> dict[str, Any]:
        """Activate or deactivate secondary cells (carrier aggregation).

        Args:
            enb_ue_id: The eNB UE identifier.
            scell_ids: List of secondary cell IDs.
            activate: True to activate, False to deactivate.
        """
        return self._client.send(
            {
                "message": "scells_act_deact",
                "enb_ue_id": enb_ue_id,
                "scell_id": scell_ids,
                "activate": activate,
            }
        )

    # ──────────────────────────────────────────────
    # RF Control (Additional)
    # ──────────────────────────────────────────────

    def rf_gain(
        self,
        tx_gain: float | None = None,
        rx_gain: float | None = None,
    ) -> dict[str, Any]:
        """Get or set RF gain values.

        Args:
            tx_gain: Transmit gain in dB.
            rx_gain: Receive gain in dB.
        """
        msg: dict[str, Any] = {"message": "rf_gain"}
        if tx_gain is not None:
            msg["tx_gain"] = tx_gain
        if rx_gain is not None:
            msg["rx_gain"] = rx_gain
        return self._client.send(msg)

    def rf_power(
        self,
        cell_id: int | None = None,
    ) -> dict[str, Any]:
        """Get RF power information.

        Args:
            cell_id: Filter by cell identifier.
        """
        msg: dict[str, Any] = {"message": "rf_power"}
        if cell_id is not None:
            msg["cell_id"] = cell_id
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Handover / Mobility
    # ──────────────────────────────────────────────

    def handover(
        self,
        enb_ue_id: int,
        target_cell_id: int,
        **params: Any,
    ) -> dict[str, Any]:
        """Initiate handover for a UE.

        Args:
            enb_ue_id: The eNB UE identifier.
            target_cell_id: Target cell ID for handover.
            **params: Additional handover parameters.
        """
        msg: dict[str, Any] = {
            "message": "handover",
            "enb_ue_id": enb_ue_id,
            "target_cell_id": target_cell_id,
        }
        msg.update(params)
        return self._client.send(msg)

    def nr_pscell_change(
        self,
        enb_ue_id: int,
        target_cell_id: int,
        **params: Any,
    ) -> dict[str, Any]:
        """Change PSCell for NR (5G) UE.

        Args:
            enb_ue_id: The gNB UE identifier.
            target_cell_id: Target PSCell ID.
            **params: Additional parameters.
        """
        msg: dict[str, Any] = {
            "message": "nr_pscell_change",
            "enb_ue_id": enb_ue_id,
            "target_cell_id": target_cell_id,
        }
        msg.update(params)
        return self._client.send(msg)

    def mr_dc_scg_release(
        self,
        enb_ue_id: int,
    ) -> dict[str, Any]:
        """Release SCG (Secondary Cell Group) for MR-DC UE.

        Args:
            enb_ue_id: The eNB UE identifier.
        """
        return self._client.send(
            {
                "message": "mr_dc_scg_release",
                "enb_ue_id": enb_ue_id,
            }
        )

    def mr_dc_split_dl_ratio_change(
        self,
        enb_ue_id: int,
        ratio: int,
    ) -> dict[str, Any]:
        """Change DL split ratio for MR-DC UE.

        Args:
            enb_ue_id: The eNB UE identifier.
            ratio: Split ratio percentage (0-100).
        """
        return self._client.send(
            {
                "message": "mr_dc_split_dl_ratio_change",
                "enb_ue_id": enb_ue_id,
                "ratio": ratio,
            }
        )

    # ──────────────────────────────────────────────
    # Neighbor Cell Management
    # ──────────────────────────────────────────────

    def ncell_list_add(
        self,
        cell_id: int,
        ncell: dict[str, Any],
    ) -> dict[str, Any]:
        """Add a neighbor cell to the neighbor list.

        Args:
            cell_id: Source cell identifier.
            ncell: Neighbor cell configuration.
        """
        return self._client.send(
            {
                "message": "ncell_list_add",
                "cell_id": cell_id,
                "ncell": ncell,
            }
        )

    def ncell_list_del(
        self,
        cell_id: int,
        ncell_id: int,
    ) -> dict[str, Any]:
        """Remove a neighbor cell from the neighbor list.

        Args:
            cell_id: Source cell identifier.
            ncell_id: Neighbor cell identifier to remove.
        """
        return self._client.send(
            {
                "message": "ncell_list_del",
                "cell_id": cell_id,
                "ncell_id": ncell_id,
            }
        )

    # ──────────────────────────────────────────────
    # X2 Interface
    # ──────────────────────────────────────────────

    def x2_connect(self, peer_addr: str | None = None) -> dict[str, Any]:
        """Connect to peer eNB via X2 interface.

        Args:
            peer_addr: Peer eNB address (optional).
        """
        msg: dict[str, Any] = {"message": "x2connect"}
        if peer_addr is not None:
            msg["peer_addr"] = peer_addr
        return self._client.send(msg)

    def x2_disconnect(self, peer_addr: str | None = None) -> dict[str, Any]:
        """Disconnect from peer eNB via X2 interface.

        Args:
            peer_addr: Peer eNB address (optional).
        """
        msg: dict[str, Any] = {"message": "x2disconnect"}
        if peer_addr is not None:
            msg["peer_addr"] = peer_addr
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Xn Interface (5G)
    # ──────────────────────────────────────────────

    def xn_status(self) -> dict[str, Any]:
        """Query Xn interface status."""
        return self._client.send({"message": "xn"})

    def xn_connect(self, peer_addr: str | None = None) -> dict[str, Any]:
        """Connect to peer gNB via Xn interface.

        Args:
            peer_addr: Peer gNB address (optional).
        """
        msg: dict[str, Any] = {"message": "xnconnect"}
        if peer_addr is not None:
            msg["peer_addr"] = peer_addr
        return self._client.send(msg)

    def xn_disconnect(self, peer_addr: str | None = None) -> dict[str, Any]:
        """Disconnect from peer gNB via Xn interface.

        Args:
            peer_addr: Peer gNB address (optional).
        """
        msg: dict[str, Any] = {"message": "xndisconnect"}
        if peer_addr is not None:
            msg["peer_addr"] = peer_addr
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # S1 Interface (Additional)
    # ──────────────────────────────────────────────

    def s1_add(
        self,
        mme_addr: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Add an MME to S1 interface.

        Args:
            mme_addr: MME IP address.
            **params: Additional MME parameters.
        """
        msg: dict[str, Any] = {
            "message": "s1add",
            "mme_addr": mme_addr,
        }
        msg.update(params)
        return self._client.send(msg)

    def s1_delete(
        self,
        mme_addr: str,
    ) -> dict[str, Any]:
        """Remove an MME from S1 interface.

        Args:
            mme_addr: MME IP address to remove.
        """
        return self._client.send(
            {
                "message": "s1delete",
                "mme_addr": mme_addr,
            }
        )

    def s1_reset(
        self,
        mme_addr: str | None = None,
    ) -> dict[str, Any]:
        """Reset S1 interface.

        Args:
            mme_addr: Specific MME to reset (optional).
        """
        msg: dict[str, Any] = {"message": "s1_reset"}
        if mme_addr is not None:
            msg["mme_addr"] = mme_addr
        return self._client.send(msg)

    def s1_enb_config_upd(self) -> dict[str, Any]:
        """Send eNB Configuration Update to MME."""
        return self._client.send({"message": "s1_enb_config_upd"})

    # ──────────────────────────────────────────────
    # NG Interface (Additional)
    # ──────────────────────────────────────────────

    def ng_add(
        self,
        amf_addr: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Add an AMF to NG interface.

        Args:
            amf_addr: AMF IP address.
            **params: Additional AMF parameters.
        """
        msg: dict[str, Any] = {
            "message": "ngadd",
            "amf_addr": amf_addr,
        }
        msg.update(params)
        return self._client.send(msg)

    def ng_delete(
        self,
        amf_addr: str,
    ) -> dict[str, Any]:
        """Remove an AMF from NG interface.

        Args:
            amf_addr: AMF IP address to remove.
        """
        return self._client.send(
            {
                "message": "ngdelete",
                "amf_addr": amf_addr,
            }
        )

    # ──────────────────────────────────────────────
    # M2 Interface (MBMS)
    # ──────────────────────────────────────────────

    def m2_status(self) -> dict[str, Any]:
        """Query M2 interface status (MBMS)."""
        return self._client.send({"message": "m2"})

    def m2_connect(self) -> dict[str, Any]:
        """Connect to MCE via M2 interface."""
        return self._client.send({"message": "m2connect"})

    def m2_disconnect(self) -> dict[str, Any]:
        """Disconnect from MCE via M2 interface."""
        return self._client.send({"message": "m2disconnect"})

    # ──────────────────────────────────────────────
    # SIB (Additional)
    # ──────────────────────────────────────────────

    def sib14(
        self,
        cell_id: int,
        enable: bool = True,
    ) -> dict[str, Any]:
        """Enable/disable SIB14 (ETWS/CMAS) for a cell.

        Args:
            cell_id: Target cell identifier.
            enable: True to enable, False to disable.
        """
        return self._client.send(
            {
                "message": "sib14",
                "cell_id": cell_id,
                "enable": enable,
            }
        )

    # ──────────────────────────────────────────────
    # Utility Commands
    # ──────────────────────────────────────────────

    def cancel(self, message_id: int) -> dict[str, Any]:
        """Cancel a pending asynchronous operation.

        Args:
            message_id: ID of the message to cancel.
        """
        return self._client.send(
            {
                "message": "cancel",
                "message_id": message_id,
            }
        )

    def echo(self, data: Any = None) -> dict[str, Any]:
        """Echo test command.

        Args:
            data: Data to echo back.
        """
        msg: dict[str, Any] = {"message": "echo"}
        if data is not None:
            msg["data"] = data
        return self._client.send(msg)

    def monitor(self, **params: Any) -> dict[str, Any]:
        """Enable/disable event monitoring.

        Args:
            **params: Monitor parameters (events to monitor).
        """
        msg: dict[str, Any] = {"message": "monitor"}
        msg.update(params)
        return self._client.send(msg)

    def quit(self) -> dict[str, Any]:
        """Terminate the eNB/gNB process."""
        return self._client.send({"message": "quit"})

    # ──────────────────────────────────────────────
    # Command Execution
    # ──────────────────────────────────────────────

    def cmd(self, command: str, **params: Any) -> dict[str, Any]:
        """Execute a shell command on the eNB/gNB.

        Args:
            command: Command string to execute.
            **params: Additional parameters.
        """
        msg: dict[str, Any] = {"message": "cmd", "command": command}
        msg.update(params)
        return self._client.send(msg)

    def register(self, **params: Any) -> dict[str, Any]:
        """Register for event notifications.

        Args:
            **params: Registration parameters.
        """
        msg: dict[str, Any] = {"message": "register"}
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # KPI / Logging (Additional)
    # ──────────────────────────────────────────────

    def kpi_get(self, **params: Any) -> dict[str, Any]:
        """Get Key Performance Indicators.

        Args:
            **params: Optional filter parameters.
        """
        msg: dict[str, Any] = {"message": "kpi_get"}
        msg.update(params)
        return self._client.send(msg)

    def log_bin_get(
        self,
        min_: int | None = None,
        max_: int | None = None,
    ) -> dict[str, Any]:
        """Get binary log data.

        Args:
            min_: Minimum log index.
            max_: Maximum log index.
        """
        msg: dict[str, Any] = {"message": "log_bin_get"}
        if min_ is not None:
            msg["min"] = min_
        if max_ is not None:
            msg["max"] = max_
        return self._client.send(msg)

    def log_reset(self) -> dict[str, Any]:
        """Reset the log buffer."""
        return self._client.send({"message": "log_reset"})

    # ──────────────────────────────────────────────
    # EN-DC / Dual Connectivity
    # ──────────────────────────────────────────────

    def en_dc_split_dl_ratio_change(
        self,
        enb_ue_id: int,
        ratio: int,
    ) -> dict[str, Any]:
        """Change DL split ratio for EN-DC UE.

        Args:
            enb_ue_id: The eNB UE identifier.
            ratio: Split ratio percentage (0-100).
        """
        return self._client.send(
            {
                "message": "en_dc_split_dl_ratio_change",
                "enb_ue_id": enb_ue_id,
                "ratio": ratio,
            }
        )

    # ──────────────────────────────────────────────
    # PWS (Public Warning System)
    # ──────────────────────────────────────────────

    def enb_pws_failure(self, cell_id: int | None = None) -> dict[str, Any]:
        """Simulate PWS failure on eNB.

        Args:
            cell_id: Target cell identifier (optional).
        """
        msg: dict[str, Any] = {"message": "enb_pws_failure"}
        if cell_id is not None:
            msg["cell_id"] = cell_id
        return self._client.send(msg)

    def enb_pws_restart(self, cell_id: int | None = None) -> dict[str, Any]:
        """Restart PWS on eNB.

        Args:
            cell_id: Target cell identifier (optional).
        """
        msg: dict[str, Any] = {"message": "enb_pws_restart"}
        if cell_id is not None:
            msg["cell_id"] = cell_id
        return self._client.send(msg)

    def gnb_pws_failure(self, cell_id: int | None = None) -> dict[str, Any]:
        """Simulate PWS failure on gNB.

        Args:
            cell_id: Target cell identifier (optional).
        """
        msg: dict[str, Any] = {"message": "gnb_pws_failure"}
        if cell_id is not None:
            msg["cell_id"] = cell_id
        return self._client.send(msg)

    def gnb_pws_restart(self, cell_id: int | None = None) -> dict[str, Any]:
        """Restart PWS on gNB.

        Args:
            cell_id: Target cell identifier (optional).
        """
        msg: dict[str, Any] = {"message": "gnb_pws_restart"}
        if cell_id is not None:
            msg["cell_id"] = cell_id
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # NTN (Non-Terrestrial Network)
    # ──────────────────────────────────────────────

    def ntn_satellite_update(self, **params: Any) -> dict[str, Any]:
        """Update NTN satellite parameters.

        Args:
            **params: Satellite configuration parameters.
        """
        msg: dict[str, Any] = {"message": "ntn_satellite_update"}
        msg.update(params)
        return self._client.send(msg)

    def ntn_sv_file_update(self, filename: str | None = None) -> dict[str, Any]:
        """Update NTN state vector file.

        Args:
            filename: Path to state vector file.
        """
        msg: dict[str, Any] = {"message": "ntn_sv_file_update"}
        if filename is not None:
            msg["filename"] = filename
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # TRX (Transceiver)
    # ──────────────────────────────────────────────

    def trx(self, **params: Any) -> dict[str, Any]:
        """Get or set TRX (transceiver) parameters.

        Args:
            **params: TRX configuration parameters.
        """
        msg: dict[str, Any] = {"message": "trx"}
        msg.update(params)
        return self._client.send(msg)

    def trx_iq_dump(
        self,
        filename: str,
        duration: float | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Dump IQ samples to file.

        Args:
            filename: Output filename for IQ dump.
            duration: Duration in seconds.
            **params: Additional dump parameters.
        """
        msg: dict[str, Any] = {"message": "trx_iq_dump", "filename": filename}
        if duration is not None:
            msg["duration"] = duration
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Cell List
    # ──────────────────────────────────────────────

    def cell_list(self) -> dict[str, Any]:
        """Get list of configured cells.

        Note: This may not be supported on all Amarisoft versions.
        Falls back to extracting from config_get if not available.
        """
        return self._client.send({"message": "cell_list"})
