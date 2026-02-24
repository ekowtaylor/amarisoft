"""UE Simulator HTTP API client."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import HTTPClient


class UEApi:
    """HTTP client for UE Simulator operations.

    Provides the same interface as the WebSocket UEApi but uses HTTP.

    Example::

        from client.http import Callbox

        cb = Callbox("http://192.168.1.80:9010")
        cb.ue.power_on()
        ue_info = cb.ue.ue_get()
    """

    def __init__(self, client: "HTTPClient"):
        self._client = client

    def version(self) -> dict[str, Any]:
        """Get UE Simulator version information."""
        return self._client.get("/ue/version")

    def help(self) -> dict[str, Any]:
        """Get list of available API commands."""
        return self._client.get("/ue/help")

    def stats(self) -> dict[str, Any]:
        """Get UE Simulator statistics.

        Returns:
            Statistics data including UE counts and session metrics.
        """
        return self._client.get("/ue/stats")

    def config_get(self) -> dict[str, Any]:
        """Get UE Simulator configuration."""
        return self._client.get("/ue/config")

    def config_set(self, **kwargs: Any) -> dict[str, Any]:
        """Set UE Simulator configuration parameters.

        Args:
            **kwargs: Configuration parameters to set.

        Returns:
            Response from the API.
        """
        return self._client.post("/ue/config", data={"config": kwargs})

    # ──────────────────────────────────────────────
    # UE Power Control
    # ──────────────────────────────────────────────

    def power_on(self, ue_id: int | None = None) -> dict[str, Any]:
        """Power on a simulated UE.

        Args:
            ue_id: Specific UE to power on. None for all UEs.

        Returns:
            Response from the API.
        """
        data = {}
        if ue_id is not None:
            data["ue_id"] = ue_id
        return self._client.post("/ue/power-on", data=data if data else None)

    def power_off(self, ue_id: int | None = None) -> dict[str, Any]:
        """Power off a simulated UE.

        Args:
            ue_id: Specific UE to power off. None for all UEs.

        Returns:
            Response from the API.
        """
        data = {}
        if ue_id is not None:
            data["ue_id"] = ue_id
        return self._client.post("/ue/power-off", data=data if data else None)

    # ──────────────────────────────────────────────
    # UE Information
    # ──────────────────────────────────────────────

    def ue_get(
        self,
        ue_id: int | None = None,
        imsi: str | None = None,
    ) -> dict[str, Any]:
        """Get UE information.

        Args:
            ue_id: Filter by UE ID.
            imsi: Filter by IMSI.

        Returns:
            UE information.
        """
        if ue_id is not None:
            return self._client.get(f"/ue/{ue_id}")

        params = {}
        if imsi:
            params["imsi"] = imsi
        return self._client.get("/ue", params=params if params else None)

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
                "dl_gbr", "ul_gbr", "dl_mbr", "ul_mbr".
            filters: Traffic flow template filters, each containing
                "direction", "id", "precedence", "components".

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {
            "ue_id": ue_id,
            "def_bearer_id": def_bearer_id,
            "qci": qci,
        }
        if gbr is not None:
            data["gbr"] = gbr
        if filters is not None:
            data["filters"] = filters
        return self._client.post(f"/ue/{ue_id}/bearer/activate", data=data)

    # ──────────────────────────────────────────────
    # UE Assistance Information (NR)
    # ──────────────────────────────────────────────

    def ue_assistance_information(
        self,
        ue_id: int,
        preferred_rrc_state: str | None = None,
    ) -> dict[str, Any]:
        """Send UE Assistance Information (5G NR).

        Args:
            ue_id: Target UE identifier.
            preferred_rrc_state: Preferred RRC state
                ("connected", "inactive", "idle").

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"ue_id": ue_id}
        if preferred_rrc_state is not None:
            data["preferred_rrc_state"] = preferred_rrc_state
        return self._client.post(f"/ue/{ue_id}/assistance-info", data=data)

    # ──────────────────────────────────────────────
    # PDN/PDU Session
    # ──────────────────────────────────────────────

    def pdn_connect(
        self,
        ue_id: int,
        apn: str | None = None,
        pdn_type: str | None = None,
    ) -> dict[str, Any]:
        """Establish PDN/PDU connection for a UE.

        Args:
            ue_id: Target UE identifier.
            apn: Access Point Name.
            pdn_type: PDN type (e.g., 'ipv4', 'ipv6', 'ipv4v6').

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"ue_id": ue_id}
        if apn:
            data["apn"] = apn
        if pdn_type:
            data["pdn_type"] = pdn_type
        return self._client.post(f"/ue/{ue_id}/pdn/connect", data=data)

    def pdn_disconnect(
        self,
        ue_id: int,
        pdn_id: int | None = None,
    ) -> dict[str, Any]:
        """Disconnect PDN/PDU for a UE.

        Args:
            ue_id: Target UE identifier.
            pdn_id: Specific PDN ID to disconnect.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"ue_id": ue_id}
        if pdn_id is not None:
            data["pdn_id"] = pdn_id
        return self._client.post(f"/ue/{ue_id}/pdn/disconnect", data=data)

    # ──────────────────────────────────────────────
    # Attach/Detach
    # ──────────────────────────────────────────────

    def attach(self, ue_id: int | None = None) -> dict[str, Any]:
        """Initiate attach procedure for a UE.

        Args:
            ue_id: Specific UE to attach. None for all UEs.

        Returns:
            Response from the API.
        """
        data = {}
        if ue_id is not None:
            data["ue_id"] = ue_id
        return self._client.post("/ue/attach", data=data if data else None)

    def detach(
        self,
        ue_id: int | None = None,
        detach_type: str = "normal",
    ) -> dict[str, Any]:
        """Initiate detach procedure for a UE.

        Args:
            ue_id: Specific UE to detach. None for all UEs.
            detach_type: Type of detach ('normal', 'power_off', 'imsi_detach').

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"detach_type": detach_type}
        if ue_id is not None:
            data["ue_id"] = ue_id
        return self._client.post("/ue/detach", data=data)

    # ──────────────────────────────────────────────
    # NAS Procedures
    # ──────────────────────────────────────────────

    def service_request(self, ue_id: int) -> dict[str, Any]:
        """Initiate service request procedure for a UE.

        Args:
            ue_id: Target UE identifier.

        Returns:
            Response from the API.
        """
        return self._client.post(f"/ue/{ue_id}/service-request")

    def tau(self, ue_id: int) -> dict[str, Any]:
        """Initiate Tracking Area Update (TAU) for a UE.

        Args:
            ue_id: Target UE identifier.

        Returns:
            Response from the API.
        """
        return self._client.post(f"/ue/{ue_id}/tau")

    # ──────────────────────────────────────────────
    # Cell Selection
    # ──────────────────────────────────────────────

    def cell_search(self, ue_id: int) -> dict[str, Any]:
        """Trigger cell search for a UE.

        Args:
            ue_id: Target UE identifier.

        Returns:
            Response from the API.
        """
        return self._client.post(f"/ue/{ue_id}/cell-search")

    def cell_select(self, ue_id: int, cell_id: int) -> dict[str, Any]:
        """Select a specific cell for a UE.

        Args:
            ue_id: Target UE identifier.
            cell_id: Cell ID to select.

        Returns:
            Response from the API.
        """
        return self._client.post(f"/ue/{ue_id}/cell-select", data={"cell_id": cell_id})

    # ──────────────────────────────────────────────
    # Logging
    # ──────────────────────────────────────────────

    def log_get(
        self,
        min_: int | None = None,
        max_: int | None = None,
        layer: str | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Get log entries.

        Args:
            min_: Minimum log index.
            max_: Maximum log index.
            layer: Filter by layer.
            timeout: Query timeout in seconds.

        Returns:
            Log entries.
        """
        params = {}
        if min_ is not None:
            params["min"] = min_
        if max_ is not None:
            params["max"] = max_
        if layer:
            params["layer"] = layer
        if timeout is not None:
            params["timeout"] = timeout
        return self._client.get("/ue/logs", params=params if params else None)

    def log_set(
        self,
        layers: dict[str, Any] | None = None,
        max_size: int | None = None,
    ) -> dict[str, Any]:
        """Configure logging.

        Args:
            layers: Per-layer log settings.
            max_size: Maximum log buffer size.

        Returns:
            Response from the API.
        """
        data = {}
        if layers:
            data["layers"] = layers
        if max_size:
            data["max_size"] = max_size
        return self._client.post("/ue/logs/config", data=data)

    def license(self) -> dict[str, Any]:
        """Get license information."""
        return self._client.get("/ue/license")

    def quit(self) -> dict[str, Any]:
        """Terminate the UE Simulator process. Use with caution!"""
        return self._client.post("/ue/quit")
