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
    # System
    # ──────────────────────────────────────────────

    def system_info(self) -> dict[str, Any]:
        """Retrieve overall system status of the eNB/gNB."""
        return self._client.send({"message": "system_info"})

    # ──────────────────────────────────────────────
    # Configuration (cell-level)
    # ──────────────────────────────────────────────

    def config_set_cell(
        self, cell_id: int, **params: Any
    ) -> dict[str, Any]:
        """Set configuration parameters for a specific cell.

        Args:
            cell_id: Target cell identifier.
            **params: Cell-level parameters to set.

        Example::

            enb.config_set_cell(1, inactivity_timer=6000, pdsch_mcs=15)
        """
        return self._client.send({
            "message": "config_set",
            "cells": {str(cell_id): params},
        })

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
        return self._client.send({
            "message": "cell_gain",
            "cell_id": cell_id,
            "gain": gain,
        })

    def cell_list(self) -> dict[str, Any]:
        """List all configured cells and their status."""
        return self._client.send({"message": "cell_list"})

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
        return self._client.send({
            "message": "rrc_cnx_release",
            "enb_ue_id": enb_ue_id,
        })

    def rrc_cnx_reconf(
        self, enb_ue_id: int, **params: Any
    ) -> dict[str, Any]:
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

    def rrc_ue_info_req(
        self, enb_ue_id: int, req_mask: int
    ) -> dict[str, Any]:
        """Request UE information via RRC.

        Args:
            enb_ue_id: The eNB UE identifier.
            req_mask: Bitmask specifying requested information.
        """
        return self._client.send({
            "message": "rrc_ue_info_req",
            "enb_ue_id": enb_ue_id,
            "req_mask": req_mask,
        })

    def rrc_ue_cap_enquiry(self, enb_ue_id: int) -> dict[str, Any]:
        """Query UE radio capabilities.

        Args:
            enb_ue_id: The eNB UE identifier.
        """
        return self._client.send({
            "message": "rrc_ue_cap_enquiry",
            "enb_ue_id": enb_ue_id,
        })

    def rrc_procedure_filter(self, **params: Any) -> dict[str, Any]:
        """Control RRC procedure rejection filters.

        Args:
            **params: Filter parameters.
        """
        msg: dict[str, Any] = {"message": "rrc_procedure_filter"}
        msg.update(params)
        return self._client.send(msg)

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
        return self._client.send({
            "message": "page_ue",
            "cell_id": cell_ids,
            "imsi": imsi,
            "type": paging_type,
            "cn_domain": cn_domain,
        })

    # ──────────────────────────────────────────────
    # SIB (System Information Block)
    # ──────────────────────────────────────────────

    def sib_set(
        self, cell_id: int, sib_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Configure System Information Block parameters for a cell.

        Args:
            cell_id: Target cell identifier.
            sib_data: SIB configuration data.
        """
        return self._client.send({
            "message": "sib_set",
            "cell_id": cell_id,
            **sib_data,
        })

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
    # IQ Dump / Constellation
    # ──────────────────────────────────────────────

    def trx_iq_dump(
        self,
        duration: float,
        rx_filename: str | None = None,
        tx_filename: str | None = None,
    ) -> dict[str, Any]:
        """Capture IQ samples for analysis.

        Args:
            duration: Capture duration in seconds.
            rx_filename: Path to save RX IQ samples.
            tx_filename: Path to save TX IQ samples.
        """
        msg: dict[str, Any] = {
            "message": "trx_iq_dump",
            "duration": duration,
        }
        if rx_filename is not None:
            msg["rx_filename"] = rx_filename
        if tx_filename is not None:
            msg["tx_filename"] = tx_filename
        return self._client.send(msg)

    def register_channel(self, channel: str) -> dict[str, Any]:
        """Register to receive constellation data for a PHY channel.

        Args:
            channel: Channel name (e.g., ``"pusch"``, ``"srs"``).
        """
        return self._client.send({
            "message": "register",
            "register": channel,
        })

    def unregister_channel(self, channel: str) -> dict[str, Any]:
        """Stop receiving constellation data for a PHY channel.

        Args:
            channel: Channel name to unregister.
        """
        return self._client.send({
            "message": "register",
            "register": channel,
            "enable": False,
        })

    # ──────────────────────────────────────────────
    # PDCCH
    # ──────────────────────────────────────────────

    def pdcch_order_prach(self, enb_ue_id: int) -> dict[str, Any]:
        """Issue a PDCCH order to trigger PRACH from a UE.

        Args:
            enb_ue_id: The eNB UE identifier.
        """
        return self._client.send({
            "message": "pdcch_order_prach",
            "enb_ue_id": enb_ue_id,
        })

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
