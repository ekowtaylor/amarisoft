"""eNB/gNB REST API endpoints.

Provides HTTP REST interface for eNB/gNB (base station) operations
including cell management, UE control, and statistics.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from amarisoft.exceptions import AmariError

from ..exceptions import map_amarisoft_exception
from ..manager import CallboxManager, get_manager
from ..models import (
    CellGainRequest,
    ConfigSetRequest,
    HandoverRequest,
    LogConfigRequest,
    PagingRequest,
    RrcReleaseRequest,
)

router = APIRouter(prefix="/enb", tags=["eNB/gNB"])


# ──────────────────────────────────────────────
# System Information
# ──────────────────────────────────────────────


@router.get(
    "/version",
    summary="Get eNB version",
    description="Get the software version of the eNB/gNB service.",
)
async def get_version(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get eNB/gNB version information."""
    try:
        return manager.enb.version()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/help",
    summary="Get available commands",
    description="List all available Remote API messages for the eNB/gNB service.",
)
async def get_help(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get list of available eNB/gNB API commands."""
    try:
        return manager.enb.help()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# Statistics
# ──────────────────────────────────────────────


@router.get(
    "/stats",
    summary="Get eNB statistics",
    description="Retrieve current eNB/gNB statistics including cell and UE metrics.",
)
async def get_stats(
    samples: bool = Query(False, description="Include sample data"),
    rf: bool = Query(False, description="Include RF statistics"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get eNB/gNB statistics."""
    try:
        return manager.enb.stats(samples=samples, rf=rf)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────


@router.get(
    "/config",
    summary="Get eNB configuration",
    description="Retrieve the current eNB/gNB configuration.",
)
async def get_config(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get eNB/gNB configuration."""
    try:
        return manager.enb.config_get()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/config",
    summary="Set eNB configuration",
    description="Update eNB/gNB configuration parameters.",
)
async def set_config(
    request: ConfigSetRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Set eNB/gNB configuration parameters."""
    try:
        return manager.enb.config_set(**request.config)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# UE Management
# ──────────────────────────────────────────────


@router.get(
    "/ue",
    summary="List connected UEs",
    description="Get information about UEs connected to the eNB/gNB.",
)
async def list_ues(
    imsi: str | None = Query(None, description="Filter by IMSI"),
    enb_ue_id: int | None = Query(None, description="Filter by eNB UE ID"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """List UEs connected to the eNB/gNB."""
    try:
        filters: dict[str, Any] = {}
        if imsi is not None:
            filters["imsi"] = imsi
        if enb_ue_id is not None:
            filters["enb_ue_id"] = enb_ue_id
        return manager.enb.ue_get(**filters)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/ue/{enb_ue_id}",
    summary="Get UE by ID",
    description="Get information about a specific UE by its eNB UE ID.",
)
async def get_ue(
    enb_ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get specific UE information."""
    try:
        return manager.enb.ue_get(enb_ue_id=enb_ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ue/{enb_ue_id}/rrc-release",
    summary="Release RRC connection",
    description="Release the RRC connection for a specific UE.",
)
async def rrc_release(
    enb_ue_id: int,
    request: RrcReleaseRequest | None = None,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Release RRC connection for a UE."""
    try:
        kwargs: dict[str, Any] = {"enb_ue_id": enb_ue_id}
        if request:
            if request.cause:
                kwargs["cause"] = request.cause
            if request.redirect_freq:
                kwargs["redirect_freq"] = request.redirect_freq
        return manager.enb.rrc_release(**kwargs)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ue/{enb_ue_id}/handover",
    summary="Trigger handover",
    description="Trigger a handover for a specific UE to another cell.",
)
async def handover(
    enb_ue_id: int,
    request: HandoverRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Trigger handover for a UE."""
    try:
        kwargs: dict[str, Any] = {
            "enb_ue_id": enb_ue_id,
            "target_cell_id": request.target_cell_id,
        }
        if request.target_pci is not None:
            kwargs["target_pci"] = request.target_pci
        return manager.enb.handover(**kwargs)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# Cell Management
# ──────────────────────────────────────────────


@router.get(
    "/cells",
    summary="List cells",
    description="Get information about all configured cells.",
)
async def list_cells(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """List all cells."""
    try:
        return manager.enb.cells_get()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/cells/{cell_id}",
    summary="Get cell by ID",
    description="Get information about a specific cell.",
)
async def get_cell(
    cell_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get specific cell information."""
    try:
        return manager.enb.cells_get(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/cells/{cell_id}/gain",
    summary="Set cell gain",
    description="Set the gain (attenuation) for a specific cell.",
)
async def set_cell_gain(
    cell_id: int,
    request: CellGainRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Set cell gain."""
    try:
        return manager.enb.cell_gain(cell_id=cell_id, gain=request.gain)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/cells/{cell_id}/activate",
    summary="Activate cell",
    description="Activate a specific cell.",
)
async def activate_cell(
    cell_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Activate a cell."""
    try:
        return manager.enb.cell_activate(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/cells/{cell_id}/deactivate",
    summary="Deactivate cell",
    description="Deactivate a specific cell.",
)
async def deactivate_cell(
    cell_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Deactivate a cell."""
    try:
        return manager.enb.cell_deactivate(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/cells/{cell_id}/mib-update",
    summary="Trigger MIB update",
    description="Trigger a Master Information Block update for the cell.",
)
async def mib_update(
    cell_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Trigger MIB update."""
    try:
        return manager.enb.mib_update(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/cells/{cell_id}/sib-update",
    summary="Trigger SIB update",
    description="Trigger System Information Block updates for the cell.",
)
async def sib_update(
    cell_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Trigger SIB update."""
    try:
        return manager.enb.sib_update(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# Paging
# ──────────────────────────────────────────────


@router.post(
    "/paging",
    summary="Send paging",
    description="Send a paging message to a UE.",
)
async def send_paging(
    request: PagingRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send paging to a UE."""
    try:
        return manager.enb.paging(imsi=request.imsi, domain=request.domain)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────


@router.get(
    "/logs",
    summary="Get logs",
    description="Retrieve log entries from the eNB/gNB service.",
)
async def get_logs(
    min_index: int | None = Query(None, alias="min", description="Minimum log index"),
    max_index: int | None = Query(None, alias="max", description="Maximum log index"),
    layer: str | None = Query(None, description="Filter by layer (PHY, RRC, etc.)"),
    timeout: float | None = Query(None, description="Query timeout in seconds"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get eNB/gNB logs."""
    try:
        return manager.enb.log_get(
            min_=min_index,
            max_=max_index,
            layer=layer,
            timeout=timeout,
        )
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/logs/config",
    summary="Configure logging",
    description="Configure eNB/gNB logging options.",
)
async def configure_logs(
    request: LogConfigRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Configure eNB/gNB logging."""
    try:
        kwargs: dict[str, Any] = {}
        if request.layers:
            kwargs["layers"] = request.layers
        if request.max_size:
            kwargs["max_size"] = request.max_size
        return manager.enb.log_set(**kwargs)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# System Control
# ──────────────────────────────────────────────


@router.get(
    "/license",
    summary="Get license info",
    description="Get license information for the eNB/gNB service.",
)
async def get_license(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get eNB/gNB license information."""
    try:
        return manager.enb.license()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/quit",
    summary="Terminate eNB",
    description="Terminate the eNB/gNB process. Use with caution!",
)
async def quit_enb(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Terminate the eNB/gNB process."""
    try:
        return manager.enb.quit()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e
