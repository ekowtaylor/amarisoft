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
