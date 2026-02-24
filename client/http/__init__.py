"""Amarisoft HTTP Client Library.

A Python client for interfacing with Amarisoft Callbox via the REST API service.
Provides the same interface as the WebSocket client but uses HTTP under the hood.

Example::

    from client.http import Callbox

    # Connect to REST API service running on callbox
    cb = Callbox("http://192.168.1.80:9010")

    # Same interface as WebSocket client
    stats = cb.enb.stats()
    ues = cb.mme.ue_get()
    config = cb.enb.config_get()

    # With test session and logging
    from client.http.logging import TestSession

    with TestSession(cb, name="my_test") as session:
        with session.step("Get Stats"):
            stats = cb.enb.stats()

    # With capability validation
    from client.http.capabilities import DeviceCapabilities, ValidationContext

    caps = DeviceCapabilities.from_callbox(cb)
    print(f"Max cells: {caps.max_cells}")

The HTTP client is ideal for:
- Remote access from machines outside the callbox network
- Integration with web applications
- Scenarios where WebSocket connectivity is not available
- RESTful API consumers

Note: Requires the REST API service to be deployed and running on the callbox.
See service/DEPLOYMENT.plan.md for deployment instructions.
"""

__version__ = "0.1.0"

from .client import HTTPClient
from .callbox import Callbox
from .enb import ENBApi
from .mme import MMEApi
from .ims import IMSApi
from .ue import UEApi
from .exceptions import (
    HTTPClientError,
    ConnectionError,
    TimeoutError,
    AuthenticationError,
    APIError,
)
from .logging import (
    LogEntry,
    LogCollector,
    TestStep,
    TestSession,
    enable_file_logging,
)
from .capabilities import (
    BandInfo,
    RFLimits,
    LicenseLimits,
    DeviceCapabilities,
    ValidationError,
    CapabilityChecker,
    ValidationContext,
)

__all__ = [
    # Version
    "__version__",
    # Core client
    "HTTPClient",
    "Callbox",
    # API classes
    "ENBApi",
    "MMEApi",
    "IMSApi",
    "UEApi",
    # Exceptions
    "HTTPClientError",
    "ConnectionError",
    "TimeoutError",
    "AuthenticationError",
    "APIError",
    # Logging
    "LogEntry",
    "LogCollector",
    "TestStep",
    "TestSession",
    "enable_file_logging",
    # Capabilities
    "BandInfo",
    "RFLimits",
    "LicenseLimits",
    "DeviceCapabilities",
    "ValidationError",
    "CapabilityChecker",
    "ValidationContext",
]
