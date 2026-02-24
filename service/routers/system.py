"""System endpoints for health checks, status, and service information.

Provides endpoints for monitoring the REST API service and checking
connectivity to Amarisoft backend services.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from .. import __version__
from ..manager import CallboxManager, get_manager

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    summary="Health check",
    description="Check if the REST API service is healthy and can reach backend services.",
    response_description="Health status of the service",
)
async def health_check(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Perform a health check on the service.

    Returns:
        Health status including connectivity to backend services.
    """
    status = manager.get_status()

    return {
        "status": "healthy" if status.healthy else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
        "callbox": {
            "host": status.host,
            "connected_services": status.connected_count,
            "total_services": len(status.services),
        },
    }


@router.get(
    "/health/live",
    summary="Liveness probe",
    description="Simple liveness check for container orchestration.",
    response_description="Service is alive",
)
async def liveness() -> dict[str, str]:
    """Simple liveness check.

    Returns:
        Status indicating the service is alive.
    """
    return {"status": "ok"}


@router.get(
    "/health/ready",
    summary="Readiness probe",
    description="Check if the service is ready to accept requests.",
    response_description="Service readiness status",
)
async def readiness(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Check if the service is ready to handle requests.

    Returns:
        Readiness status. Returns 200 if at least one backend service
        is connected, otherwise returns degraded status.
    """
    status = manager.get_status()

    return {
        "ready": status.healthy,
        "services": {
            name: svc.connected for name, svc in status.services.items()
        },
    }


@router.get(
    "/version",
    summary="Get version information",
    description="Get version information for the REST API and connected services.",
    response_description="Version information",
)
async def get_version(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get version information for all services.

    Returns:
        Version information for the REST API and backend services.
    """
    status = manager.get_status()

    service_versions = {}
    for name, svc in status.services.items():
        service_versions[name] = {
            "version": svc.version,
            "connected": svc.connected,
        }

    return {
        "api_version": __version__,
        "services": service_versions,
    }


@router.get(
    "/services",
    summary="Get service status",
    description="Get detailed connection status for all Amarisoft backend services.",
    response_description="Service connection status",
)
async def get_services(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get detailed status of all backend services.

    Returns:
        Detailed connection status for each service.
    """
    status = manager.get_status()
    return status.to_dict()


@router.get(
    "/services/{service}",
    summary="Get single service status",
    description="Get connection status for a specific Amarisoft service.",
    response_description="Service status",
)
async def get_service(
    service: str,
    connect: bool = Query(
        default=False,
        description="Attempt to connect if not already connected",
    ),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get status of a specific service.

    Args:
        service: Service name (enb, mme, ims, ue).
        connect: If True, attempt to connect if not already connected.

    Returns:
        Status information for the requested service.
    """
    if connect:
        status = manager.check_service(service)
    else:
        # Get status without connecting
        full_status = manager.get_status()
        service_lower = service.lower()
        if service_lower not in full_status.services:
            raise ValueError(
                f"Unknown service: {service}. "
                f"Valid services: {list(full_status.services.keys())}"
            )
        status = full_status.services[service_lower]

    return status.to_dict()


@router.post(
    "/services/{service}/connect",
    summary="Connect to service",
    description="Establish connection to a specific Amarisoft service.",
    response_description="Connection result",
)
async def connect_service(
    service: str,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect to a specific service.

    Args:
        service: Service name (enb, mme, ims, ue).

    Returns:
        Status after connection attempt.
    """
    status = manager.check_service(service)
    return {
        "action": "connect",
        "service": status.to_dict(),
    }


@router.post(
    "/services/{service}/disconnect",
    summary="Disconnect from service",
    description="Close connection to a specific Amarisoft service.",
    response_description="Disconnection result",
)
async def disconnect_service(
    service: str,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect from a specific service.

    Args:
        service: Service name (enb, mme, ims, ue).

    Returns:
        Status after disconnection.
    """
    manager.disconnect_service(service)
    status = manager.get_status()
    service_status = status.services.get(service.lower())

    return {
        "action": "disconnect",
        "service": service_status.to_dict() if service_status else None,
    }


@router.post(
    "/services/{service}/reconnect",
    summary="Reconnect to service",
    description="Disconnect and reconnect to a specific Amarisoft service.",
    response_description="Reconnection result",
)
async def reconnect_service(
    service: str,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Reconnect to a specific service.

    Args:
        service: Service name (enb, mme, ims, ue).

    Returns:
        Status after reconnection attempt.
    """
    status = manager.reconnect_service(service)
    return {
        "action": "reconnect",
        "service": status.to_dict(),
    }


@router.post(
    "/services/connect",
    summary="Connect to all services",
    description="Establish connections to all Amarisoft services.",
    response_description="Connection results",
)
async def connect_all_services(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect to all backend services.

    Returns:
        Status of all services after connection attempts.
    """
    status = manager.connect_all()
    return {
        "action": "connect_all",
        **status.to_dict(),
    }


@router.post(
    "/services/disconnect",
    summary="Disconnect from all services",
    description="Close connections to all Amarisoft services.",
    response_description="Disconnection results",
)
async def disconnect_all_services(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect from all backend services.

    Returns:
        Status of all services after disconnection.
    """
    manager.close_all()
    status = manager.get_status()
    return {
        "action": "disconnect_all",
        **status.to_dict(),
    }
