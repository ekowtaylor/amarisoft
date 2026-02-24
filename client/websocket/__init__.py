"""Amarisoft WebSocket Client Library.

A Python library for interfacing with Amarisoft Callbox equipment via WebSocket API.
Provides direct access to eNB/gNB, MME/AMF, IMS, and UE Simulator services.

Example::

    from client.websocket import Callbox

    with Callbox("192.168.1.80") as cb:
        # Get eNB statistics
        stats = cb.enb.stats()

        # List connected UEs
        ues = cb.mme.ue_get()

        # Get cell configuration
        config = cb.enb.config_get()
"""

__version__ = "0.1.0"

from .callbox import Callbox
from .capabilities import (
    CapabilityChecker,
    CellConfig,
    DeviceCapabilities,
    DuplexMode,
    LicenseInfo,
    MIMOConfig,
    RATType,
    SDRInfo,
    ServicePorts,
    ValidationContext,
    get_default_capabilities,
    require_feature,
    require_service,
    validate_bandwidth,
    validate_mcs_param,
    validate_qci_param,
    validate_rf_params,
)
from .client import WebSocketClient
from .enb import ENBApi
from .exceptions import (
    AmariConnectionError,
    AmariError,
    AmariTimeoutError,
    AuthenticationError,
    CommandError,
    InvalidParameterError,
)
from .ims import IMSApi
from .logging import (
    LogCollector,
    LogEntry,
    TestSession,
    TestStep,
    enable_file_logging,
)
from .mme import MMEApi
from .ue import UEApi

# SSH Client (optional, for system administration)
from .ssh import (
    NetworkInterface,
    PCIeDevice,
    SDRCard,
    SSHClient,
    SystemInfo,
    USBDevice,
)

__all__ = [
    # Version
    "__version__",
    # Main Classes
    "Callbox",
    "WebSocketClient",
    # Service APIs
    "ENBApi",
    "MMEApi",
    "IMSApi",
    "UEApi",
    # SSH Client
    "SSHClient",
    "SDRCard",
    "SystemInfo",
    "PCIeDevice",
    "USBDevice",
    "NetworkInterface",
    # Capabilities
    "DeviceCapabilities",
    "CapabilityChecker",
    "ValidationContext",
    "SDRInfo",
    "LicenseInfo",
    "CellConfig",
    "ServicePorts",
    "RATType",
    "DuplexMode",
    "MIMOConfig",
    "get_default_capabilities",
    # Validation decorators
    "validate_rf_params",
    "validate_mcs_param",
    "validate_qci_param",
    "validate_bandwidth",
    "require_service",
    "require_feature",
    # Logging & Test Sessions
    "TestSession",
    "TestStep",
    "LogCollector",
    "LogEntry",
    "enable_file_logging",
    # Exceptions
    "AmariError",
    "AmariConnectionError",
    "AmariTimeoutError",
    "AuthenticationError",
    "CommandError",
    "InvalidParameterError",
]
