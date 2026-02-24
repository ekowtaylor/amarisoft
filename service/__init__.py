"""Amarisoft REST API Webservice.

A FastAPI-based HTTP REST interface for the Amarisoft Callbox WebSocket API.
Designed to be deployed on the callbox to provide remote HTTP access to
eNB/gNB, MME/AMF, IMS, and UE Simulator services.

Example::

    # Start the service
    python -m service.main

    # Or with uvicorn directly
    uvicorn service.app:create_app --factory --host 0.0.0.0 --port 8080
"""

# Version must be defined before imports to avoid circular import issues
__version__ = "0.1.0"

from .app import create_app
from .config import Settings, get_settings
from .manager import CallboxManager

__all__ = [
    "__version__",
    "create_app",
    "Settings",
    "get_settings",
    "CallboxManager",
]
