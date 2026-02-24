"""Connection manager for Amarisoft WebSocket services.

Provides a centralized manager for maintaining connections to all
Amarisoft services (eNB, MME, IMS, UE) with lazy initialization
and automatic reconnection support.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from client.websocket.client import WebSocketClient
from client.websocket.enb import ENBApi
from client.websocket.exceptions import AmariError
from client.websocket.ims import IMSApi
from client.websocket.mme import MMEApi
from client.websocket.ue import UEApi

from .config import Settings
from .exceptions import map_amarisoft_exception

if TYPE_CHECKING:
    from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Status information for a single Amarisoft service."""

    name: str
    port: int
    connected: bool = False
    version: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "port": self.port,
            "connected": self.connected,
            "version": self.version,
            "error": self.error,
        }


@dataclass
class CallboxStatus:
    """Overall status of the Amarisoft callbox connection."""

    host: str
    services: dict[str, ServiceStatus] = field(default_factory=dict)

    @property
    def healthy(self) -> bool:
        """Return True if at least one service is connected."""
        return any(s.connected for s in self.services.values())

    @property
    def all_connected(self) -> bool:
        """Return True if all services are connected."""
        return all(s.connected for s in self.services.values())

    @property
    def connected_count(self) -> int:
        """Return the number of connected services."""
        return sum(1 for s in self.services.values() if s.connected)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "host": self.host,
            "healthy": self.healthy,
            "all_connected": self.all_connected,
            "connected_count": self.connected_count,
            "total_services": len(self.services),
            "services": {
                name: status.to_dict() for name, status in self.services.items()
            },
        }


class CallboxManager:
    """Manages WebSocket connections to Amarisoft callbox services.

    Provides lazy initialization of connections - services are only
    connected when first accessed. Supports automatic reconnection
    on failure.

    Thread-safe for concurrent access from multiple HTTP request handlers.

    Example::

        manager = CallboxManager(settings)

        # Connections are established lazily
        stats = manager.enb.stats()

        # Check status
        status = manager.get_status()
        print(f"Connected: {status.connected_count}/{status.total_services}")

        # Cleanup
        manager.close_all()
    """

    def __init__(self, settings: Settings):
        """Initialize the CallboxManager.

        Args:
            settings: Configuration settings for the service.
        """
        self._settings = settings
        self._lock = threading.RLock()

        # WebSocket clients (lazy initialized)
        self._enb_client: WebSocketClient | None = None
        self._mme_client: WebSocketClient | None = None
        self._ims_client: WebSocketClient | None = None
        self._ue_client: WebSocketClient | None = None

        # Service API wrappers (lazy initialized)
        self._enb_api: ENBApi | None = None
        self._mme_api: MMEApi | None = None
        self._ims_api: IMSApi | None = None
        self._ue_api: UEApi | None = None

        logger.info(
            "CallboxManager initialized for %s",
            settings.callbox_host,
        )

    def _create_client(self, port: int) -> WebSocketClient:
        """Create a WebSocket client with common settings.

        Args:
            port: The port number for the service.

        Returns:
            Configured WebSocketClient instance.
        """
        return WebSocketClient(
            host=self._settings.callbox_host,
            port=port,
            password=self._settings.ws_password,
            ssl=self._settings.ssl,
            ssl_verify=self._settings.ssl_verify,
            timeout=self._settings.ws_timeout,
            auto_reconnect=self._settings.auto_reconnect,
        )

    def _ensure_client(
        self,
        client_attr: str,
        api_attr: str,
        port: int,
        api_class: type,
    ) -> Any:
        """Ensure a client is connected and return the API wrapper.

        Args:
            client_attr: Name of the client attribute (e.g., "_enb_client").
            api_attr: Name of the API attribute (e.g., "_enb_api").
            port: Port number for the service.
            api_class: API wrapper class to instantiate.

        Returns:
            The API wrapper instance.

        Raises:
            APIError: If connection fails.
        """
        with self._lock:
            client = getattr(self, client_attr)
            api = getattr(self, api_attr)

            if api is not None and client is not None and client.connected:
                return api

            # Create new client if needed
            if client is None:
                client = self._create_client(port)
                setattr(self, client_attr, client)

            # Connect if not connected
            if not client.connected:
                try:
                    client.connect()
                    logger.info(
                        "Connected to %s:%d",
                        self._settings.callbox_host,
                        port,
                    )
                except AmariError as e:
                    service_name = api_class.__name__.replace("Api", "").upper()
                    logger.error(
                        "Failed to connect to %s on port %d: %s",
                        service_name,
                        port,
                        e,
                    )
                    raise map_amarisoft_exception(e, service_name) from e

            # Create API wrapper if needed
            if api is None:
                api = api_class(client)
                setattr(self, api_attr, api)

            return api

    @property
    def enb(self) -> ENBApi:
        """Get the eNB/gNB API, connecting if necessary.

        Returns:
            ENBApi instance for eNB/gNB operations.

        Raises:
            ServiceUnavailableError: If connection fails.
        """
        return self._ensure_client(
            "_enb_client",
            "_enb_api",
            self._settings.enb_port,
            ENBApi,
        )

    @property
    def mme(self) -> MMEApi:
        """Get the MME/AMF API, connecting if necessary.

        Returns:
            MMEApi instance for MME/AMF operations.

        Raises:
            ServiceUnavailableError: If connection fails.
        """
        return self._ensure_client(
            "_mme_client",
            "_mme_api",
            self._settings.mme_port,
            MMEApi,
        )

    @property
    def ims(self) -> IMSApi:
        """Get the IMS API, connecting if necessary.

        Returns:
            IMSApi instance for IMS operations.

        Raises:
            ServiceUnavailableError: If connection fails.
        """
        return self._ensure_client(
            "_ims_client",
            "_ims_api",
            self._settings.ims_port,
            IMSApi,
        )

    @property
    def ue(self) -> UEApi:
        """Get the UE Simulator API, connecting if necessary.

        Returns:
            UEApi instance for UE Simulator operations.

        Raises:
            ServiceUnavailableError: If connection fails.
        """
        return self._ensure_client(
            "_ue_client",
            "_ue_api",
            self._settings.ue_port,
            UEApi,
        )

    def _get_service_status(
        self,
        name: str,
        client: WebSocketClient | None,
        api: Any,
        port: int,
    ) -> ServiceStatus:
        """Get status for a single service.

        Args:
            name: Service name.
            client: WebSocket client instance.
            api: API wrapper instance.
            port: Service port number.

        Returns:
            ServiceStatus for the service.
        """
        status = ServiceStatus(name=name, port=port)

        if client is None or not client.connected:
            status.connected = False
            status.error = "Not connected"
            return status

        status.connected = True

        # Try to get version info
        try:
            if api is not None:
                version_info = api.version()
                status.version = version_info.get("version")
        except AmariError as e:
            status.error = str(e)
        except Exception as e:
            status.error = f"Unexpected error: {e}"

        return status

    def get_status(self) -> CallboxStatus:
        """Get the connection status of all services.

        Returns:
            CallboxStatus with status of all services.
        """
        with self._lock:
            status = CallboxStatus(host=self._settings.callbox_host)

            status.services["enb"] = self._get_service_status(
                "eNB/gNB",
                self._enb_client,
                self._enb_api,
                self._settings.enb_port,
            )
            status.services["mme"] = self._get_service_status(
                "MME/AMF",
                self._mme_client,
                self._mme_api,
                self._settings.mme_port,
            )
            status.services["ims"] = self._get_service_status(
                "IMS",
                self._ims_client,
                self._ims_api,
                self._settings.ims_port,
            )
            status.services["ue"] = self._get_service_status(
                "UE Simulator",
                self._ue_client,
                self._ue_api,
                self._settings.ue_port,
            )

            return status

    def check_service(self, service: str) -> ServiceStatus:
        """Check connection status of a specific service.

        Attempts to connect if not already connected.

        Args:
            service: Service name ("enb", "mme", "ims", "ue").

        Returns:
            ServiceStatus for the requested service.

        Raises:
            ValueError: If service name is invalid.
        """
        service = service.lower()
        service_map = {
            "enb": (
                "eNB/gNB",
                self._settings.enb_port,
                "_enb_client",
                "_enb_api",
                ENBApi,
            ),
            "mme": (
                "MME/AMF",
                self._settings.mme_port,
                "_mme_client",
                "_mme_api",
                MMEApi,
            ),
            "ims": (
                "IMS",
                self._settings.ims_port,
                "_ims_client",
                "_ims_api",
                IMSApi,
            ),
            "ue": (
                "UE Simulator",
                self._settings.ue_port,
                "_ue_client",
                "_ue_api",
                UEApi,
            ),
        }

        if service not in service_map:
            raise ValueError(
                f"Unknown service: {service}. "
                f"Valid services: {list(service_map.keys())}"
            )

        name, port, client_attr, api_attr, api_class = service_map[service]
        status = ServiceStatus(name=name, port=port)

        try:
            api = self._ensure_client(client_attr, api_attr, port, api_class)
            status.connected = True

            # Get version
            version_info = api.version()
            status.version = version_info.get("version")

        except Exception as e:
            status.connected = False
            status.error = str(e)

        return status

    def connect_all(self) -> CallboxStatus:
        """Attempt to connect to all services.

        Returns:
            CallboxStatus with connection results.
        """
        errors: list[str] = []

        # Attempt to connect each service, collecting errors
        for service in ("enb", "mme", "ims", "ue"):
            try:
                self.check_service(service)
            except Exception as e:
                errors.append(f"{service}: {e}")
                logger.warning("Failed to connect to %s: %s", service, e)

        return self.get_status()

    def disconnect_service(self, service: str) -> None:
        """Disconnect a specific service.

        Args:
            service: Service name ("enb", "mme", "ims", "ue").

        Raises:
            ValueError: If service name is invalid.
        """
        service = service.lower()
        client_map = {
            "enb": "_enb_client",
            "mme": "_mme_client",
            "ims": "_ims_client",
            "ue": "_ue_client",
        }
        api_map = {
            "enb": "_enb_api",
            "mme": "_mme_api",
            "ims": "_ims_api",
            "ue": "_ue_api",
        }

        if service not in client_map:
            raise ValueError(
                f"Unknown service: {service}. "
                f"Valid services: {list(client_map.keys())}"
            )

        with self._lock:
            client = getattr(self, client_map[service])
            if client is not None:
                try:
                    client.close()
                except Exception as e:
                    logger.warning("Error closing %s client: %s", service, e)

                setattr(self, client_map[service], None)
                setattr(self, api_map[service], None)
                logger.info("Disconnected from %s", service)

    def close_all(self) -> None:
        """Close all WebSocket connections."""
        with self._lock:
            for service in ("enb", "mme", "ims", "ue"):
                try:
                    self.disconnect_service(service)
                except Exception as e:
                    logger.warning("Error closing %s: %s", service, e)

        logger.info("All connections closed")

    def reconnect_service(self, service: str) -> ServiceStatus:
        """Reconnect to a specific service.

        Args:
            service: Service name ("enb", "mme", "ims", "ue").

        Returns:
            ServiceStatus after reconnection attempt.
        """
        self.disconnect_service(service)
        return self.check_service(service)

    def __enter__(self) -> CallboxManager:
        """Context manager entry - connect to all services."""
        self.connect_all()
        return self

    def __exit__(
        self,
        _exc_type: type | None,
        _exc_val: BaseException | None,
        _exc_tb: Any,
    ) -> None:
        """Context manager exit - close all connections."""
        self.close_all()

    def __repr__(self) -> str:
        status = self.get_status()
        return (
            f"CallboxManager({self._settings.callbox_host}, "
            f"{status.connected_count}/{len(status.services)} connected)"
        )


# Global manager instance (set during app startup)
_manager: CallboxManager | None = None


def get_manager() -> CallboxManager:
    """Get the global CallboxManager instance.

    This is used as a FastAPI dependency to inject the manager
    into route handlers.

    Returns:
        The global CallboxManager instance.

    Raises:
        RuntimeError: If the manager has not been initialized.
    """
    if _manager is None:
        raise RuntimeError(
            "CallboxManager not initialized. "
            "Ensure the application startup has completed."
        )
    return _manager


def set_manager(manager: CallboxManager) -> None:
    """Set the global CallboxManager instance.

    Called during application startup.

    Args:
        manager: The CallboxManager instance to use globally.
    """
    global _manager
    _manager = manager


def clear_manager() -> None:
    """Clear the global CallboxManager instance.

    Called during application shutdown.
    """
    global _manager
    if _manager is not None:
        _manager.close_all()
        _manager = None
