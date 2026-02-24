"""UE Simulator REST API endpoints.

Provides HTTP REST interface for UE Simulator operations
including power control, UE management, and simulated device control.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from amarisoft.exceptions import AmariError

from ..exceptions import map_amarisoft_exception
from ..manager import CallboxManager, get_manager
from ..models import ConfigSetRequest, LogConfigRequest, UePowerRequest

router = APIRouter(prefix="/ue", tags=["UE Simulator"])


# ──────────────────────────────────────────────
# System Information
# ──────────────────────────────────────────────


@router.get(
    "/version",
    summary="Get UE Simulator version",
    description="Get the software version of the UE Simulator service.",
)
async def get_version(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get UE Simulator version information."""
    try:
        return manager.ue.version()
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


@router.get(
    "/help",
    summary="Get available commands",
    description="List all available Remote API messages for the UE Simulator.",
)
async def get_help(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get list of available UE Simulator API commands."""
    try:
        return manager.ue.help()
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


# ──────────────────────────────────────────────
# Statistics
# ──────────────────────────────────────────────


@router.get(
    "/stats",
    summary="Get UE Simulator statistics",
    description="Retrieve current UE Simulator statistics.",
)
async def get_stats(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get UE Simulator statistics."""
    try:
        return manager.ue.stats()
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────


@router.get(
    "/config",
    summary="Get UE Simulator configuration",
    description="Retrieve the current UE Simulator configuration.",
)
async def get_config(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get UE Simulator configuration."""
    try:
        return manager.ue.config_get()
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


@router.post(
    "/config",
    summary="Set UE Simulator configuration",
    description="Update UE Simulator configuration parameters.",
)
async def set_config(
    request: ConfigSetRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Set UE Simulator configuration parameters."""
    try:
        return manager.ue.config_set(**request.config)
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


# ──────────────────────────────────────────────
# UE Management
# ──────────────────────────────────────────────


@router.get(
    "/list",
    summary="List simulated UEs",
    description="Get information about all simulated UEs.",
)
async def list_ues(
    ue_id: int | None = Query(None, description="Filter by UE ID"),
    imsi: str | None = Query(None, description="Filter by IMSI"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """List all simulated UEs."""
    try:
        filters: dict[str, Any] = {}
        if ue_id is not None:
            filters["ue_id"] = ue_id
        if imsi is not None:
            filters["imsi"] = imsi
        return manager.ue.ue_get(**filters)
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


@router.get(
    "/{ue_id}",
    summary="Get UE by ID",
    description="Get information about a specific simulated UE.",
)
async def get_ue(
    ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get specific simulated UE information."""
    try:
        return manager.ue.ue_get(ue_id=ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


# ──────────────────────────────────────────────
# Power Control
# ──────────────────────────────────────────────


@router.post(
    "/power/on",
    summary="Power on UE(s)",
    description="Power on one or all simulated UEs.",
)
async def power_on(
    request: UePowerRequest | None = None,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Power on simulated UE(s)."""
    try:
        ue_id = request.ue_id if request else None
        return manager.ue.power_on(ue_id=ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


@router.post(
    "/power/off",
    summary="Power off UE(s)",
    description="Power off one or all simulated UEs.",
)
async def power_off(
    request: UePowerRequest | None = None,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Power off simulated UE(s)."""
    try:
        ue_id = request.ue_id if request else None
        return manager.ue.power_off(ue_id=ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


@router.post(
    "/{ue_id}/power/on",
    summary="Power on specific UE",
    description="Power on a specific simulated UE.",
)
async def power_on_ue(
    ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Power on a specific simulated UE."""
    try:
        return manager.ue.power_on(ue_id=ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


@router.post(
    "/{ue_id}/power/off",
    summary="Power off specific UE",
    description="Power off a specific simulated UE.",
)
async def power_off_ue(
    ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Power off a specific simulated UE."""
    try:
        return manager.ue.power_off(ue_id=ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


# ──────────────────────────────────────────────
# Bearer Management
# ──────────────────────────────────────────────


@router.post(
    "/{ue_id}/bearer/dedicated",
    summary="Activate dedicated bearer",
    description="Activate a dedicated bearer for a simulated UE.",
)
async def activate_dedicated_bearer(
    ue_id: int,
    def_bearer_id: int = Query(..., description="Default bearer ID"),
    qci: int = Query(..., ge=1, le=9, description="QoS Class Identifier"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Activate a dedicated bearer for a UE."""
    try:
        return manager.ue.ue_activate_dedicated_bearer(
            ue_id=ue_id,
            def_bearer_id=def_bearer_id,
            qci=qci,
        )
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


# ──────────────────────────────────────────────
# RRC State Control (NR)
# ──────────────────────────────────────────────


@router.post(
    "/{ue_id}/rrc/assistance",
    summary="Send UE Assistance Information",
    description="Send UE Assistance Information (5G NR) with preferred RRC state.",
)
async def ue_assistance_info(
    ue_id: int,
    preferred_state: str = Query(
        ...,
        description="Preferred RRC state: 'connected', 'inactive', or 'idle'",
    ),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send UE Assistance Information."""
    try:
        return manager.ue.ue_assistance_information(
            ue_id=ue_id,
            preferred_rrc_state=preferred_state,
        )
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────


@router.get(
    "/logs",
    summary="Get logs",
    description="Retrieve log entries from the UE Simulator service.",
)
async def get_logs(
    min_index: int | None = Query(None, alias="min", description="Minimum log index"),
    max_index: int | None = Query(None, alias="max", description="Maximum log index"),
    layer: str | None = Query(None, description="Filter by layer"),
    timeout: float | None = Query(None, description="Query timeout in seconds"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get UE Simulator logs."""
    try:
        return manager.ue.log_get(
            min_=min_index,
            max_=max_index,
            layer=layer,
            timeout=timeout,
        )
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e


@router.post(
    "/logs/config",
    summary="Configure logging",
    description="Configure UE Simulator logging options.",
)
async def configure_logs(
    request: LogConfigRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Configure UE Simulator logging."""
    try:
        kwargs: dict[str, Any] = {}
        if request.layers:
            kwargs["layers"] = request.layers
        if request.max_size:
            kwargs["max_size"] = request.max_size
        return manager.ue.log_set(**kwargs)
    except AmariError as e:
        raise map_amarisoft_exception(e, "UE") from e
