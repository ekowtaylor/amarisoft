"""Main Amarisoft Callbox class that orchestrates all service APIs."""

from __future__ import annotations

import logging
import ssl as _ssl
from typing import Any

from .client import WebSocketClient
from .enb import ENBApi
from .ims import IMSApi
from .mme import MMEApi
from .ue import UEApi

logger = logging.getLogger(__name__)


class Callbox:
    """High-level interface to an Amarisoft Callbox system.

    Provides unified access to all Callbox services (eNB/gNB, MME/AMF,
    IMS, UE Simulator) through their respective WebSocket Remote APIs.

    Default ports (as per Amarisoft documentation)::

        MME/AMF : 9000
        eNB/gNB : 9001
        IMS     : 9002
        UE Sim  : 9003

    Example::

        cb = Callbox("192.168.1.100")
        cb.connect_all()
        ues = cb.enb.ue_get()
        cb.enb.cell_gain(cell_id=1, gain=-10)
        cb.mme.ue_detach(imsi="001010123456789")
        cb.close()

    Context manager::

        with Callbox("192.168.1.100") as cb:
            cb.enb.stats()
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        *,
        enb_port: int = ENBApi.DEFAULT_PORT,
        mme_port: int = MMEApi.DEFAULT_PORT,
        ims_port: int = IMSApi.DEFAULT_PORT,
        ue_port: int = UEApi.DEFAULT_PORT,
        password: str | None = None,
        ssl: bool = False,
        ssl_context: _ssl.SSLContext | None = None,
        timeout: float = 10.0,
        auto_reconnect: bool = False,
    ):
        """Initialize the Callbox interface.

        Args:
            host: IP address or hostname of the Amarisoft Callbox.
            enb_port: WebSocket port for eNB/gNB service.
            mme_port: WebSocket port for MME/AMF service.
            ims_port: WebSocket port for IMS service.
            ue_port: WebSocket port for UE Simulator service.
            password: Authentication password (if ``com_auth`` is
                configured on the Callbox).
            ssl: Use WSS (TLS) for connections.
            ssl_context: Custom :class:`ssl.SSLContext` (e.g. for
                self-signed certificates).
            timeout: Default timeout in seconds for WebSocket operations.
            auto_reconnect: Automatically reconnect on send failure.
        """
        self.host = host
        self.password = password
        self.ssl = ssl
        self.timeout = timeout

        kwargs: dict[str, Any] = dict(
            password=password,
            ssl=ssl,
            timeout=timeout,
            ssl_context=ssl_context,
            auto_reconnect=auto_reconnect,
        )

        # Create WebSocket clients for each service
        self._enb_client = WebSocketClient(host, enb_port, **kwargs)
        self._mme_client = WebSocketClient(host, mme_port, **kwargs)
        self._ims_client = WebSocketClient(host, ims_port, **kwargs)
        self._ue_client = WebSocketClient(host, ue_port, **kwargs)

        # Create API instances
        self.enb = ENBApi(self._enb_client)
        self.mme = MMEApi(self._mme_client)
        self.ims = IMSApi(self._ims_client)
        self.ue = UEApi(self._ue_client)

        self._clients = {
            "enb": self._enb_client,
            "mme": self._mme_client,
            "ims": self._ims_client,
            "ue": self._ue_client,
        }

    def connect_all(self) -> dict[str, dict[str, Any]]:
        """Connect to all Callbox services.

        Returns:
            Dictionary mapping service names to their ready messages.
            Services that fail to connect will have an ``"error"`` key.

        Note:
            Services that fail to connect will log a warning but won't
            prevent other services from connecting.
        """
        results: dict[str, dict[str, Any]] = {}
        for name, client in self._clients.items():
            try:
                results[name] = client.connect()
                logger.info("Connected to %s at %s", name, client.uri)
            except Exception as e:
                logger.warning(
                    "Failed to connect to %s at %s: %s", name, client.uri, e
                )
                results[name] = {"error": str(e)}
        return results

    def connect_enb(self) -> dict[str, Any]:
        """Connect to the eNB/gNB service."""
        return self._enb_client.connect()

    def connect_mme(self) -> dict[str, Any]:
        """Connect to the MME/AMF service."""
        return self._mme_client.connect()

    def connect_ims(self) -> dict[str, Any]:
        """Connect to the IMS service."""
        return self._ims_client.connect()

    def connect_ue(self) -> dict[str, Any]:
        """Connect to the UE Simulator service."""
        return self._ue_client.connect()

    def close(self) -> None:
        """Close all WebSocket connections."""
        for name, client in self._clients.items():
            try:
                client.close()
            except Exception as e:
                logger.warning("Error closing %s: %s", name, e)

    @property
    def status(self) -> dict[str, bool]:
        """Return connection status for each service."""
        return {
            name: client.connected for name, client in self._clients.items()
        }

    def send_raw(
        self,
        service: str,
        message: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a raw JSON message to a specific service.

        Useful for commands not yet wrapped by the API classes.

        Args:
            service: Target service (``"enb"``, ``"mme"``, ``"ims"``,
                ``"ue"``).
            message: Raw JSON message dictionary.

        Returns:
            The parsed response.

        Raises:
            ValueError: If the service name is invalid.
        """
        client = self._clients.get(service)
        if client is None:
            raise ValueError(
                f"Unknown service '{service}'. "
                f"Use: {list(self._clients.keys())}"
            )
        return client.send(message)

    def __enter__(self) -> Callbox:
        self.connect_all()
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        connected = sum(1 for c in self._clients.values() if c.connected)
        return f"Callbox({self.host}, {connected}/{len(self._clients)} connected)"
