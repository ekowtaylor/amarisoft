"""Configuration management for the Amarisoft REST API service.

Settings are loaded from environment variables with sensible defaults
for deployment on an Amarisoft callbox.

Environment Variables:
    AMARISOFT_API_HOST: Host to bind the REST API (default: 0.0.0.0)
    AMARISOFT_API_PORT: Port for the REST API (default: 9010)
    AMARISOFT_CALLBOX_HOST: Host of Amarisoft services (default: 127.0.0.1)
    AMARISOFT_ENB_PORT: eNB/gNB WebSocket port (default: 9001)
    AMARISOFT_MME_PORT: MME/AMF WebSocket port (default: 9000)
    AMARISOFT_IMS_PORT: IMS WebSocket port (default: 9002)
    AMARISOFT_UE_PORT: UE Simulator WebSocket port (default: 9003)
    AMARISOFT_WS_TIMEOUT: WebSocket timeout in seconds (default: 10.0)
    AMARISOFT_WS_PASSWORD: WebSocket authentication password (default: None)
    AMARISOFT_API_KEY: API key for REST authentication (default: None)
    AMARISOFT_ENABLE_CORS: Enable CORS headers (default: true)
    AMARISOFT_LOG_LEVEL: Logging level (default: INFO)
    AMARISOFT_AUTO_RECONNECT: Auto-reconnect WebSocket on failure (default: true)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _get_bool_env(key: str, default: bool = False) -> bool:
    """Parse a boolean from an environment variable."""
    value = os.environ.get(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    return default


def _get_float_env(key: str, default: float) -> float:
    """Parse a float from an environment variable."""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int_env(key: str, default: int) -> int:
    """Parse an integer from an environment variable."""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Configuration settings for the Amarisoft REST API service.

    All settings can be configured via environment variables prefixed
    with ``AMARISOFT_``. The class is frozen (immutable) after creation.

    Attributes:
        host: Host address to bind the REST API server.
        port: Port number for the REST API server.
        callbox_host: Hostname/IP of the Amarisoft callbox services.
        enb_port: WebSocket port for eNB/gNB service.
        mme_port: WebSocket port for MME/AMF service.
        ims_port: WebSocket port for IMS service.
        ue_port: WebSocket port for UE Simulator service.
        ws_timeout: Default timeout for WebSocket operations (seconds).
        ws_password: Password for WebSocket authentication (if required).
        api_key: API key for REST endpoint authentication.
        enable_cors: Whether to enable CORS headers.
        log_level: Logging level for the service.
        auto_reconnect: Whether to auto-reconnect WebSocket on failure.
        ssl: Use SSL/TLS for WebSocket connections.
        ssl_verify: Verify SSL certificates (disable for self-signed).
    """

    # REST API Server Settings
    host: str = "0.0.0.0"
    port: int = 9010

    # Amarisoft Callbox Connection Settings
    callbox_host: str = "127.0.0.1"
    enb_port: int = 9001
    mme_port: int = 9000
    ims_port: int = 9002
    ue_port: int = 9003

    # WebSocket Settings
    ws_timeout: float = 10.0
    ws_password: str | None = None
    auto_reconnect: bool = True
    ssl: bool = False
    ssl_verify: bool = False

    # Authentication & Security
    api_key: str | None = None
    enable_cors: bool = True
    cors_origins: tuple[str, ...] = field(default_factory=lambda: ("*",))

    # Logging
    log_level: LogLevel = "INFO"

    @classmethod
    def from_env(cls) -> Settings:
        """Create Settings from environment variables.

        Returns:
            Settings instance populated from environment variables.
        """
        cors_origins_str = os.environ.get("AMARISOFT_CORS_ORIGINS", "*")
        cors_origins = tuple(
            origin.strip()
            for origin in cors_origins_str.split(",")
            if origin.strip()
        )

        return cls(
            # REST API Server
            host=os.environ.get("AMARISOFT_API_HOST", "0.0.0.0"),
            port=_get_int_env("AMARISOFT_API_PORT", 9010),
            # Callbox Connection
            callbox_host=os.environ.get("AMARISOFT_CALLBOX_HOST", "127.0.0.1"),
            enb_port=_get_int_env("AMARISOFT_ENB_PORT", 9001),
            mme_port=_get_int_env("AMARISOFT_MME_PORT", 9000),
            ims_port=_get_int_env("AMARISOFT_IMS_PORT", 9002),
            ue_port=_get_int_env("AMARISOFT_UE_PORT", 9003),
            # WebSocket
            ws_timeout=_get_float_env("AMARISOFT_WS_TIMEOUT", 10.0),
            ws_password=os.environ.get("AMARISOFT_WS_PASSWORD"),
            auto_reconnect=_get_bool_env("AMARISOFT_AUTO_RECONNECT", True),
            ssl=_get_bool_env("AMARISOFT_WS_SSL", False),
            ssl_verify=_get_bool_env("AMARISOFT_WS_SSL_VERIFY", False),
            # Authentication & Security
            api_key=os.environ.get("AMARISOFT_API_KEY"),
            enable_cors=_get_bool_env("AMARISOFT_ENABLE_CORS", True),
            cors_origins=cors_origins,
            # Logging
            log_level=os.environ.get("AMARISOFT_LOG_LEVEL", "INFO").upper(),  # type: ignore[arg-type]
        )

    def get_service_ports(self) -> dict[str, int]:
        """Get a mapping of service names to their ports.

        Returns:
            Dictionary mapping service names to port numbers.
        """
        return {
            "enb": self.enb_port,
            "mme": self.mme_port,
            "ims": self.ims_port,
            "ue": self.ue_port,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get the cached Settings instance.

    Uses LRU cache to ensure settings are only loaded once from
    environment variables. Call ``get_settings.cache_clear()`` to
    reload settings.

    Returns:
        The Settings instance.
    """
    return Settings.from_env()
