"""eNB/gNB HTTP API client."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import HTTPClient


class ENBApi:
    """HTTP client for eNB/gNB (base station) operations.

    Provides the same interface as the WebSocket ENBApi but uses HTTP.

    Example::

        from client.http import Callbox

        cb = Callbox("http://192.168.1.80:9010")
        stats = cb.enb.stats()
        config = cb.enb.config_get()
    """

    def __init__(self, client: "HTTPClient"):
        self._client = client

    def version(self) -> dict[str, Any]:
        """Get eNB/gNB version information."""
        return self._client.get("/enb/version")

    def help(self) -> dict[str, Any]:
        """Get list of available API commands."""
        return self._client.get("/enb/help")

    def stats(self, samples: bool = False, rf: bool = False) -> dict[str, Any]:
        """Get eNB/gNB statistics.

        Args:
            samples: Include sample data.
            rf: Include RF statistics.

        Returns:
            Statistics data including cells and UE metrics.
        """
        params = {}
        if samples:
            params["samples"] = "true"
        if rf:
            params["rf"] = "true"
        return self._client.get("/enb/stats", params=params if params else None)

    def config_get(self) -> dict[str, Any]:
        """Get eNB/gNB configuration."""
        return self._client.get("/enb/config")

    def config_set(self, **kwargs: Any) -> dict[str, Any]:
        """Set eNB/gNB configuration parameters.

        Args:
            **kwargs: Configuration parameters to set.

        Returns:
            Response from the API.
        """
        return self._client.post("/enb/config", data={"config": kwargs})

    def ue_get(
        self,
        imsi: str | None = None,
        enb_ue_id: int | None = None,
    ) -> dict[str, Any]:
        """Get UE information.

        Args:
            imsi: Filter by IMSI.
            enb_ue_id: Filter by eNB UE ID.

        Returns:
            UE information.
        """
        if enb_ue_id is not None:
            return self._client.get(f"/enb/ue/{enb_ue_id}")

        params = {}
        if imsi:
            params["imsi"] = imsi
        return self._client.get("/enb/ue", params=params if params else None)

    def rrc_release(
        self,
        enb_ue_id: int,
        cause: str | None = None,
        redirect_freq: int | None = None,
    ) -> dict[str, Any]:
        """Release RRC connection for a UE.

        Args:
            enb_ue_id: The eNB UE ID.
            cause: Release cause.
            redirect_freq: Redirect frequency (EARFCN).

        Returns:
            Response from the API.
        """
        data = {}
        if cause:
            data["cause"] = cause
        if redirect_freq:
            data["redirect_freq"] = redirect_freq
        return self._client.post(
            f"/enb/ue/{enb_ue_id}/rrc-release",
            data=data if data else None,
        )

    def handover(
        self,
        enb_ue_id: int,
        target_cell_id: int,
        target_pci: int | None = None,
    ) -> dict[str, Any]:
        """Trigger handover for a UE.

        Args:
            enb_ue_id: The eNB UE ID.
            target_cell_id: Target cell ID for handover.
            target_pci: Target Physical Cell ID.

        Returns:
            Response from the API.
        """
        data = {"target_cell_id": target_cell_id}
        if target_pci is not None:
            data["target_pci"] = target_pci
        return self._client.post(f"/enb/ue/{enb_ue_id}/handover", data=data)

    def cells_get(self, cell_id: int | None = None) -> dict[str, Any]:
        """Get cell information.

        Args:
            cell_id: Specific cell ID, or None for all cells.

        Returns:
            Cell information.
        """
        if cell_id is not None:
            return self._client.get(f"/enb/cells/{cell_id}")
        return self._client.get("/enb/cells")

    def cell_gain(self, cell_id: int, gain: float) -> dict[str, Any]:
        """Set cell gain (attenuation).

        Args:
            cell_id: The cell ID.
            gain: Gain value in dB (-140 to 0).

        Returns:
            Response from the API.
        """
        return self._client.post(f"/enb/cells/{cell_id}/gain", data={"gain": gain})

    def cell_activate(self, cell_id: int) -> dict[str, Any]:
        """Activate a cell.

        Args:
            cell_id: The cell ID to activate.

        Returns:
            Response from the API.
        """
        return self._client.post(f"/enb/cells/{cell_id}/activate")

    def cell_deactivate(self, cell_id: int) -> dict[str, Any]:
        """Deactivate a cell.

        Args:
            cell_id: The cell ID to deactivate.

        Returns:
            Response from the API.
        """
        return self._client.post(f"/enb/cells/{cell_id}/deactivate")

    def mib_update(self, cell_id: int) -> dict[str, Any]:
        """Trigger MIB update for a cell."""
        return self._client.post(f"/enb/cells/{cell_id}/mib-update")

    def sib_update(self, cell_id: int) -> dict[str, Any]:
        """Trigger SIB update for a cell."""
        return self._client.post(f"/enb/cells/{cell_id}/sib-update")

    def paging(self, imsi: str, domain: str = "ps") -> dict[str, Any]:
        """Send paging to a UE.

        Args:
            imsi: IMSI of UE to page.
            domain: Paging domain ('cs' or 'ps').

        Returns:
            Response from the API.
        """
        return self._client.post("/enb/paging", data={"imsi": imsi, "domain": domain})

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
            layer: Filter by layer (PHY, RRC, etc.).
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
        return self._client.get("/enb/logs", params=params if params else None)

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
        return self._client.post("/enb/logs/config", data=data)

    def license(self) -> dict[str, Any]:
        """Get license information."""
        return self._client.get("/enb/license")

    def quit(self) -> dict[str, Any]:
        """Terminate the eNB/gNB process. Use with caution!"""
        return self._client.post("/enb/quit")
