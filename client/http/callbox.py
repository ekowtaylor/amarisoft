"""High-level Callbox HTTP client that orchestrates all service APIs."""

from __future__ import annotations

from typing import Any

from .client import HTTPClient
from .enb import ENBApi
from .mme import MMEApi
from .ims import IMSApi
from .ue import UEApi


class Callbox:
    """High-level HTTP client for Amarisoft Callbox.

    Provides a unified interface to all Amarisoft services via HTTP REST API.
    This mirrors the WebSocket Callbox class but uses HTTP transport.

    Example::

        from client.http import Callbox

        # Connect to the REST API service
        cb = Callbox("http://192.168.1.80:9010")

        # Get eNB statistics
        stats = cb.enb.stats()

        # Configure a cell
        cb.enb.cell_gain(cell_id=1, gain=-10.0)

        # Get MME UE information
        ue_info = cb.mme.ue_get()

        # Send an SMS via IMS
        cb.ims.send_sms(impu="sip:user@domain", text="Hello!")

        # Control simulated UEs
        cb.ue.power_on()

    Args:
        base_url: Base URL of the REST API service (e.g., "http://192.168.1.80:9010").
        timeout: Request timeout in seconds (default: 30.0).
        retries: Number of retry attempts for failed requests (default: 3).
        api_key: Optional API key for authentication.

    Attributes:
        enb: eNB/gNB (base station) API.
        mme: MME/AMF (core network) API.
        ims: IMS (IP Multimedia Subsystem) API.
        ue: UE Simulator API.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retries: int = 3,
        api_key: str | None = None,
    ):
        self._client = HTTPClient(
            base_url=base_url,
            timeout=timeout,
            retries=retries,
            api_key=api_key,
        )

        # Initialize service APIs
        self._enb = ENBApi(self._client)
        self._mme = MMEApi(self._client)
        self._ims = IMSApi(self._client)
        self._ue = UEApi(self._client)

    @property
    def enb(self) -> ENBApi:
        """eNB/gNB (base station) API."""
        return self._enb

    @property
    def mme(self) -> MMEApi:
        """MME/AMF (core network) API."""
        return self._mme

    @property
    def ims(self) -> IMSApi:
        """IMS (IP Multimedia Subsystem) API."""
        return self._ims

    @property
    def ue(self) -> UEApi:
        """UE Simulator API."""
        return self._ue

    @property
    def base_url(self) -> str:
        """Get the base URL of the REST API service."""
        return self._client._base_url

    def health_check(self) -> dict[str, Any]:
        """Check if the REST API service is healthy.

        Returns:
            Health status including service version and uptime.
        """
        return self._client.health_check()

    def system_info(self) -> dict[str, Any]:
        """Get system-wide information.

        Returns:
            System information including all service statuses.
        """
        return self._client.get("/system/info")

    def system_restart(self, service: str | None = None) -> dict[str, Any]:
        """Restart a service or the entire system.

        Args:
            service: Specific service to restart ('enb', 'mme', 'ims', 'ue').
                    None to restart all services.

        Returns:
            Response from the API.
        """
        data = {}
        if service:
            data["service"] = service
        return self._client.post("/system/restart", data=data if data else None)

    def __repr__(self) -> str:
        return f"Callbox('{self._client._base_url}')"

    def __enter__(self) -> "Callbox":
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self._client.close()

    def close(self) -> None:
        """Close the HTTP client session."""
        self._client.close()
