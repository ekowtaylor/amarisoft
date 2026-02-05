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
from .mme import MMEApi
from .ue import UEApi

__all__ = [
    "Callbox",
    "WebSocketClient",
    "ENBApi",
    "MMEApi",
    "IMSApi",
    "UEApi",
    "AmariError",
    "AmariConnectionError",
    "AmariTimeoutError",
    "AuthenticationError",
    "CommandError",
    "InvalidParameterError",
]

__version__ = "0.1.0"
