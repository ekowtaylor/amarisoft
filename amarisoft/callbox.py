"""Main Amarisoft Callbox class that orchestrates all service APIs."""

from __future__ import annotations

import logging
import ssl as _ssl
from typing import Any, TYPE_CHECKING

from .client import WebSocketClient
from .enb import ENBApi
from .ims import IMSApi
from .mme import MMEApi
from .ue import UEApi

if TYPE_CHECKING:
    from .capabilities import CapabilityChecker, DeviceCapabilities

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

    With capability validation::

        from amarisoft.capabilities import ValidationContext

        with Callbox("192.168.1.80", ims_port=9003) as cb:
            with ValidationContext(cb) as ctx:
                # Operations are validated against device capabilities
                cb.enb.rf(tx_gain=60)  # Validated
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
        ssl_verify: bool = False,
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
            ssl_verify: Verify the server's TLS certificate. Defaults to
                ``False`` so that self-signed certificates on the
                Callbox are accepted without extra configuration.
        """
        self.host = host
        self.password = password
        self.ssl = ssl
        self.timeout = timeout

        # Capability checker (set by ValidationContext or enable_validation)
        self._capability_checker: CapabilityChecker | None = None
        self._capabilities: DeviceCapabilities | None = None

        kwargs: dict[str, Any] = dict(
            password=password,
            ssl=ssl,
            timeout=timeout,
            ssl_context=ssl_context,
            auto_reconnect=auto_reconnect,
            ssl_verify=ssl_verify,
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

        # Set callbox reference on API instances for validation
        self.enb._callbox = self
        self.mme._callbox = self
        self.ims._callbox = self
        self.ue._callbox = self

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

    # Alias for close() for consistency
    disconnect_all = close

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

    # ──────────────────────────────────────────────
    # Capability Management
    # ──────────────────────────────────────────────

    def discover_capabilities(self) -> "DeviceCapabilities":
        """Discover and cache device capabilities.

        Returns:
            DeviceCapabilities instance with discovered constraints.

        Note:
            Requires at least one service to be connected.
        """
        from .capabilities import DeviceCapabilities

        self._capabilities = DeviceCapabilities.from_callbox(self)
        return self._capabilities

    @property
    def capabilities(self) -> "DeviceCapabilities | None":
        """Return cached device capabilities, or None if not discovered."""
        return self._capabilities

    def enable_validation(
        self,
        capabilities: "DeviceCapabilities | None" = None,
    ) -> "CapabilityChecker":
        """Enable parameter validation on this Callbox.

        Args:
            capabilities: Optional capabilities to use. If None,
                discovers from the connected device.

        Returns:
            The CapabilityChecker instance.

        Example::

            cb = Callbox("192.168.1.80")
            cb.connect_all()
            checker = cb.enable_validation()
            # Now API calls will be validated
        """
        from .capabilities import CapabilityChecker

        if capabilities is None:
            capabilities = self.discover_capabilities()

        self._capabilities = capabilities
        self._capability_checker = CapabilityChecker(capabilities)
        return self._capability_checker

    def disable_validation(self) -> None:
        """Disable parameter validation."""
        self._capability_checker = None

    @property
    def validation_enabled(self) -> bool:
        """Return True if validation is enabled."""
        return self._capability_checker is not None

    def __enter__(self) -> Callbox:
        self.connect_all()
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        connected = sum(1 for c in self._clients.values() if c.connected)
        validation = " [validation]" if self.validation_enabled else ""
        return f"Callbox({self.host}, {connected}/{len(self._clients)} connected{validation})"
