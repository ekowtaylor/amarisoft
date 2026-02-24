"""MME/AMF (core network) HTTP API client."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import HTTPClient


class MMEApi:
    """HTTP client for MME/AMF (core network) operations.

    Provides the same interface as the WebSocket MMEApi but uses HTTP.

    Example::

        from client.http import Callbox

        cb = Callbox("http://192.168.1.80:9010")
        stats = cb.mme.stats()
        ue_info = cb.mme.ue_get()
    """

    def __init__(self, client: "HTTPClient"):
        self._client = client

    def version(self) -> dict[str, Any]:
        """Get MME/AMF version information."""
        return self._client.get("/mme/version")

    def help(self) -> dict[str, Any]:
        """Get list of available API commands."""
        return self._client.get("/mme/help")

    def stats(self) -> dict[str, Any]:
        """Get MME/AMF statistics.

        Returns:
            Statistics data including UE counts and network metrics.
        """
        return self._client.get("/mme/stats")

    def config_get(self) -> dict[str, Any]:
        """Get MME/AMF configuration."""
        return self._client.get("/mme/config")

    def config_set(self, **kwargs: Any) -> dict[str, Any]:
        """Set MME/AMF configuration parameters.

        Args:
            **kwargs: Configuration parameters to set.

        Returns:
            Response from the API.
        """
        return self._client.post("/mme/config", data={"config": kwargs})

    def ue_get(
        self,
        imsi: str | None = None,
        mme_ue_id: int | None = None,
    ) -> dict[str, Any]:
        """Get UE information from the core network.

        Args:
            imsi: Filter by IMSI.
            mme_ue_id: Filter by MME UE ID.

        Returns:
            UE information.
        """
        if mme_ue_id is not None:
            return self._client.get(f"/mme/ue/{mme_ue_id}")

        params = {}
        if imsi:
            params["imsi"] = imsi
        return self._client.get("/mme/ue", params=params if params else None)

    def ue_release(
        self,
        imsi: str,
        cause: str | None = None,
    ) -> dict[str, Any]:
        """Release a UE from the network.

        Args:
            imsi: IMSI of the UE to release.
            cause: Release cause.

        Returns:
            Response from the API.
        """
        data = {"imsi": imsi}
        if cause:
            data["cause"] = cause
        return self._client.post("/mme/ue/release", data=data)

    def pdn_connect(
        self,
        imsi: str,
        apn: str | None = None,
        pdn_type: str | None = None,
    ) -> dict[str, Any]:
        """Establish PDN connection for a UE.

        Args:
            imsi: IMSI of the UE.
            apn: Access Point Name.
            pdn_type: PDN type (e.g., 'ipv4', 'ipv6', 'ipv4v6').

        Returns:
            Response from the API.
        """
        data = {"imsi": imsi}
        if apn:
            data["apn"] = apn
        if pdn_type:
            data["pdn_type"] = pdn_type
        return self._client.post("/mme/pdn/connect", data=data)

    def pdn_disconnect(
        self,
        imsi: str,
        apn: str | None = None,
    ) -> dict[str, Any]:
        """Disconnect PDN for a UE.

        Args:
            imsi: IMSI of the UE.
            apn: Access Point Name (if specific APN to disconnect).

        Returns:
            Response from the API.
        """
        data = {"imsi": imsi}
        if apn:
            data["apn"] = apn
        return self._client.post("/mme/pdn/disconnect", data=data)

    def bearer_activate(
        self,
        imsi: str,
        qci: int,
        apn: str | None = None,
        gbr_dl: int | None = None,
        gbr_ul: int | None = None,
        mbr_dl: int | None = None,
        mbr_ul: int | None = None,
    ) -> dict[str, Any]:
        """Activate a dedicated bearer for a UE.

        Args:
            imsi: IMSI of the UE.
            qci: QoS Class Identifier.
            apn: Access Point Name.
            gbr_dl: Guaranteed bit rate (downlink) in kbps.
            gbr_ul: Guaranteed bit rate (uplink) in kbps.
            mbr_dl: Maximum bit rate (downlink) in kbps.
            mbr_ul: Maximum bit rate (uplink) in kbps.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"imsi": imsi, "qci": qci}
        if apn:
            data["apn"] = apn
        if gbr_dl is not None:
            data["gbr_dl"] = gbr_dl
        if gbr_ul is not None:
            data["gbr_ul"] = gbr_ul
        if mbr_dl is not None:
            data["mbr_dl"] = mbr_dl
        if mbr_ul is not None:
            data["mbr_ul"] = mbr_ul
        return self._client.post("/mme/bearer/activate", data=data)

    def bearer_deactivate(
        self,
        imsi: str,
        bearer_id: int,
    ) -> dict[str, Any]:
        """Deactivate a bearer for a UE.

        Args:
            imsi: IMSI of the UE.
            bearer_id: Bearer ID to deactivate.

        Returns:
            Response from the API.
        """
        return self._client.post(
            "/mme/bearer/deactivate",
            data={"imsi": imsi, "bearer_id": bearer_id},
        )

    def bearer_modify(
        self,
        imsi: str,
        bearer_id: int,
        qci: int | None = None,
        gbr_dl: int | None = None,
        gbr_ul: int | None = None,
        mbr_dl: int | None = None,
        mbr_ul: int | None = None,
    ) -> dict[str, Any]:
        """Modify an existing bearer for a UE.

        Args:
            imsi: IMSI of the UE.
            bearer_id: Bearer ID to modify.
            qci: New QoS Class Identifier.
            gbr_dl: New guaranteed bit rate (downlink) in kbps.
            gbr_ul: New guaranteed bit rate (uplink) in kbps.
            mbr_dl: New maximum bit rate (downlink) in kbps.
            mbr_ul: New maximum bit rate (uplink) in kbps.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"imsi": imsi, "bearer_id": bearer_id}
        if qci is not None:
            data["qci"] = qci
        if gbr_dl is not None:
            data["gbr_dl"] = gbr_dl
        if gbr_ul is not None:
            data["gbr_ul"] = gbr_ul
        if mbr_dl is not None:
            data["mbr_dl"] = mbr_dl
        if mbr_ul is not None:
            data["mbr_ul"] = mbr_ul
        return self._client.post("/mme/bearer/modify", data=data)

    def paging(
        self,
        imsi: str,
        domain: str = "ps",
    ) -> dict[str, Any]:
        """Send paging to a UE.

        Args:
            imsi: IMSI of UE to page.
            domain: Paging domain ('cs' or 'ps').

        Returns:
            Response from the API.
        """
        return self._client.post(
            "/mme/paging",
            data={"imsi": imsi, "domain": domain},
        )

    def detach(
        self,
        imsi: str,
        detach_type: str = "network",
        cause: str | None = None,
    ) -> dict[str, Any]:
        """Detach a UE from the network.

        Args:
            imsi: IMSI of the UE.
            detach_type: Type of detach ('network' or 'ue').
            cause: Detach cause.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"imsi": imsi, "detach_type": detach_type}
        if cause:
            data["cause"] = cause
        return self._client.post("/mme/detach", data=data)

    def subscribers_get(self) -> dict[str, Any]:
        """Get list of configured subscribers.

        Returns:
            Subscriber list.
        """
        return self._client.get("/mme/subscribers")

    def subscribers_add(
        self,
        imsi: str,
        key: str,
        opc: str | None = None,
        apn: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Add a subscriber to the HSS.

        Args:
            imsi: IMSI of the subscriber.
            key: Authentication key (K).
            opc: Operator key (OPc).
            apn: Default APN.
            **kwargs: Additional subscriber parameters.

        Returns:
            Response from the API.
        """
        data: dict[str, Any] = {"imsi": imsi, "key": key}
        if opc:
            data["opc"] = opc
        if apn:
            data["apn"] = apn
        data.update(kwargs)
        return self._client.post("/mme/subscribers", data=data)

    def subscribers_delete(self, imsi: str) -> dict[str, Any]:
        """Delete a subscriber from the HSS.

        Args:
            imsi: IMSI of the subscriber to delete.

        Returns:
            Response from the API.
        """
        return self._client.delete(f"/mme/subscribers/{imsi}")

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
            layer: Filter by layer (NAS, S1AP, etc.).
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
        return self._client.get("/mme/logs", params=params if params else None)

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
        return self._client.post("/mme/logs/config", data=data)

    def license(self) -> dict[str, Any]:
        """Get license information."""
        return self._client.get("/mme/license")

    def quit(self) -> dict[str, Any]:
        """Terminate the MME/AMF process. Use with caution!"""
        return self._client.post("/mme/quit")
