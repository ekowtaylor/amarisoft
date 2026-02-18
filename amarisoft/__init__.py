"""Amarisoft Callbox Python API client.

A Python package for interfacing with the Amarisoft Callbox via its
WebSocket Remote API. Supports eNB/gNB, MME/AMF, IMS, and UE Simulator.

Example::

    from amarisoft import Callbox

    with Callbox("192.168.1.100") as cb:
        ues = cb.enb.ue_get()
        cb.enb.cell_gain(cell_id=1, gain=-10)
"""

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

__version__ = "0.1.0"
