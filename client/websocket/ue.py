"""UE Simulator Remote API methods."""

from __future__ import annotations

from typing import Any

from .base import ServiceApi


class UEApi(ServiceApi):
    """API for controlling an Amarisoft UE Simulator via the Remote API.

    Provides methods for managing simulated UEs, controlling their state,
    and performing test procedures.

    Inherits common methods from :class:`ServiceApi`:
    ``config_get``, ``config_set``, ``stats``, ``ue_get``,
    ``log_get``, ``log_set``, ``help``.

    Remote API Commands Summary:
        - Power Control: power_on, power_off
        - UE State: ue_get, ue_add, ue_del, ue_set
        - Registration: register, deregister
        - PDN/PDU Sessions: pdn_connect, pdn_disconnect, pdu_session_establish,
          pdu_session_release, pdu_session_modify
        - Bearers: ue_activate_dedicated_bearer, ue_deactivate_dedicated_bearer,
          ue_modify_dedicated_bearer
        - Data: data_start, data_stop
        - Voice/IMS: mo_call, mt_call_answer, call_release, send_sms
        - Mobility: cell_reselection, handover_trigger
        - NR Specific: ue_assistance_information, rrc_release_request
        - Utility: cancel, echo, monitor, quit
    """

    DEFAULT_PORT = 9003

    # ──────────────────────────────────────────────
    # UE Power Control
    # ──────────────────────────────────────────────

    def power_on(self, ue_id: int | None = None) -> dict[str, Any]:
        """Power on a simulated UE.

        Args:
            ue_id: Specific UE to power on. ``None`` for all UEs.

        Returns:
            Power on confirmation.
        """
        msg: dict[str, Any] = {"message": "power_on"}
        if ue_id is not None:
            msg["ue_id"] = ue_id
        return self._client.send(msg)

    def power_off(self, ue_id: int | None = None) -> dict[str, Any]:
        """Power off a simulated UE.

        Args:
            ue_id: Specific UE to power off. ``None`` for all UEs.

        Returns:
            Power off confirmation.
        """
        msg: dict[str, Any] = {"message": "power_off"}
        if ue_id is not None:
            msg["ue_id"] = ue_id
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # UE Management
    # ──────────────────────────────────────────────

    def ue_add(
        self,
        imsi: str,
        k: str | None = None,
        opc: str | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Add a new simulated UE.

        Args:
            imsi: IMSI for the new UE.
            k: Authentication key (hex string).
            opc: Operator variant key (hex string).
            **params: Additional UE parameters (imei, msisdn, etc.).

        Returns:
            UE creation confirmation with assigned ue_id.
        """
        msg: dict[str, Any] = {"message": "ue_add", "imsi": imsi}
        if k is not None:
            msg["k"] = k
        if opc is not None:
            msg["opc"] = opc
        msg.update(params)
        return self._client.send(msg)

    def ue_del(self, ue_id: int) -> dict[str, Any]:
        """Delete a simulated UE.

        Args:
            ue_id: UE identifier to delete.

        Returns:
            Deletion confirmation.
        """
        return self._client.send({"message": "ue_del", "ue_id": ue_id})

    def ue_set(self, ue_id: int, **params: Any) -> dict[str, Any]:
        """Set parameters for a simulated UE.

        Args:
            ue_id: Target UE identifier.
            **params: Parameters to set (imsi, k, opc, etc.).

        Returns:
            Update confirmation.
        """
        msg: dict[str, Any] = {"message": "ue_set", "ue_id": ue_id}
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Registration Control
    # ──────────────────────────────────────────────

    def register(
        self,
        ue_id: int | None = None,
        registration_type: str | None = None,
    ) -> dict[str, Any]:
        """Trigger UE registration/attach.

        Args:
            ue_id: Specific UE to register. ``None`` for all UEs.
            registration_type: Registration type for 5G (initial, mobility, periodic).

        Returns:
            Registration request confirmation.
        """
        msg: dict[str, Any] = {"message": "register"}
        if ue_id is not None:
            msg["ue_id"] = ue_id
        if registration_type is not None:
            msg["registration_type"] = registration_type
        return self._client.send(msg)

    def deregister(
        self,
        ue_id: int | None = None,
        switch_off: bool = False,
    ) -> dict[str, Any]:
        """Trigger UE deregistration/detach.

        Args:
            ue_id: Specific UE to deregister. ``None`` for all UEs.
            switch_off: If True, indicates switch-off detach.

        Returns:
            Deregistration request confirmation.
        """
        msg: dict[str, Any] = {"message": "deregister"}
        if ue_id is not None:
            msg["ue_id"] = ue_id
        if switch_off:
            msg["switch_off"] = True
        return self._client.send(msg)

    def attach(self, ue_id: int | None = None) -> dict[str, Any]:
        """Trigger LTE attach procedure.

        Args:
            ue_id: Specific UE to attach. ``None`` for all UEs.

        Returns:
            Attach request confirmation.
        """
        msg: dict[str, Any] = {"message": "attach"}
        if ue_id is not None:
            msg["ue_id"] = ue_id
        return self._client.send(msg)

    def detach(
        self,
        ue_id: int | None = None,
        switch_off: bool = False,
    ) -> dict[str, Any]:
        """Trigger LTE detach procedure.

        Args:
            ue_id: Specific UE to detach. ``None`` for all UEs.
            switch_off: If True, indicates switch-off detach.

        Returns:
            Detach request confirmation.
        """
        msg: dict[str, Any] = {"message": "detach"}
        if ue_id is not None:
            msg["ue_id"] = ue_id
        if switch_off:
            msg["switch_off"] = True
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # PDN Connection (4G)
    # ──────────────────────────────────────────────

    def pdn_connect(
        self,
        ue_id: int,
        apn: str,
        pdn_type: str = "ipv4",
        **params: Any,
    ) -> dict[str, Any]:
        """Request PDN connection (4G).

        Args:
            ue_id: Target UE identifier.
            apn: Access Point Name.
            pdn_type: PDN type (ipv4, ipv6, ipv4v6).
            **params: Additional PDN parameters.

        Returns:
            PDN connection request confirmation.
        """
        msg: dict[str, Any] = {
            "message": "pdn_connect",
            "ue_id": ue_id,
            "apn": apn,
            "pdn_type": pdn_type,
        }
        msg.update(params)
        return self._client.send(msg)

    def pdn_disconnect(
        self,
        ue_id: int,
        pdn_id: int | None = None,
        apn: str | None = None,
    ) -> dict[str, Any]:
        """Disconnect PDN connection (4G).

        Args:
            ue_id: Target UE identifier.
            pdn_id: PDN connection ID to disconnect.
            apn: Disconnect by APN name.

        Returns:
            PDN disconnection confirmation.
        """
        msg: dict[str, Any] = {"message": "pdn_disconnect", "ue_id": ue_id}
        if pdn_id is not None:
            msg["pdn_id"] = pdn_id
        if apn is not None:
            msg["apn"] = apn
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # PDU Sessions (5G)
    # ──────────────────────────────────────────────

    def pdu_session_establish(
        self,
        ue_id: int,
        dnn: str | None = None,
        s_nssai: dict[str, Any] | None = None,
        pdu_session_type: str = "ipv4",
        **params: Any,
    ) -> dict[str, Any]:
        """Establish PDU session (5G).

        Args:
            ue_id: Target UE identifier.
            dnn: Data Network Name.
            s_nssai: S-NSSAI (slice info) with sst and optional sd.
            pdu_session_type: PDU session type (ipv4, ipv6, ipv4v6).
            **params: Additional PDU session parameters.

        Returns:
            PDU session establishment confirmation.
        """
        msg: dict[str, Any] = {
            "message": "pdu_session_establish",
            "ue_id": ue_id,
            "pdu_session_type": pdu_session_type,
        }
        if dnn is not None:
            msg["dnn"] = dnn
        if s_nssai is not None:
            msg["s_nssai"] = s_nssai
        msg.update(params)
        return self._client.send(msg)

    def pdu_session_release(
        self,
        ue_id: int,
        pdu_session_id: int,
    ) -> dict[str, Any]:
        """Release PDU session (5G).

        Args:
            ue_id: Target UE identifier.
            pdu_session_id: PDU session ID to release.

        Returns:
            PDU session release confirmation.
        """
        return self._client.send(
            {
                "message": "pdu_session_release",
                "ue_id": ue_id,
                "pdu_session_id": pdu_session_id,
            }
        )

    def pdu_session_modify(
        self,
        ue_id: int,
        pdu_session_id: int,
        **params: Any,
    ) -> dict[str, Any]:
        """Modify PDU session (5G).

        Args:
            ue_id: Target UE identifier.
            pdu_session_id: PDU session ID to modify.
            **params: Parameters to modify.

        Returns:
            PDU session modification confirmation.
        """
        msg: dict[str, Any] = {
            "message": "pdu_session_modify",
            "ue_id": ue_id,
            "pdu_session_id": pdu_session_id,
        }
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Bearer Management
    # ──────────────────────────────────────────────

    def ue_activate_dedicated_bearer(
        self,
        ue_id: int,
        def_bearer_id: int,
        qci: int,
        gbr: dict[str, Any] | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Activate a dedicated bearer for a simulated UE.

        Args:
            ue_id: Target UE identifier.
            def_bearer_id: Default bearer ID to associate with.
            qci: QoS Class Identifier.
            gbr: Guaranteed bit rate configuration with keys like
                ``"dl_gbr"``, ``"ul_gbr"``, ``"dl_mbr"``, ``"ul_mbr"``.
            filters: Traffic flow template filters, each containing
                ``"direction"``, ``"id"``, ``"precedence"``, ``"components"``.

        Returns:
            Bearer activation confirmation.
        """
        msg: dict[str, Any] = {
            "message": "ue_activate_dedicated_bearer",
            "ue_id": ue_id,
            "def_bearer_id": def_bearer_id,
            "qci": qci,
        }
        if gbr is not None:
            msg["gbr"] = gbr
        if filters is not None:
            msg["filters"] = filters
        return self._client.send(msg)

    def ue_deactivate_dedicated_bearer(
        self,
        ue_id: int,
        bearer_id: int,
    ) -> dict[str, Any]:
        """Deactivate a dedicated bearer.

        Args:
            ue_id: Target UE identifier.
            bearer_id: Bearer ID to deactivate.

        Returns:
            Bearer deactivation confirmation.
        """
        return self._client.send(
            {
                "message": "ue_deactivate_dedicated_bearer",
                "ue_id": ue_id,
                "bearer_id": bearer_id,
            }
        )

    def ue_modify_dedicated_bearer(
        self,
        ue_id: int,
        bearer_id: int,
        **params: Any,
    ) -> dict[str, Any]:
        """Modify a dedicated bearer.

        Args:
            ue_id: Target UE identifier.
            bearer_id: Bearer ID to modify.
            **params: Parameters to modify (qci, gbr, etc.).

        Returns:
            Bearer modification confirmation.
        """
        msg: dict[str, Any] = {
            "message": "ue_modify_dedicated_bearer",
            "ue_id": ue_id,
            "bearer_id": bearer_id,
        }
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Data Transfer
    # ──────────────────────────────────────────────

    def data_start(
        self,
        ue_id: int,
        bearer_id: int | None = None,
        direction: str = "dl",
        rate_mbps: float | None = None,
        duration_s: float | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Start data transfer for a UE.

        Args:
            ue_id: Target UE identifier.
            bearer_id: Specific bearer for data transfer.
            direction: Transfer direction (dl, ul, both).
            rate_mbps: Target rate in Mbps.
            duration_s: Transfer duration in seconds.
            **params: Additional data parameters.

        Returns:
            Data transfer start confirmation.
        """
        msg: dict[str, Any] = {
            "message": "data_start",
            "ue_id": ue_id,
            "direction": direction,
        }
        if bearer_id is not None:
            msg["bearer_id"] = bearer_id
        if rate_mbps is not None:
            msg["rate_mbps"] = rate_mbps
        if duration_s is not None:
            msg["duration_s"] = duration_s
        msg.update(params)
        return self._client.send(msg)

    def data_stop(
        self,
        ue_id: int,
        bearer_id: int | None = None,
    ) -> dict[str, Any]:
        """Stop data transfer for a UE.

        Args:
            ue_id: Target UE identifier.
            bearer_id: Specific bearer to stop.

        Returns:
            Data transfer stop confirmation.
        """
        msg: dict[str, Any] = {"message": "data_stop", "ue_id": ue_id}
        if bearer_id is not None:
            msg["bearer_id"] = bearer_id
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Voice / IMS
    # ──────────────────────────────────────────────

    def mo_call(
        self,
        ue_id: int,
        destination: str,
        call_type: str = "voice",
        **params: Any,
    ) -> dict[str, Any]:
        """Initiate mobile-originated call.

        Args:
            ue_id: Calling UE identifier.
            destination: Called party number/URI.
            call_type: Call type (voice, video, emergency).
            **params: Additional call parameters.

        Returns:
            Call initiation confirmation.
        """
        msg: dict[str, Any] = {
            "message": "mo_call",
            "ue_id": ue_id,
            "destination": destination,
            "call_type": call_type,
        }
        msg.update(params)
        return self._client.send(msg)

    def mt_call_answer(
        self,
        ue_id: int,
        call_id: int | None = None,
    ) -> dict[str, Any]:
        """Answer an incoming mobile-terminated call.

        Args:
            ue_id: Answering UE identifier.
            call_id: Call ID to answer (if multiple).

        Returns:
            Call answer confirmation.
        """
        msg: dict[str, Any] = {"message": "mt_call_answer", "ue_id": ue_id}
        if call_id is not None:
            msg["call_id"] = call_id
        return self._client.send(msg)

    def call_release(
        self,
        ue_id: int,
        call_id: int | None = None,
        cause: int | None = None,
    ) -> dict[str, Any]:
        """Release/hang up a call.

        Args:
            ue_id: UE identifier.
            call_id: Call ID to release.
            cause: Release cause code.

        Returns:
            Call release confirmation.
        """
        msg: dict[str, Any] = {"message": "call_release", "ue_id": ue_id}
        if call_id is not None:
            msg["call_id"] = call_id
        if cause is not None:
            msg["cause"] = cause
        return self._client.send(msg)

    def send_sms(
        self,
        ue_id: int,
        destination: str,
        text: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Send SMS from a simulated UE.

        Args:
            ue_id: Sending UE identifier.
            destination: Recipient number.
            text: SMS message text.
            **params: Additional SMS parameters.

        Returns:
            SMS send confirmation.
        """
        msg: dict[str, Any] = {
            "message": "send_sms",
            "ue_id": ue_id,
            "destination": destination,
            "text": text,
        }
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Mobility
    # ──────────────────────────────────────────────

    def cell_reselection(
        self,
        ue_id: int,
        target_cell_id: int | None = None,
        target_pci: int | None = None,
    ) -> dict[str, Any]:
        """Trigger cell reselection for idle UE.

        Args:
            ue_id: Target UE identifier.
            target_cell_id: Target cell ID.
            target_pci: Target Physical Cell ID.

        Returns:
            Cell reselection trigger confirmation.
        """
        msg: dict[str, Any] = {"message": "cell_reselection", "ue_id": ue_id}
        if target_cell_id is not None:
            msg["target_cell_id"] = target_cell_id
        if target_pci is not None:
            msg["target_pci"] = target_pci
        return self._client.send(msg)

    def handover_trigger(
        self,
        ue_id: int,
        target_cell_id: int | None = None,
        target_pci: int | None = None,
    ) -> dict[str, Any]:
        """Trigger UE-side handover request.

        Args:
            ue_id: Target UE identifier.
            target_cell_id: Target cell ID.
            target_pci: Target Physical Cell ID.

        Returns:
            Handover trigger confirmation.
        """
        msg: dict[str, Any] = {"message": "handover_trigger", "ue_id": ue_id}
        if target_cell_id is not None:
            msg["target_cell_id"] = target_cell_id
        if target_pci is not None:
            msg["target_pci"] = target_pci
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # NR/5G Specific
    # ──────────────────────────────────────────────

    def ue_assistance_information(
        self,
        ue_id: int,
        preferred_rrc_state: str | None = None,
        delay_budget_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send UE Assistance Information (5G NR).

        Args:
            ue_id: Target UE identifier.
            preferred_rrc_state: Preferred RRC state
                (``"connected"``, ``"inactive"``, ``"idle"``).
            delay_budget_report: Delay budget report parameters.

        Returns:
            UE assistance information confirmation.
        """
        msg: dict[str, Any] = {
            "message": "ue_assistance_information",
            "ue_id": ue_id,
        }
        if preferred_rrc_state is not None:
            msg["preferred_rrc_state"] = preferred_rrc_state
        if delay_budget_report is not None:
            msg["delay_budget_report"] = delay_budget_report
        return self._client.send(msg)

    def rrc_release_request(
        self,
        ue_id: int,
        cause: str | None = None,
    ) -> dict[str, Any]:
        """Request RRC release from UE side (5G NR).

        Args:
            ue_id: Target UE identifier.
            cause: Release cause.

        Returns:
            RRC release request confirmation.
        """
        msg: dict[str, Any] = {"message": "rrc_release_request", "ue_id": ue_id}
        if cause is not None:
            msg["cause"] = cause
        return self._client.send(msg)

    def service_request(
        self,
        ue_id: int,
        service_type: str | None = None,
    ) -> dict[str, Any]:
        """Trigger service request (for inactive UEs).

        Args:
            ue_id: Target UE identifier.
            service_type: Service type (signaling, data, etc.).

        Returns:
            Service request confirmation.
        """
        msg: dict[str, Any] = {"message": "service_request", "ue_id": ue_id}
        if service_type is not None:
            msg["service_type"] = service_type
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Measurements
    # ──────────────────────────────────────────────

    def measurement_report(
        self,
        ue_id: int,
        measurement_id: int | None = None,
    ) -> dict[str, Any]:
        """Get or trigger measurement report from UE.

        Args:
            ue_id: Target UE identifier.
            measurement_id: Specific measurement configuration ID.

        Returns:
            Measurement report data.
        """
        msg: dict[str, Any] = {"message": "measurement_report", "ue_id": ue_id}
        if measurement_id is not None:
            msg["measurement_id"] = measurement_id
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # SIM/USIM Configuration
    # ──────────────────────────────────────────────

    def sim_set(
        self,
        ue_id: int,
        imsi: str | None = None,
        k: str | None = None,
        opc: str | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Configure SIM/USIM parameters for a UE.

        Args:
            ue_id: Target UE identifier.
            imsi: IMSI to set.
            k: Authentication key (hex).
            opc: Operator variant key (hex).
            **params: Additional SIM parameters.

        Returns:
            SIM configuration confirmation.
        """
        msg: dict[str, Any] = {"message": "sim_set", "ue_id": ue_id}
        if imsi is not None:
            msg["imsi"] = imsi
        if k is not None:
            msg["k"] = k
        if opc is not None:
            msg["opc"] = opc
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # TAU / Periodic Updates
    # ──────────────────────────────────────────────

    def tau(self, ue_id: int, tau_type: str = "normal") -> dict[str, Any]:
        """Trigger Tracking Area Update (4G).

        Args:
            ue_id: Target UE identifier.
            tau_type: TAU type (normal, periodic, combined).

        Returns:
            TAU request confirmation.
        """
        return self._client.send(
            {
                "message": "tau",
                "ue_id": ue_id,
                "tau_type": tau_type,
            }
        )

    def periodic_registration(self, ue_id: int) -> dict[str, Any]:
        """Trigger periodic registration update (5G).

        Args:
            ue_id: Target UE identifier.

        Returns:
            Periodic registration confirmation.
        """
        return self._client.send(
            {
                "message": "periodic_registration",
                "ue_id": ue_id,
            }
        )

    # ──────────────────────────────────────────────
    # Utility Commands
    # ──────────────────────────────────────────────

    def cancel(self, message_id: int) -> dict[str, Any]:
        """Cancel a pending async operation.

        Args:
            message_id: Message ID to cancel.

        Returns:
            Cancellation confirmation.
        """
        return self._client.send(
            {
                "message": "cancel",
                "message_id": message_id,
            }
        )

    def echo(self, data: Any = None) -> dict[str, Any]:
        """Echo test - returns the sent data.

        Args:
            data: Optional data to echo back.

        Returns:
            Echo response with the sent data.
        """
        msg: dict[str, Any] = {"message": "echo"}
        if data is not None:
            msg["data"] = data
        return self._client.send(msg)

    def monitor(self, **params: Any) -> dict[str, Any]:
        """Enable event monitoring.

        Args:
            **params: Monitoring parameters.

        Returns:
            Monitor configuration confirmation.
        """
        msg: dict[str, Any] = {"message": "monitor"}
        msg.update(params)
        return self._client.send(msg)

    def quit(self) -> dict[str, Any]:
        """Quit the UE simulator service.

        Returns:
            Quit acknowledgment.
        """
        return self._client.send({"message": "quit"})
