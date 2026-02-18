"""MME/AMF (core network) Remote API methods."""

from __future__ import annotations

from typing import Any

from .base import ServiceApi


class MMEApi(ServiceApi):
    """API for controlling an Amarisoft MME/AMF via the Remote API.

    Provides methods for UE management, bearer control, paging,
    and policy configuration on the core network side.

    Inherits common methods from :class:`ServiceApi`:
    ``config_get``, ``config_set``, ``stats``, ``ue_get``,
    ``log_get``, ``log_set``.

    Remote API Commands Summary:
        - Network Queries: enb_get, gnb_get, session_get, bearer_get
        - UE Management: ue_add, ue_del, ue_set, ue_detach, ue_identity_request
        - Bearer/Session: ue_activate_dedicated_bearer, ue_deactivate_bearer,
            ue_modify_bearer, ue_modify_pdu_session, ue_modify_reflective_qos
        - 5G NAS: 5gs_nas_transport, generic_nas_transport, guti_realloc
        - Paging: mt_cs_paging, mt_data_paging, mme_paging_status
        - Policy/Filters: attach_reject_filter, registration_reject_filter, pdn_list
        - Location Services: lcs, location_req, lpp_request_location, etc.
        - Interface Control: S6, S13, SGS, N-interfaces (5GC)
        - PWS/CBC: cbc_notif_subscribe, pws_kill, pws_write, sbc
        - Utility: cancel, echo, license, monitor, quit
    """

    DEFAULT_PORT = 9000

    # ──────────────────────────────────────────────
    # Network Element Queries
    # ──────────────────────────────────────────────

    def enb_get(self, **filters: Any) -> dict[str, Any]:
        """Query connected eNodeBs (LTE base stations).

        Args:
            **filters: Optional filters.
        """
        msg: dict[str, Any] = {"message": "enb_get"}
        msg.update(filters)
        return self._client.send(msg)

    def gnb_get(self, **filters: Any) -> dict[str, Any]:
        """Query connected gNodeBs (NR base stations).

        Args:
            **filters: Optional filters.
        """
        msg: dict[str, Any] = {"message": "gnb_get"}
        msg.update(filters)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Session / Bearer Queries
    # ──────────────────────────────────────────────

    def session_get(self, **filters: Any) -> dict[str, Any]:
        """Query PDN/PDU session details.

        Args:
            **filters: Optional filters (e.g., imsi).
        """
        msg: dict[str, Any] = {"message": "session_get"}
        msg.update(filters)
        return self._client.send(msg)

    def bearer_get(self, **filters: Any) -> dict[str, Any]:
        """Query EPS bearer or QoS flow information.

        Args:
            **filters: Optional filters (e.g., imsi, erab_id).
        """
        msg: dict[str, Any] = {"message": "bearer_get"}
        msg.update(filters)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # UE Management
    # ──────────────────────────────────────────────

    def ue_detach(
        self,
        imsi: str | None = None,
        imei: str | None = None,
    ) -> dict[str, Any]:
        """Detach a UE from the network.

        At least one of *imsi* or *imei* should be provided to identify
        the target UE.

        Args:
            imsi: IMSI of the target UE.
            imei: IMEI of the target UE.
        """
        msg: dict[str, Any] = {"message": "ue_detach"}
        if imsi is not None:
            msg["imsi"] = imsi
        if imei is not None:
            msg["imei"] = imei
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Bearer Management
    # ──────────────────────────────────────────────

    def ue_deactivate_bearer(
        self,
        erab_id: int,
        imsi: str | None = None,
        imei: str | None = None,
    ) -> dict[str, Any]:
        """Deactivate a bearer for a UE.

        Args:
            erab_id: E-RAB identifier to deactivate.
            imsi: IMSI of the target UE.
            imei: IMEI of the target UE.
        """
        msg: dict[str, Any] = {
            "message": "ue_deactivate_bearer",
            "erab_id": erab_id,
        }
        if imsi is not None:
            msg["imsi"] = imsi
        if imei is not None:
            msg["imei"] = imei
        return self._client.send(msg)

    def ue_modify_bearer(
        self,
        imsi: str,
        erab_id: int,
        qci: int,
        priority_level: int | None = None,
        pre_emption_capability: str | None = None,
        pre_emption_vulnerability: str | None = None,
    ) -> dict[str, Any]:
        """Modify QoS parameters of an existing bearer.

        Args:
            imsi: IMSI of the target UE.
            erab_id: E-RAB identifier to modify.
            qci: New QoS Class Identifier.
            priority_level: ARP priority level.
            pre_emption_capability: ``"shall_not_trigger"`` or
                ``"may_trigger"``.
            pre_emption_vulnerability: ``"not_pre_emptable"`` or
                ``"pre_emptable"``.
        """
        qos: dict[str, Any] = {"qci": qci}
        if priority_level is not None:
            qos["priority_level"] = priority_level
        if pre_emption_capability is not None:
            qos["pre_emption_capability"] = pre_emption_capability
        if pre_emption_vulnerability is not None:
            qos["pre_emption_vulnerability"] = pre_emption_vulnerability

        return self._client.send({
            "message": "ue_modify_bearer",
            "imsi": imsi,
            "erab_id": erab_id,
            "qos": qos,
        })

    # ──────────────────────────────────────────────
    # Paging
    # ──────────────────────────────────────────────

    def mt_cs_paging(self, imsi: str) -> dict[str, Any]:
        """Initiate circuit-switched mobile-terminated paging.

        Args:
            imsi: IMSI of the target UE.
        """
        return self._client.send({
            "message": "mt_cs_paging",
            "imsi": imsi,
        })

    # ──────────────────────────────────────────────
    # Policy / Filters
    # ──────────────────────────────────────────────

    def attach_reject_filter(
        self,
        imsi: str,
        emm_cause: int,
    ) -> dict[str, Any]:
        """Set an attach reject filter for a specific IMSI.

        Args:
            imsi: IMSI to filter.
            emm_cause: EMM cause code for rejection.
        """
        return self._client.send({
            "message": "attach_reject_filter",
            "imsi": imsi,
            "emm_cause": emm_cause,
        })

    def attach_reject_filter_clear(self) -> dict[str, Any]:
        """Clear all attach reject filters."""
        return self._client.send({
            "message": "attach_reject_filter",
            "clear": True,
        })

    def registration_reject_filter(
        self,
        imsi: str,
        cause: int,
    ) -> dict[str, Any]:
        """Set a 5G registration reject filter.

        Uses the ``registration_mobility_periodic`` message to configure
        the AMF to reject registration from a specific IMSI.

        Args:
            imsi: IMSI to filter.
            cause: 5GMM cause code for rejection.
        """
        return self._client.send({
            "message": "registration_mobility_periodic",
            "imsi": imsi,
            "reject": True,
            "cause": cause,
        })

    def set_t3512(self, value: int) -> dict[str, Any]:
        """Set the T3512 periodic tracking area update timer.

        Args:
            value: Timer value in seconds.
        """
        return self._client.send({
            "message": "t3512",
            "value": value,
        })

    def pdn_list(self, apn: str, **params: Any) -> dict[str, Any]:
        """Configure PDN settings.

        Args:
            apn: Access Point Name.
            **params: Additional PDN parameters (e.g.,
                ``esm_procedure_filter``).
        """
        msg: dict[str, Any] = {
            "message": "pdn_list",
            "apn": apn,
        }
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # APN Configuration Helpers
    # ──────────────────────────────────────────────

    def set_default_apn(
        self,
        apn: str = "default",
        pdn_type: str = "ipv4",
        first_ip: str | None = None,
        last_ip: str | None = None,
        dns: str | list[str] | None = None,
        qci: int = 9,
        priority_level: int = 15,
    ) -> dict[str, Any]:
        """Set the default APN configuration.

        This is a convenience method that configures a default APN with
        common settings. For more advanced configuration, edit the MME
        config file directly via SSH.

        Args:
            apn: Access Point Name (default: "default").
            pdn_type: PDN type - "ipv4", "ipv6", or "ipv4v6" (default: "ipv4").
            first_ip: First IP address in the pool (e.g., "192.168.2.2").
            last_ip: Last IP address in the pool (e.g., "192.168.2.254").
            dns: DNS server address(es). Can be a string or list of strings.
                Example: "8.8.8.8" or ["8.8.8.8", "8.8.4.4"]
            qci: QoS Class Identifier (default: 9 for best-effort).
                Common values:
                - 1: Conversational Voice
                - 5: IMS Signaling
                - 9: Best Effort (default internet)
            priority_level: ARP priority level 1-15 (default: 15, lowest).

        Returns:
            Response from the MME.

        Example::

            # Set a simple default APN
            mme.set_default_apn()

            # Set internet APN with custom IP pool
            mme.set_default_apn(
                apn="internet",
                first_ip="192.168.3.2",
                last_ip="192.168.3.254",
                dns="8.8.8.8"
            )

            # Set IMS APN for VoLTE
            mme.set_default_apn(
                apn="ims",
                pdn_type="ipv4v6",
                qci=5,  # IMS signaling
                priority_level=1
            )

        Note:
            This method uses the pdn_list Remote API command. For persistent
            changes, you should modify the MME config file directly:

            .. code-block:: bash

                ssh root@<callbox_ip>
                vi /root/mme/config/mme.cfg
                # Edit the pdn_list section
        """
        msg: dict[str, Any] = {
            "message": "pdn_list",
            "apn": apn,
            "pdn_type": pdn_type,
        }

        if first_ip is not None:
            msg["first_ip_addr"] = first_ip
        if last_ip is not None:
            msg["last_ip_addr"] = last_ip
        if dns is not None:
            msg["dns_addr"] = dns

        # QoS parameters
        msg["qci"] = qci
        msg["priority_level"] = priority_level

        return self._client.send(msg)

    def get_apn_sessions(self, apn: str | None = None) -> list[dict[str, Any]]:
        """Get active PDN sessions, optionally filtered by APN.

        Args:
            apn: Filter by APN name. If None, returns all sessions.

        Returns:
            List of active PDN sessions.

        Example::

            # Get all sessions
            sessions = mme.get_apn_sessions()

            # Get only IMS sessions
            ims_sessions = mme.get_apn_sessions(apn="ims")
        """
        result = self.session_get()
        sessions = result.get("session_list", result.get("pdn_list", []))

        if apn is not None:
            sessions = [
                s for s in sessions
                if s.get("apn") == apn or s.get("access_point_name") == apn
            ]

        return sessions

    # ──────────────────────────────────────────────
    # UE Management (Extended)
    # ──────────────────────────────────────────────

    def ue_add(
        self,
        imsi: str,
        ki: str | None = None,
        opc: str | None = None,
        apn: str = "default",
        **params: Any,
    ) -> dict[str, Any]:
        """Add a UE to the subscriber database.

        Args:
            imsi: IMSI of the UE to add.
            ki: Authentication key (128-bit hex string).
            opc: Operator variant algorithm configuration (128-bit hex string).
            apn: Default APN for the UE.
            **params: Additional UE parameters (e.g., sqn, msisdn).

        Returns:
            Response from the MME.
        """
        msg: dict[str, Any] = {
            "message": "ue_add",
            "imsi": imsi,
            "apn": apn,
        }
        if ki is not None:
            msg["Ki"] = ki
        if opc is not None:
            msg["OPc"] = opc
        msg.update(params)
        return self._client.send(msg)

    def ue_del(
        self,
        imsi: str | None = None,
        imei: str | None = None,
    ) -> dict[str, Any]:
        """Delete a UE from the subscriber database.

        Args:
            imsi: IMSI of the UE to delete.
            imei: IMEI of the UE to delete.

        Returns:
            Response from the MME.
        """
        msg: dict[str, Any] = {"message": "ue_del"}
        if imsi is not None:
            msg["imsi"] = imsi
        if imei is not None:
            msg["imei"] = imei
        return self._client.send(msg)

    def ue_set(
        self,
        imsi: str | None = None,
        imei: str | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Modify UE parameters in the subscriber database.

        Args:
            imsi: IMSI of the UE to modify.
            imei: IMEI of the UE to modify.
            **params: Parameters to modify (e.g., apn, qci, ambr).

        Returns:
            Response from the MME.
        """
        msg: dict[str, Any] = {"message": "ue_set"}
        if imsi is not None:
            msg["imsi"] = imsi
        if imei is not None:
            msg["imei"] = imei
        msg.update(params)
        return self._client.send(msg)

    def ue_identity_request(
        self,
        imsi: str | None = None,
        imei: str | None = None,
        identity_type: str = "imei",
    ) -> dict[str, Any]:
        """Request UE identity.

        Args:
            imsi: IMSI of the target UE.
            imei: IMEI of the target UE.
            identity_type: Type of identity to request ("imsi", "imei", "imeisv").

        Returns:
            Response containing the requested identity.
        """
        msg: dict[str, Any] = {
            "message": "ue_identity_request",
            "identity_type": identity_type,
        }
        if imsi is not None:
            msg["imsi"] = imsi
        if imei is not None:
            msg["imei"] = imei
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Bearer/Session Management (Extended)
    # ──────────────────────────────────────────────

    def ue_activate_dedicated_bearer(
        self,
        imsi: str,
        apn: str,
        qci: int,
        priority_level: int = 15,
        pre_emption_capability: str = "shall_not_trigger",
        pre_emption_vulnerability: str = "pre_emptable",
        **params: Any,
    ) -> dict[str, Any]:
        """Activate a dedicated bearer for a UE.

        Args:
            imsi: IMSI of the target UE.
            apn: APN for the bearer.
            qci: QoS Class Identifier.
            priority_level: ARP priority level (1-15).
            pre_emption_capability: "shall_not_trigger" or "may_trigger".
            pre_emption_vulnerability: "not_pre_emptable" or "pre_emptable".
            **params: Additional bearer parameters.

        Returns:
            Response from the MME.
        """
        msg: dict[str, Any] = {
            "message": "ue_activate_dedicated_bearer",
            "imsi": imsi,
            "apn": apn,
            "qos": {
                "qci": qci,
                "priority_level": priority_level,
                "pre_emption_capability": pre_emption_capability,
                "pre_emption_vulnerability": pre_emption_vulnerability,
            },
        }
        msg.update(params)
        return self._client.send(msg)

    def ue_modify_pdu_session(
        self,
        imsi: str,
        pdu_session_id: int,
        **params: Any,
    ) -> dict[str, Any]:
        """Modify an existing PDU session (5G).

        Args:
            imsi: IMSI of the target UE.
            pdu_session_id: PDU session ID to modify.
            **params: Session parameters to modify.

        Returns:
            Response from the MME/AMF.
        """
        msg: dict[str, Any] = {
            "message": "ue_modify_pdu_session",
            "imsi": imsi,
            "pdu_session_id": pdu_session_id,
        }
        msg.update(params)
        return self._client.send(msg)

    def ue_modify_reflective_qos(
        self,
        imsi: str,
        pdu_session_id: int,
        enabled: bool,
    ) -> dict[str, Any]:
        """Enable or disable reflective QoS for a PDU session.

        Args:
            imsi: IMSI of the target UE.
            pdu_session_id: PDU session ID.
            enabled: True to enable reflective QoS, False to disable.

        Returns:
            Response from the AMF.
        """
        return self._client.send({
            "message": "ue_modify_reflective_qos",
            "imsi": imsi,
            "pdu_session_id": pdu_session_id,
            "reflective_qos": enabled,
        })

    def ue_nssaa(
        self,
        imsi: str,
        slice_service_type: int,
        slice_differentiator: int | None = None,
        action: str = "start",
    ) -> dict[str, Any]:
        """Trigger Network Slice-Specific Authentication and Authorization.

        Args:
            imsi: IMSI of the target UE.
            slice_service_type: S-NSSAI Slice/Service Type.
            slice_differentiator: S-NSSAI Slice Differentiator.
            action: "start" to initiate, "complete" to finish.

        Returns:
            Response from the AMF.
        """
        msg: dict[str, Any] = {
            "message": "ue_nssaa",
            "imsi": imsi,
            "slice_service_type": slice_service_type,
            "action": action,
        }
        if slice_differentiator is not None:
            msg["slice_differentiator"] = slice_differentiator
        return self._client.send(msg)

    def ue_s_nssai_update(
        self,
        imsi: str,
        allowed_nssai: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Update allowed NSSAI for a UE.

        Args:
            imsi: IMSI of the target UE.
            allowed_nssai: List of S-NSSAI entries.

        Returns:
            Response from the AMF.
        """
        return self._client.send({
            "message": "ue_s_nssai_update",
            "imsi": imsi,
            "allowed_nssai": allowed_nssai,
        })

    # ──────────────────────────────────────────────
    # 5G NAS Transport
    # ──────────────────────────────────────────────

    def nas_5gs_transport(
        self,
        imsi: str,
        payload: str,
        payload_type: str = "n1",
    ) -> dict[str, Any]:
        """Send 5GS NAS transport message.

        Args:
            imsi: IMSI of the target UE.
            payload: Payload data (hex string).
            payload_type: Type of payload ("n1", "sms", "lpp").

        Returns:
            Response from the AMF.
        """
        return self._client.send({
            "message": "5gs_nas_transport",
            "imsi": imsi,
            "payload": payload,
            "payload_type": payload_type,
        })

    def generic_nas_transport(
        self,
        imsi: str,
        container_type: str,
        container: str,
    ) -> dict[str, Any]:
        """Send generic NAS transport message.

        Args:
            imsi: IMSI of the target UE.
            container_type: Type of container.
            container: Container data (hex string).

        Returns:
            Response from the MME/AMF.
        """
        return self._client.send({
            "message": "generic_nas_transport",
            "imsi": imsi,
            "container_type": container_type,
            "container": container,
        })

    def guti_realloc(
        self,
        imsi: str | None = None,
        imei: str | None = None,
    ) -> dict[str, Any]:
        """Reallocate GUTI for a UE.

        Args:
            imsi: IMSI of the target UE.
            imei: IMEI of the target UE.

        Returns:
            Response from the MME/AMF.
        """
        msg: dict[str, Any] = {"message": "guti_realloc"}
        if imsi is not None:
            msg["imsi"] = imsi
        if imei is not None:
            msg["imei"] = imei
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Paging (Extended)
    # ──────────────────────────────────────────────

    def mt_data_paging(
        self,
        imsi: str,
        apn: str | None = None,
    ) -> dict[str, Any]:
        """Initiate mobile-terminated data paging.

        Args:
            imsi: IMSI of the target UE.
            apn: Optional APN to specify.

        Returns:
            Response from the MME/AMF.
        """
        msg: dict[str, Any] = {
            "message": "mt_data_paging",
            "imsi": imsi,
        }
        if apn is not None:
            msg["apn"] = apn
        return self._client.send(msg)

    def mme_paging_status(
        self,
        imsi: str | None = None,
    ) -> dict[str, Any]:
        """Get paging status.

        Args:
            imsi: Optional IMSI to filter status.

        Returns:
            Paging status information.
        """
        msg: dict[str, Any] = {"message": "mme_paging_status"}
        if imsi is not None:
            msg["imsi"] = imsi
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Timer Configuration
    # ──────────────────────────────────────────────

    def t3346(self, value: int) -> dict[str, Any]:
        """Set T3346 timer (congestion back-off timer).

        Args:
            value: Timer value in seconds.

        Returns:
            Response from the MME.
        """
        return self._client.send({
            "message": "t3346",
            "value": value,
        })

    # ──────────────────────────────────────────────
    # Location Services
    # ──────────────────────────────────────────────

    def lcs(
        self,
        imsi: str,
        action: str = "start",
        **params: Any,
    ) -> dict[str, Any]:
        """Location services control.

        Args:
            imsi: IMSI of the target UE.
            action: Action to perform ("start", "stop").
            **params: Additional LCS parameters.

        Returns:
            Response from the MME/AMF.
        """
        msg: dict[str, Any] = {
            "message": "lcs",
            "imsi": imsi,
            "action": action,
        }
        msg.update(params)
        return self._client.send(msg)

    def location_req(
        self,
        imsi: str,
        location_type: str = "current",
        **params: Any,
    ) -> dict[str, Any]:
        """Request UE location.

        Args:
            imsi: IMSI of the target UE.
            location_type: Type of location request.
            **params: Additional parameters.

        Returns:
            Location information.
        """
        msg: dict[str, Any] = {
            "message": "location_req",
            "imsi": imsi,
            "location_type": location_type,
        }
        msg.update(params)
        return self._client.send(msg)

    def lpp_request_location(
        self,
        imsi: str,
        method: str = "ecid",
        **params: Any,
    ) -> dict[str, Any]:
        """Request UE location using LPP protocol.

        Args:
            imsi: IMSI of the target UE.
            method: Positioning method ("ecid", "otdoa", "gnss", "agnss").
            **params: Additional LPP parameters.

        Returns:
            Location response.
        """
        msg: dict[str, Any] = {
            "message": "lpp_request_location",
            "imsi": imsi,
            "method": method,
        }
        msg.update(params)
        return self._client.send(msg)

    def lpp_provide_ad(
        self,
        imsi: str,
        assistance_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Provide LPP assistance data to UE.

        Args:
            imsi: IMSI of the target UE.
            assistance_data: Assistance data to provide.

        Returns:
            Response from the MME/AMF.
        """
        return self._client.send({
            "message": "lpp_provide_ad",
            "imsi": imsi,
            "assistance_data": assistance_data,
        })

    def lpp_request_ad(
        self,
        imsi: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Request LPP assistance data.

        Args:
            imsi: IMSI of the target UE.
            **params: Request parameters.

        Returns:
            Assistance data response.
        """
        msg: dict[str, Any] = {
            "message": "lpp_request_ad",
            "imsi": imsi,
        }
        msg.update(params)
        return self._client.send(msg)

    def lpp_request_capabilities(
        self,
        imsi: str,
    ) -> dict[str, Any]:
        """Request UE LPP capabilities.

        Args:
            imsi: IMSI of the target UE.

        Returns:
            UE positioning capabilities.
        """
        return self._client.send({
            "message": "lpp_request_capabilities",
            "imsi": imsi,
        })

    def lpp_abort(
        self,
        imsi: str,
        transaction_id: int | None = None,
    ) -> dict[str, Any]:
        """Abort LPP transaction.

        Args:
            imsi: IMSI of the target UE.
            transaction_id: Optional transaction ID to abort.

        Returns:
            Response from the MME/AMF.
        """
        msg: dict[str, Any] = {
            "message": "lpp_abort",
            "imsi": imsi,
        }
        if transaction_id is not None:
            msg["transaction_id"] = transaction_id
        return self._client.send(msg)

    def lpp_error(
        self,
        imsi: str,
        error_code: int,
        transaction_id: int | None = None,
    ) -> dict[str, Any]:
        """Send LPP error to UE.

        Args:
            imsi: IMSI of the target UE.
            error_code: LPP error code.
            transaction_id: Optional transaction ID.

        Returns:
            Response from the MME/AMF.
        """
        msg: dict[str, Any] = {
            "message": "lpp_error",
            "imsi": imsi,
            "error_code": error_code,
        }
        if transaction_id is not None:
            msg["transaction_id"] = transaction_id
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # S6a/S6d Interface (HSS)
    # ──────────────────────────────────────────────

    def s6_status(self) -> dict[str, Any]:
        """Get S6a/S6d interface status.

        Returns:
            S6 interface status information.
        """
        return self._client.send({"message": "s6_status"})

    def s6_connect(
        self,
        host: str,
        port: int = 3868,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to HSS via S6a/S6d interface.

        Args:
            host: HSS hostname or IP.
            port: Diameter port (default: 3868).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "s6_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def s6_disconnect(self) -> dict[str, Any]:
        """Disconnect from HSS.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "s6_disconnect"})

    # ──────────────────────────────────────────────
    # S13 Interface (EIR)
    # ──────────────────────────────────────────────

    def s13_status(self) -> dict[str, Any]:
        """Get S13 interface status.

        Returns:
            S13 interface status information.
        """
        return self._client.send({"message": "s13_status"})

    def s13_connect(
        self,
        host: str,
        port: int = 3868,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to EIR via S13 interface.

        Args:
            host: EIR hostname or IP.
            port: Diameter port (default: 3868).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "s13_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def s13_disconnect(self) -> dict[str, Any]:
        """Disconnect from EIR.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "s13_disconnect"})

    # ──────────────────────────────────────────────
    # SGS Interface (MSC/VLR)
    # ──────────────────────────────────────────────

    def sgs_status(self) -> dict[str, Any]:
        """Get SGs interface status.

        Returns:
            SGs interface status information.
        """
        return self._client.send({"message": "sgs_status"})

    def sgs_connect(
        self,
        host: str,
        port: int = 29118,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to MSC/VLR via SGs interface.

        Args:
            host: MSC/VLR hostname or IP.
            port: SCTP port (default: 29118).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "sgs_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def sgs_disconnect(self) -> dict[str, Any]:
        """Disconnect from MSC/VLR.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "sgs_disconnect"})

    # ──────────────────────────────────────────────
    # 5GC N-Interfaces
    # ──────────────────────────────────────────────

    def n8_status(self) -> dict[str, Any]:
        """Get N8 interface status (AMF-UDM).

        Returns:
            N8 interface status information.
        """
        return self._client.send({"message": "n8_status"})

    def n8_connect(
        self,
        host: str,
        port: int = 443,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to UDM via N8 interface.

        Args:
            host: UDM hostname or IP.
            port: HTTPS port (default: 443).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "n8_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def n8_disconnect(self) -> dict[str, Any]:
        """Disconnect from UDM.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "n8_disconnect"})

    def n12_status(self) -> dict[str, Any]:
        """Get N12 interface status (AMF-AUSF).

        Returns:
            N12 interface status information.
        """
        return self._client.send({"message": "n12_status"})

    def n12_connect(
        self,
        host: str,
        port: int = 443,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to AUSF via N12 interface.

        Args:
            host: AUSF hostname or IP.
            port: HTTPS port (default: 443).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "n12_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def n12_disconnect(self) -> dict[str, Any]:
        """Disconnect from AUSF.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "n12_disconnect"})

    def n13_status(self) -> dict[str, Any]:
        """Get N13 interface status (UDM-AUSF).

        Returns:
            N13 interface status information.
        """
        return self._client.send({"message": "n13_status"})

    def n13_connect(
        self,
        host: str,
        port: int = 443,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect UDM to AUSF via N13 interface.

        Args:
            host: AUSF hostname or IP.
            port: HTTPS port (default: 443).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "n13_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def n13_disconnect(self) -> dict[str, Any]:
        """Disconnect UDM from AUSF.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "n13_disconnect"})

    def n17_status(self) -> dict[str, Any]:
        """Get N17 interface status (AMF-5G-EIR).

        Returns:
            N17 interface status information.
        """
        return self._client.send({"message": "n17_status"})

    def n17_connect(
        self,
        host: str,
        port: int = 443,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to 5G-EIR via N17 interface.

        Args:
            host: 5G-EIR hostname or IP.
            port: HTTPS port (default: 443).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "n17_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def n17_disconnect(self) -> dict[str, Any]:
        """Disconnect from 5G-EIR.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "n17_disconnect"})

    def nl1_status(self) -> dict[str, Any]:
        """Get NL1 interface status (LMF).

        Returns:
            NL1 interface status information.
        """
        return self._client.send({"message": "nl1_status"})

    def nl1_connect(
        self,
        host: str,
        port: int = 443,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to LMF via NL1 interface.

        Args:
            host: LMF hostname or IP.
            port: HTTPS port (default: 443).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "nl1_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def nl1_disconnect(self) -> dict[str, Any]:
        """Disconnect from LMF.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "nl1_disconnect"})

    # ──────────────────────────────────────────────
    # SLm Interface (GMLC)
    # ──────────────────────────────────────────────

    def slm_status(self) -> dict[str, Any]:
        """Get SLm interface status (MME-GMLC).

        Returns:
            SLm interface status information.
        """
        return self._client.send({"message": "slm_status"})

    def slm_connect(
        self,
        host: str,
        port: int = 3868,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to GMLC via SLm interface.

        Args:
            host: GMLC hostname or IP.
            port: Diameter port (default: 3868).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "slm_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def slm_disconnect(self) -> dict[str, Any]:
        """Disconnect from GMLC.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "slm_disconnect"})

    # ──────────────────────────────────────────────
    # SLs Interface (GMLC)
    # ──────────────────────────────────────────────

    def sls_status(self) -> dict[str, Any]:
        """Get SLs interface status (MME-E-SMLC).

        Returns:
            SLs interface status information.
        """
        return self._client.send({"message": "sls_status"})

    def sls_connect(
        self,
        host: str,
        port: int = 29171,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to E-SMLC via SLs interface.

        Args:
            host: E-SMLC hostname or IP.
            port: SCTP port (default: 29171).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "sls_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def sls_disconnect(self) -> dict[str, Any]:
        """Disconnect from E-SMLC.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "sls_disconnect"})

    # ──────────────────────────────────────────────
    # CBC/PWS (Public Warning System)
    # ──────────────────────────────────────────────

    def cbc_notif_subscribe(
        self,
        callback_url: str,
    ) -> dict[str, Any]:
        """Subscribe to CBC notifications.

        Args:
            callback_url: URL to receive notifications.

        Returns:
            Subscription result.
        """
        return self._client.send({
            "message": "cbc_notif_subscribe",
            "callback_url": callback_url,
        })

    def cbc_notif_unsubscribe(
        self,
        subscription_id: str | None = None,
    ) -> dict[str, Any]:
        """Unsubscribe from CBC notifications.

        Args:
            subscription_id: Optional subscription ID to unsubscribe.

        Returns:
            Unsubscription result.
        """
        msg: dict[str, Any] = {"message": "cbc_notif_unsubscribe"}
        if subscription_id is not None:
            msg["subscription_id"] = subscription_id
        return self._client.send(msg)

    def pws_kill(
        self,
        message_id: int,
        serial_number: int | None = None,
    ) -> dict[str, Any]:
        """Kill a PWS message.

        Args:
            message_id: Message ID to kill.
            serial_number: Optional serial number.

        Returns:
            Kill result.
        """
        msg: dict[str, Any] = {
            "message": "pws_kill",
            "message_id": message_id,
        }
        if serial_number is not None:
            msg["serial_number"] = serial_number
        return self._client.send(msg)

    def pws_write(
        self,
        message_id: int,
        serial_number: int,
        payload: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Write a PWS message.

        Args:
            message_id: Message ID.
            serial_number: Serial number.
            payload: Message payload (hex string).
            **params: Additional parameters (warning_type, repetition_period, etc.).

        Returns:
            Write result.
        """
        msg: dict[str, Any] = {
            "message": "pws_write",
            "message_id": message_id,
            "serial_number": serial_number,
            "payload": payload,
        }
        msg.update(params)
        return self._client.send(msg)

    def sbc_status(self) -> dict[str, Any]:
        """Get SBc interface status (MME-CBC).

        Returns:
            SBc interface status information.
        """
        return self._client.send({"message": "sbc_status"})

    def sbc_connect(
        self,
        host: str,
        port: int = 29168,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to CBC via SBc interface.

        Args:
            host: CBC hostname or IP.
            port: SCTP port (default: 29168).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "sbc_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def sbc_disconnect(self) -> dict[str, Any]:
        """Disconnect from CBC.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "sbc_disconnect"})

    def n50_status(self) -> dict[str, Any]:
        """Get N50 interface status (AMF-CBCF, 5G PWS).

        Returns:
            N50 interface status information.
        """
        return self._client.send({"message": "n50_status"})

    def n50_connect(
        self,
        host: str,
        port: int = 443,
        **params: Any,
    ) -> dict[str, Any]:
        """Connect to CBCF via N50 interface (5G PWS).

        Args:
            host: CBCF hostname or IP.
            port: HTTPS port (default: 443).
            **params: Additional connection parameters.

        Returns:
            Connection result.
        """
        msg: dict[str, Any] = {
            "message": "n50_connect",
            "host": host,
            "port": port,
        }
        msg.update(params)
        return self._client.send(msg)

    def n50_disconnect(self) -> dict[str, Any]:
        """Disconnect from CBCF.

        Returns:
            Disconnection result.
        """
        return self._client.send({"message": "n50_disconnect"})

    # ──────────────────────────────────────────────
    # SMS
    # ──────────────────────────────────────────────

    def sms_send(
        self,
        imsi: str,
        text: str,
        originating_addr: str | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Send SMS to a UE.

        Args:
            imsi: IMSI of the target UE.
            text: SMS text content.
            originating_addr: Optional originating address.
            **params: Additional SMS parameters.

        Returns:
            SMS send result.
        """
        msg: dict[str, Any] = {
            "message": "sms_send",
            "imsi": imsi,
            "text": text,
        }
        if originating_addr is not None:
            msg["originating_addr"] = originating_addr
        msg.update(params)
        return self._client.send(msg)

    def sms_status(
        self,
        imsi: str | None = None,
    ) -> dict[str, Any]:
        """Get SMS status.

        Args:
            imsi: Optional IMSI to filter status.

        Returns:
            SMS status information.
        """
        msg: dict[str, Any] = {"message": "sms_status"}
        if imsi is not None:
            msg["imsi"] = imsi
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Lawful Interception
    # ──────────────────────────────────────────────

    def li_start(
        self,
        imsi: str,
        **params: Any,
    ) -> dict[str, Any]:
        """Start lawful interception for a UE.

        Args:
            imsi: IMSI of the target UE.
            **params: Additional LI parameters.

        Returns:
            LI start result.
        """
        msg: dict[str, Any] = {
            "message": "li_start",
            "imsi": imsi,
        }
        msg.update(params)
        return self._client.send(msg)

    def li_stop(
        self,
        imsi: str | None = None,
        li_id: str | None = None,
    ) -> dict[str, Any]:
        """Stop lawful interception.

        Args:
            imsi: IMSI of the target UE.
            li_id: Optional LI session ID.

        Returns:
            LI stop result.
        """
        msg: dict[str, Any] = {"message": "li_stop"}
        if imsi is not None:
            msg["imsi"] = imsi
        if li_id is not None:
            msg["li_id"] = li_id
        return self._client.send(msg)

    def li_status(self) -> dict[str, Any]:
        """Get lawful interception status.

        Returns:
            LI status information.
        """
        return self._client.send({"message": "li_status"})

    # ──────────────────────────────────────────────
    # TAU/Mobility
    # ──────────────────────────────────────────────

    def tau_reject_filter(
        self,
        imsi: str,
        emm_cause: int,
    ) -> dict[str, Any]:
        """Set TAU reject filter for a specific IMSI.

        Args:
            imsi: IMSI to filter.
            emm_cause: EMM cause code for rejection.

        Returns:
            Response from the MME.
        """
        return self._client.send({
            "message": "tau_reject_filter",
            "imsi": imsi,
            "emm_cause": emm_cause,
        })

    def tau_reject_filter_clear(self) -> dict[str, Any]:
        """Clear all TAU reject filters.

        Returns:
            Response from the MME.
        """
        return self._client.send({
            "message": "tau_reject_filter",
            "clear": True,
        })

    def service_reject_filter(
        self,
        imsi: str,
        emm_cause: int,
    ) -> dict[str, Any]:
        """Set service request reject filter.

        Args:
            imsi: IMSI to filter.
            emm_cause: EMM cause code for rejection.

        Returns:
            Response from the MME.
        """
        return self._client.send({
            "message": "service_reject_filter",
            "imsi": imsi,
            "emm_cause": emm_cause,
        })

    def service_reject_filter_clear(self) -> dict[str, Any]:
        """Clear all service request reject filters.

        Returns:
            Response from the MME.
        """
        return self._client.send({
            "message": "service_reject_filter",
            "clear": True,
        })

    def registration_mobility_periodic(
        self,
        imsi: str | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Configure registration/mobility/periodic TAU behavior.

        Args:
            imsi: Optional IMSI to target.
            **params: Configuration parameters.

        Returns:
            Response from the AMF.
        """
        msg: dict[str, Any] = {"message": "registration_mobility_periodic"}
        if imsi is not None:
            msg["imsi"] = imsi
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Slice Management (5G)
    # ──────────────────────────────────────────────

    def slice_get(self, **filters: Any) -> dict[str, Any]:
        """Get network slice information.

        Args:
            **filters: Optional filters.

        Returns:
            Slice information.
        """
        msg: dict[str, Any] = {"message": "slice_get"}
        msg.update(filters)
        return self._client.send(msg)

    def slice_add(
        self,
        sst: int,
        sd: int | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Add a network slice.

        Args:
            sst: Slice/Service Type.
            sd: Slice Differentiator.
            **params: Additional slice parameters.

        Returns:
            Response from the AMF.
        """
        msg: dict[str, Any] = {
            "message": "slice_add",
            "sst": sst,
        }
        if sd is not None:
            msg["sd"] = sd
        msg.update(params)
        return self._client.send(msg)

    def slice_del(
        self,
        sst: int,
        sd: int | None = None,
    ) -> dict[str, Any]:
        """Delete a network slice.

        Args:
            sst: Slice/Service Type.
            sd: Slice Differentiator.

        Returns:
            Response from the AMF.
        """
        msg: dict[str, Any] = {
            "message": "slice_del",
            "sst": sst,
        }
        if sd is not None:
            msg["sd"] = sd
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # AMBR Management
    # ──────────────────────────────────────────────

    def ue_ambr_update(
        self,
        imsi: str,
        dl_ambr: int,
        ul_ambr: int,
    ) -> dict[str, Any]:
        """Update UE aggregate maximum bit rate.

        Args:
            imsi: IMSI of the target UE.
            dl_ambr: Downlink AMBR in kbps.
            ul_ambr: Uplink AMBR in kbps.

        Returns:
            Response from the MME/AMF.
        """
        return self._client.send({
            "message": "ue_ambr_update",
            "imsi": imsi,
            "dl_ambr": dl_ambr,
            "ul_ambr": ul_ambr,
        })

    def session_ambr_update(
        self,
        imsi: str,
        pdu_session_id: int | None = None,
        apn: str | None = None,
        dl_ambr: int | None = None,
        ul_ambr: int | None = None,
    ) -> dict[str, Any]:
        """Update PDU session AMBR.

        Args:
            imsi: IMSI of the target UE.
            pdu_session_id: PDU session ID (5G).
            apn: APN (4G).
            dl_ambr: Downlink AMBR in kbps.
            ul_ambr: Uplink AMBR in kbps.

        Returns:
            Response from the MME/AMF.
        """
        msg: dict[str, Any] = {
            "message": "session_ambr_update",
            "imsi": imsi,
        }
        if pdu_session_id is not None:
            msg["pdu_session_id"] = pdu_session_id
        if apn is not None:
            msg["apn"] = apn
        if dl_ambr is not None:
            msg["dl_ambr"] = dl_ambr
        if ul_ambr is not None:
            msg["ul_ambr"] = ul_ambr
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Utility Commands
    # ──────────────────────────────────────────────

    def cancel(self, request_id: int) -> dict[str, Any]:
        """Cancel a pending async request.

        Args:
            request_id: ID of the request to cancel.

        Returns:
            Cancel result.
        """
        return self._client.send({
            "message": "cancel",
            "request_id": request_id,
        })

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

    def license(self) -> dict[str, Any]:
        """Get license information.

        Returns:
            License details and expiration.
        """
        return self._client.send({"message": "license"})

    def monitor(
        self,
        enable: bool = True,
        events: list[str] | None = None,
    ) -> dict[str, Any]:
        """Enable or disable event monitoring.

        Args:
            enable: True to enable monitoring, False to disable.
            events: Optional list of event types to monitor.

        Returns:
            Monitor configuration result.
        """
        msg: dict[str, Any] = {
            "message": "monitor",
            "enable": enable,
        }
        if events is not None:
            msg["events"] = events
        return self._client.send(msg)

    def quit(self) -> dict[str, Any]:
        """Quit the MME/AMF service.

        Returns:
            Quit acknowledgment.
        """
        return self._client.send({"message": "quit"})

    def version(self) -> dict[str, Any]:
        """Get MME/AMF version information.

        Returns:
            Version information.
        """
        return self._client.send({"message": "version"})

    # ──────────────────────────────────────────────
    # Logging (Extended)
    # ──────────────────────────────────────────────

    def log_bin_get(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
        max_count: int | None = None,
    ) -> dict[str, Any]:
        """Get binary log entries.

        Args:
            start_time: Start timestamp.
            end_time: End timestamp.
            max_count: Maximum number of entries.

        Returns:
            Binary log entries.
        """
        msg: dict[str, Any] = {"message": "log_bin_get"}
        if start_time is not None:
            msg["start_time"] = start_time
        if end_time is not None:
            msg["end_time"] = end_time
        if max_count is not None:
            msg["max_count"] = max_count
        return self._client.send(msg)

    def log_reset(self) -> dict[str, Any]:
        """Reset the log buffer.

        Returns:
            Reset confirmation.
        """
        return self._client.send({"message": "log_reset"})
