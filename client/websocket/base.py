"""Base class for Amarisoft service APIs with shared functionality."""

from __future__ import annotations

from typing import Any

from .client import WebSocketClient


class ServiceApi:
    """Base class providing methods common to all Amarisoft services.

    Subclasses should set ``DEFAULT_PORT`` and add service-specific methods.
    """

    DEFAULT_PORT: int = 0

    def __init__(self, client: WebSocketClient):
        self._client = client

    # ──────────────────────────────────────────────
    # Configuration
    # ──────────────────────────────────────────────

    def config_get(self) -> dict[str, Any]:
        """Retrieve the current service configuration."""
        return self._client.send({"message": "config_get"})

    def config_set(self, **params: Any) -> dict[str, Any]:
        """Set service configuration parameters.

        Args:
            **params: Key-value configuration parameters.
        """
        msg: dict[str, Any] = {"message": "config_set"}
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Statistics
    # ──────────────────────────────────────────────

    def stats(self, **params: Any) -> dict[str, Any]:
        """Retrieve service statistics.

        Args:
            **params: Optional parameters (e.g., samples=True, rf=True
                      on the eNB service).
        """
        msg: dict[str, Any] = {"message": "stats"}
        msg.update(params)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # UE Queries
    # ──────────────────────────────────────────────

    def ue_get(self, **filters: Any) -> dict[str, Any]:
        """Get information about connected / simulated UEs.

        Args:
            **filters: Optional filters (e.g., enb_ue_id, imsi).
        """
        msg: dict[str, Any] = {"message": "ue_get"}
        msg.update(filters)
        return self._client.send(msg)

    # ──────────────────────────────────────────────
    # Logging
    # ──────────────────────────────────────────────

    def log_get(
        self,
        min_: int | None = None,
        max_: int | None = None,
        timeout: float | None = None,
        layer: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve log entries maintained in memory.

        Args:
            min_: Minimum log index to return.
            max_: Maximum log index to return.
            timeout: Timeout for the log query in seconds.
            layer: Filter logs by layer name (e.g., ``"PHY"``, ``"RRC"``).
        """
        msg: dict[str, Any] = {"message": "log_get"}
        if min_ is not None:
            msg["min"] = min_
        if max_ is not None:
            msg["max"] = max_
        if timeout is not None:
            msg["timeout"] = timeout
        if layer is not None:
            msg["layer"] = layer
        return self._client.send(msg)

    def log_set(
        self,
        layers: dict[str, dict[str, Any]] | None = None,
        **params: Any,
    ) -> dict[str, Any]:
        """Configure logging options.

        Logging is managed via ``config_set`` with a nested ``logs`` key,
        which is the mechanism Amarisoft uses for runtime log control.

        Args:
            layers: Per-layer log settings.
                    Example: ``{"PHY": {"level": "debug", "max_size": 1}}``
            **params: Additional log parameters.
        """
        logs: dict[str, Any] = {}
        if layers is not None:
            logs["layers"] = layers
        logs.update(params)
        return self._client.send({"message": "config_set", "logs": logs})

    # ──────────────────────────────────────────────
    # System Information
    # ──────────────────────────────────────────────

    def version(self) -> dict[str, Any]:
        """Retrieve the software version of the service."""
        return self._client.send({"message": "version"})

    def help(self) -> dict[str, Any]:
        """List all available Remote API messages and events."""
        return self._client.send({"message": "help"})
