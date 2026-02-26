"""MME/AMF REST API endpoints.

Provides HTTP REST interface for MME/AMF (core network) operations
including UE management, PDN connections, bearers, and statistics.
"""

from __future__ import annotations

from typing import Any

from client.websocket.exceptions import AmariError
from fastapi import APIRouter, Depends, Query

from ..exceptions import map_amarisoft_exception
from ..manager import CallboxManager, get_manager
from ..models import (
    ConfigSetRequest,
    DedicatedBearerRequest,
    LogConfigRequest,
    PdnConnectRequest,
    UeReleaseRequest,
)

router = APIRouter(prefix="/mme", tags=["MME/AMF"])


# ──────────────────────────────────────────────
# System Information
# ──────────────────────────────────────────────


@router.get(
    "/help",
    summary="Get available commands",
    description="List all available Remote API messages for the MME/AMF service.",
)
async def get_help(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get list of available MME/AMF API commands."""
    try:
        return manager.mme.help()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# Statistics
# ──────────────────────────────────────────────


@router.get(
    "/stats",
    summary="Get MME statistics",
    description="Retrieve current MME/AMF statistics.",
)
async def get_stats(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get MME/AMF statistics."""
    try:
        return manager.mme.stats()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────


@router.get(
    "/config",
    summary="Get MME configuration",
    description="Retrieve the current MME/AMF configuration.",
)
async def get_config(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get MME/AMF configuration."""
    try:
        return manager.mme.config_get()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/config",
    summary="Set MME configuration",
    description="Update MME/AMF configuration parameters.",
)
async def set_config(
    request: ConfigSetRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Set MME/AMF configuration parameters."""
    try:
        return manager.mme.config_set(**request.config)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# UE Management
# ──────────────────────────────────────────────


@router.get(
    "/ue",
    summary="List connected UEs",
    description="Get information about UEs registered with the MME/AMF.",
)
async def list_ues(
    imsi: str | None = Query(None, description="Filter by IMSI"),
    mme_ue_id: int | None = Query(None, description="Filter by MME UE ID"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """List UEs registered with the MME/AMF."""
    try:
        filters: dict[str, Any] = {}
        if imsi is not None:
            filters["imsi"] = imsi
        if mme_ue_id is not None:
            filters["mme_ue_id"] = mme_ue_id
        return manager.mme.ue_get(**filters)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/ue/{mme_ue_id}",
    summary="Get UE by ID",
    description="Get information about a specific UE by its MME UE ID.",
)
async def get_ue(
    mme_ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get specific UE information."""
    try:
        return manager.mme.ue_get(mme_ue_id=mme_ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/ue/imsi/{imsi}",
    summary="Get UE by IMSI",
    description="Get information about a specific UE by its IMSI.",
)
async def get_ue_by_imsi(
    imsi: str,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get specific UE information by IMSI."""
    try:
        return manager.mme.ue_get(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/ue/{mme_ue_id}/release",
    summary="Release UE",
    description="Release/detach a UE from the network.",
)
async def release_ue(
    mme_ue_id: int,
    request: UeReleaseRequest | None = None,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Release/detach a UE."""
    try:
        kwargs: dict[str, Any] = {"mme_ue_id": mme_ue_id}
        if request and request.cause:
            kwargs["cause"] = request.cause
        return manager.mme.ue_release(**kwargs)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/ue/imsi/{imsi}/release",
    summary="Release UE by IMSI",
    description="Release/detach a UE from the network by IMSI.",
)
async def release_ue_by_imsi(
    imsi: str,
    request: UeReleaseRequest | None = None,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Release/detach a UE by IMSI."""
    try:
        kwargs: dict[str, Any] = {"imsi": imsi}
        if request and request.cause:
            kwargs["cause"] = request.cause
        return manager.mme.ue_release(**kwargs)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# PDN Connection Management
# ──────────────────────────────────────────────


@router.post(
    "/ue/{mme_ue_id}/pdn",
    summary="Create PDN connection",
    description="Create a PDN connection for a UE.",
)
async def create_pdn(
    mme_ue_id: int,
    request: PdnConnectRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Create a PDN connection for a UE."""
    try:
        kwargs: dict[str, Any] = {
            "mme_ue_id": mme_ue_id,
            "apn": request.apn,
            "pdn_type": request.pdn_type,
        }
        if request.qci is not None:
            kwargs["qci"] = request.qci
        return manager.mme.pdn_connect(**kwargs)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.delete(
    "/ue/{mme_ue_id}/pdn/{pdn_id}",
    summary="Disconnect PDN",
    description="Disconnect a PDN connection for a UE.",
)
async def disconnect_pdn(
    mme_ue_id: int,
    pdn_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect a PDN connection."""
    try:
        return manager.mme.pdn_disconnect(mme_ue_id=mme_ue_id, pdn_id=pdn_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# Bearer Management
# ──────────────────────────────────────────────


@router.post(
    "/ue/{mme_ue_id}/bearer",
    summary="Create dedicated bearer",
    description="Create a dedicated bearer for a UE.",
)
async def create_bearer(
    mme_ue_id: int,
    request: DedicatedBearerRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Create a dedicated bearer."""
    try:
        kwargs: dict[str, Any] = {
            "mme_ue_id": mme_ue_id,
            "qci": request.qci,
        }
        if request.gbr_dl is not None:
            kwargs["gbr_dl"] = request.gbr_dl
        if request.gbr_ul is not None:
            kwargs["gbr_ul"] = request.gbr_ul
        if request.mbr_dl is not None:
            kwargs["mbr_dl"] = request.mbr_dl
        if request.mbr_ul is not None:
            kwargs["mbr_ul"] = request.mbr_ul
        if request.arp_priority is not None:
            kwargs["arp_priority"] = request.arp_priority
        if request.tft is not None:
            kwargs["tft"] = request.tft
        return manager.mme.bearer_activate(**kwargs)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.delete(
    "/ue/{mme_ue_id}/bearer/{bearer_id}",
    summary="Delete bearer",
    description="Delete a bearer for a UE.",
)
async def delete_bearer(
    mme_ue_id: int,
    bearer_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Delete a bearer."""
    try:
        return manager.mme.bearer_deactivate(mme_ue_id=mme_ue_id, bearer_id=bearer_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# SMS
# ──────────────────────────────────────────────


@router.post(
    "/ue/{mme_ue_id}/sms",
    summary="Send SMS to UE",
    description="Send an SMS message to a UE.",
)
async def send_sms(
    mme_ue_id: int,
    message: str = Query(..., description="SMS message content"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send SMS to a UE."""
    try:
        return manager.mme.sms_send(mme_ue_id=mme_ue_id, message=message)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/ue/imsi/{imsi}/sms",
    summary="Send SMS by IMSI",
    description="Send an SMS message to a UE by IMSI.",
)
async def send_sms_by_imsi(
    imsi: str,
    message: str = Query(..., description="SMS message content"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send SMS to a UE by IMSI."""
    try:
        return manager.mme.sms_send(imsi=imsi, message=message)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# Paging
# ──────────────────────────────────────────────


@router.post(
    "/paging",
    summary="Page a UE",
    description="Send a paging request to a UE.",
)
async def page_ue(
    imsi: str = Query(..., description="IMSI of UE to page"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Page a UE."""
    try:
        return manager.mme.paging(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────


@router.get(
    "/logs",
    summary="Get logs",
    description="Retrieve log entries from the MME/AMF service.",
)
async def get_logs(
    min_index: int | None = Query(None, alias="min", description="Minimum log index"),
    max_index: int | None = Query(None, alias="max", description="Maximum log index"),
    layer: str | None = Query(None, description="Filter by layer"),
    timeout: float | None = Query(None, description="Query timeout in seconds"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get MME/AMF logs."""
    try:
        return manager.mme.log_get(
            min_=min_index,
            max_=max_index,
            layer=layer,
            timeout=timeout,
        )
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/logs/config",
    summary="Configure logging",
    description="Configure MME/AMF logging options.",
)
async def configure_logs(
    request: LogConfigRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Configure MME/AMF logging."""
    try:
        kwargs: dict[str, Any] = {}
        if request.layers:
            kwargs["layers"] = request.layers
        if request.max_size:
            kwargs["max_size"] = request.max_size
        return manager.mme.log_set(**kwargs)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# APN Management
# ──────────────────────────────────────────────


@router.get(
    "/apn",
    summary="List APNs",
    description="Get list of configured APNs.",
)
async def list_apns(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """List configured APNs."""
    try:
        return manager.mme.apn_get()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# System Control
# ──────────────────────────────────────────────


@router.post(
    "/quit",
    summary="Terminate MME",
    description="Terminate the MME/AMF process. Use with caution!",
)
async def quit_mme(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Terminate the MME/AMF process."""
    try:
        return manager.mme.quit()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# Command Execution
# ──────────────────────────────────────────────


@router.post(
    "/cmd",
    summary="Execute command",
    description="Execute a shell command on the MME/AMF.",
)
async def execute_cmd(
    command: str = Query(..., description="Command to execute"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Execute a command on the MME/AMF."""
    try:
        return manager.mme.cmd(command)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/register",
    summary="Register for events",
    description="Register for event notifications.",
)
async def register_events(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Register for event notifications."""
    try:
        return manager.mme.register()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/echo",
    summary="Echo test",
    description="Echo test command.",
)
async def echo(
    data: str | None = Query(None, description="Data to echo"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Echo test command."""
    try:
        return manager.mme.echo(data)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/cancel/{message_id}",
    summary="Cancel operation",
    description="Cancel a pending asynchronous operation.",
)
async def cancel_operation(
    message_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Cancel a pending operation."""
    try:
        return manager.mme.cancel(message_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/monitor",
    summary="Configure monitoring",
    description="Enable/disable event monitoring.",
)
async def configure_monitor(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Configure event monitoring."""
    try:
        return manager.mme.monitor()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# Additional Logging
# ──────────────────────────────────────────────


@router.get(
    "/logs/binary",
    summary="Get binary logs",
    description="Get binary log data.",
)
async def get_binary_logs(
    start_time: float | None = Query(None, description="Start timestamp"),
    end_time: float | None = Query(None, description="End timestamp"),
    max_count: int | None = Query(None, description="Maximum number of entries"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get binary log data."""
    try:
        return manager.mme.log_bin_get(
            start_time=start_time,
            end_time=end_time,
            max_count=max_count,
        )
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/logs/reset",
    summary="Reset logs",
    description="Reset the log buffer.",
)
async def reset_logs(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Reset log buffer."""
    try:
        return manager.mme.log_reset()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# S1 Interface
# ──────────────────────────────────────────────


@router.post(
    "/interface/s1/config-update",
    summary="S1 MME config update",
    description="Send MME Configuration Update.",
)
async def s1_mme_config_update(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send MME config update."""
    try:
        return manager.mme.s1_mme_config_upd()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/s1/reset",
    summary="S1 reset",
    description="Reset S1 interface.",
)
async def s1_reset(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Reset S1 interface."""
    try:
        return manager.mme.s1_reset()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# Interface Status (S6/S13/SGS/N8/N12/N13/N17)
# ──────────────────────────────────────────────


@router.get(
    "/interface/s6",
    summary="S6 status",
    description="Get S6 interface status (HSS).",
)
async def s6_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get S6 status."""
    try:
        return manager.mme.s6_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/s6/connect",
    summary="S6 connect",
    description="Connect to HSS via S6.",
)
async def s6_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect S6."""
    try:
        return manager.mme.s6_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/s6/disconnect",
    summary="S6 disconnect",
    description="Disconnect from HSS via S6.",
)
async def s6_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect S6."""
    try:
        return manager.mme.s6_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/interface/s13",
    summary="S13 status",
    description="Get S13 interface status (EIR).",
)
async def s13_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get S13 status."""
    try:
        return manager.mme.s13_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/s13/connect",
    summary="S13 connect",
    description="Connect to EIR via S13.",
)
async def s13_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect S13."""
    try:
        return manager.mme.s13_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/s13/disconnect",
    summary="S13 disconnect",
    description="Disconnect from EIR via S13.",
)
async def s13_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect S13."""
    try:
        return manager.mme.s13_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/interface/sgs",
    summary="SGs status",
    description="Get SGs interface status (VLR).",
)
async def sgs_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get SGs status."""
    try:
        return manager.mme.sgs_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/sgs/connect",
    summary="SGs connect",
    description="Connect to VLR via SGs.",
)
async def sgs_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect SGs."""
    try:
        return manager.mme.sgs_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/sgs/disconnect",
    summary="SGs disconnect",
    description="Disconnect from VLR via SGs.",
)
async def sgs_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect SGs."""
    try:
        return manager.mme.sgs_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/interface/n8",
    summary="N8 status",
    description="Get N8 interface status (UDM).",
)
async def n8_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get N8 status."""
    try:
        return manager.mme.n8_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n8/connect",
    summary="N8 connect",
    description="Connect to UDM via N8.",
)
async def n8_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect N8."""
    try:
        return manager.mme.n8_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n8/disconnect",
    summary="N8 disconnect",
    description="Disconnect from UDM via N8.",
)
async def n8_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect N8."""
    try:
        return manager.mme.n8_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n8/peer-connect",
    summary="N8 peer connect",
    description="Connect to UDM via N8 (peer mode).",
)
async def n8_peer_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect N8 peer."""
    try:
        return manager.mme.n8_peer_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n8/dereg-notify",
    summary="N8 deregistration notify",
    description="Send N8 deregistration notification.",
)
async def n8_dereg_notify(
    imsi: str = Query(..., description="IMSI of target UE"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send N8 dereg notification."""
    try:
        return manager.mme.n8_dereg_notify(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/interface/n12",
    summary="N12 status",
    description="Get N12 interface status (AUSF).",
)
async def n12_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get N12 status."""
    try:
        return manager.mme.n12_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n12/connect",
    summary="N12 connect",
    description="Connect to AUSF via N12.",
)
async def n12_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect N12."""
    try:
        return manager.mme.n12_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n12/disconnect",
    summary="N12 disconnect",
    description="Disconnect from AUSF via N12.",
)
async def n12_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect N12."""
    try:
        return manager.mme.n12_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/interface/n13",
    summary="N13 status",
    description="Get N13 interface status (UDM).",
)
async def n13_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get N13 status."""
    try:
        return manager.mme.n13_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n13/connect",
    summary="N13 connect",
    description="Connect via N13.",
)
async def n13_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect N13."""
    try:
        return manager.mme.n13_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n13/disconnect",
    summary="N13 disconnect",
    description="Disconnect via N13.",
)
async def n13_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect N13."""
    try:
        return manager.mme.n13_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/interface/n17",
    summary="N17 status",
    description="Get N17 interface status.",
)
async def n17_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get N17 status."""
    try:
        return manager.mme.n17_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n17/connect",
    summary="N17 connect",
    description="Connect via N17.",
)
async def n17_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect N17."""
    try:
        return manager.mme.n17_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n17/disconnect",
    summary="N17 disconnect",
    description="Disconnect via N17.",
)
async def n17_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect N17."""
    try:
        return manager.mme.n17_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# N5 Interface (PCF)
# ──────────────────────────────────────────────


@router.post(
    "/interface/n5/connect",
    summary="N5 connect",
    description="Connect to PCF via N5.",
)
async def n5_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect N5."""
    try:
        return manager.mme.n5_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n5/events/subscribe",
    summary="N5 events subscribe",
    description="Subscribe to N5 events.",
)
async def n5_events_subscribe(
    imsi: str | None = Query(None, description="IMSI filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Subscribe to N5 events."""
    try:
        return manager.mme.n5_events_subscribe(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n5/events/unsubscribe",
    summary="N5 events unsubscribe",
    description="Unsubscribe from N5 events.",
)
async def n5_events_unsubscribe(
    imsi: str | None = Query(None, description="IMSI filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Unsubscribe from N5 events."""
    try:
        return manager.mme.n5_events_unsubscribe(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n5/session/create",
    summary="N5 session create",
    description="Create N5 session.",
)
async def n5_session_create(
    imsi: str = Query(..., description="IMSI of target UE"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Create N5 session."""
    try:
        return manager.mme.n5_session_create(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/n5/session/terminate",
    summary="N5 session terminate",
    description="Terminate N5 session.",
)
async def n5_session_terminate(
    imsi: str = Query(..., description="IMSI of target UE"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Terminate N5 session."""
    try:
        return manager.mme.n5_session_terminate(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# LCS Interface (Location Services)
# ──────────────────────────────────────────────


@router.post(
    "/interface/lcs/connect",
    summary="LCS connect",
    description="Connect to LCS.",
)
async def lcs_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect LCS."""
    try:
        return manager.mme.lcs_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/lcs/disconnect",
    summary="LCS disconnect",
    description="Disconnect from LCS.",
)
async def lcs_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect LCS."""
    try:
        return manager.mme.lcs_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/lcs/reset",
    summary="LCS-AP reset",
    description="Send LCS-AP Reset Request.",
)
async def lcsap_reset(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send LCS-AP reset."""
    try:
        return manager.mme.lcsap_reset_req()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/lcs/location-request",
    summary="LCS location request",
    description="Request location for a UE.",
)
async def lcs_location_request(
    imsi: str = Query(..., description="IMSI of target UE"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Request UE location."""
    try:
        return manager.mme.location_req(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# LMF Interface (5G Location)
# ──────────────────────────────────────────────


@router.post(
    "/interface/lmf/connect",
    summary="LMF connect",
    description="Connect to LMF.",
)
async def lmf_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect LMF."""
    try:
        return manager.mme.lmf_client_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/lmf/non-ue-n2/subscribe",
    summary="LMF non-UE N2 subscribe",
    description="Subscribe to non-UE N2 messages from LMF.",
)
async def lmf_non_ue_n2_subscribe(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Subscribe to LMF non-UE N2."""
    try:
        return manager.mme.lmf_non_ue_n2_subscribe()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/lmf/non-ue-n2/unsubscribe",
    summary="LMF non-UE N2 unsubscribe",
    description="Unsubscribe from non-UE N2 messages from LMF.",
)
async def lmf_non_ue_n2_unsubscribe(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Unsubscribe from LMF non-UE N2."""
    try:
        return manager.mme.lmf_non_ue_n2_unsubscribe()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/lmf/ue-n1-n2/subscribe",
    summary="LMF UE N1/N2 subscribe",
    description="Subscribe to UE N1/N2 messages from LMF.",
)
async def lmf_ue_n1_n2_subscribe(
    imsi: str | None = Query(None, description="IMSI filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Subscribe to LMF UE N1/N2."""
    try:
        return manager.mme.lmf_ue_n1_n2_subscribe(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/lmf/ue-n1-n2/unsubscribe",
    summary="LMF UE N1/N2 unsubscribe",
    description="Unsubscribe from UE N1/N2 messages from LMF.",
)
async def lmf_ue_n1_n2_unsubscribe(
    imsi: str | None = Query(None, description="IMSI filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Unsubscribe from LMF UE N1/N2."""
    try:
        return manager.mme.lmf_ue_n1_n2_unsubscribe(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# NR Location Services
# ──────────────────────────────────────────────


@router.post(
    "/location/nr-request",
    summary="NR location request",
    description="Request NR location for a UE.",
)
async def nr_location_request(
    imsi: str = Query(..., description="IMSI of target UE"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Request NR location."""
    try:
        return manager.mme.nr_location_req(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/location/nr-cancel",
    summary="Cancel NR location",
    description="Cancel NR location request.",
)
async def nr_cancel_location(
    imsi: str = Query(..., description="IMSI of target UE"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Cancel NR location."""
    try:
        return manager.mme.nr_cancel_location(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/location/nr-otdoa-info",
    summary="NR OTDOA info request",
    description="Request NR OTDOA information.",
)
async def nr_otdoa_info_request(
    imsi: str | None = Query(None, description="IMSI filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Request NR OTDOA info."""
    try:
        return manager.mme.nr_otdoa_information_req(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/location/otdoa-info",
    summary="OTDOA info request",
    description="Request OTDOA information.",
)
async def otdoa_info_request(
    imsi: str | None = Query(None, description="IMSI filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Request OTDOA info."""
    try:
        return manager.mme.otdoa_information_req(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/location/trp-info",
    summary="TRP info request",
    description="Request TRP information.",
)
async def trp_info_request(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Request TRP info."""
    try:
        return manager.mme.trp_information_req()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/location/reset-stored-info",
    summary="Reset stored position info",
    description="Reset stored UE positioning information.",
)
async def reset_ue_pos_info(
    imsi: str | None = Query(None, description="IMSI filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Reset stored position info."""
    try:
        return manager.mme.reset_ue_pos_stored_info(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/location/ecid-terminate",
    summary="E-CID measurement termination",
    description="Terminate E-CID periodic measurements.",
)
async def ecid_terminate(
    imsi: str | None = Query(None, description="IMSI filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Terminate E-CID measurements."""
    try:
        return manager.mme.ecid_periodic_meas_termination(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# Mobile Equipment Management
# ──────────────────────────────────────────────


@router.post(
    "/me/add",
    summary="Add mobile equipment",
    description="Add Mobile Equipment entry.",
)
async def me_add(
    imei: str = Query(..., description="IMEI of mobile equipment"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Add ME entry."""
    try:
        return manager.mme.me_add(imei=imei)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.delete(
    "/me/{imei}",
    summary="Delete mobile equipment",
    description="Delete Mobile Equipment entry.",
)
async def me_delete(
    imei: str,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Delete ME entry."""
    try:
        return manager.mme.me_del(imei=imei)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# Data Transport
# ──────────────────────────────────────────────


@router.post(
    "/data/connectionless",
    summary="Connectionless info",
    description="Send/receive connectionless information.",
)
async def connectionless_info(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send connectionless info."""
    try:
        return manager.mme.connectionless_info()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/data/eth-pdu",
    summary="Ethernet PDU",
    description="Send Ethernet PDU.",
)
async def eth_pdu(
    imsi: str | None = Query(None, description="IMSI filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send Ethernet PDU."""
    try:
        return manager.mme.eth_pdu(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/data/non-ip",
    summary="Non-IP data",
    description="Send non-IP data (NB-IoT/LTE-M).",
)
async def non_ip_data(
    imsi: str | None = Query(None, description="IMSI filter"),
    data: str | None = Query(None, description="Data (hex encoded)"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send non-IP data."""
    try:
        return manager.mme.non_ip_data(imsi=imsi, data=data)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# URSP (UE Route Selection Policy)
# ──────────────────────────────────────────────


@router.get(
    "/ue/{mme_ue_id}/ursp",
    summary="Get URSP rules",
    description="Get URSP rules for a UE.",
)
async def get_ursp_rules(
    mme_ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get URSP rules."""
    try:
        ue_data = manager.mme.ue_get(mme_ue_id=mme_ue_id)
        ue_list = ue_data.get("ue_list", [])
        if ue_list:
            imsi = ue_list[0].get("imsi")
            if imsi:
                return manager.mme.ursp_rules(imsi=imsi)
        return {"error": "UE not found"}
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/ue/imsi/{imsi}/ursp",
    summary="Get URSP rules by IMSI",
    description="Get URSP rules for a UE by IMSI.",
)
async def get_ursp_rules_by_imsi(
    imsi: str,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get URSP rules by IMSI."""
    try:
        return manager.mme.ursp_rules(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# SBC (Session Border Controller)
# ──────────────────────────────────────────────


@router.get(
    "/interface/sbc",
    summary="SBC status",
    description="Get SBC interface status.",
)
async def sbc_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get SBC status."""
    try:
        return manager.mme.sbc_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/sbc/connect",
    summary="SBC connect",
    description="Connect to SBC.",
)
async def sbc_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect SBC."""
    try:
        return manager.mme.sbc_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/interface/sbc/disconnect",
    summary="SBC disconnect",
    description="Disconnect from SBC.",
)
async def sbc_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect SBC."""
    try:
        return manager.mme.sbc_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# PWS (Public Warning System)
# ──────────────────────────────────────────────


@router.post(
    "/pws/write",
    summary="PWS write",
    description="Write PWS message.",
)
async def pws_write(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Write PWS message."""
    try:
        return manager.mme.pws_write()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/pws/kill",
    summary="PWS kill",
    description="Kill PWS message.",
)
async def pws_kill(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Kill PWS message."""
    try:
        return manager.mme.pws_kill()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# NG-RAN Status
# ──────────────────────────────────────────────


@router.get(
    "/ng-ran",
    summary="NG-RAN status",
    description="Get NG-RAN status (connected gNBs).",
)
async def ng_ran_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get NG-RAN status."""
    try:
        return manager.mme.ng_ran_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/enb",
    summary="eNB status",
    description="Get eNB status (connected eNBs).",
)
async def enb_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get eNB status."""
    try:
        return manager.mme.enb_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.get(
    "/gnb",
    summary="gNB status",
    description="Get gNB status (connected gNBs).",
)
async def gnb_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get gNB status."""
    try:
        return manager.mme.gnb_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# NAS Transport
# ──────────────────────────────────────────────


@router.post(
    "/nas/5gs-transport",
    summary="5GS NAS transport",
    description="Send 5GS NAS transport message.",
)
async def nas_5gs_transport(
    imsi: str = Query(..., description="IMSI of target UE"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send 5GS NAS transport."""
    try:
        return manager.mme.nas_5gs_transport(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/nas/generic-transport",
    summary="Generic NAS transport",
    description="Send generic NAS transport message.",
)
async def generic_nas_transport(
    imsi: str = Query(..., description="IMSI of target UE"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send generic NAS transport."""
    try:
        return manager.mme.generic_nas_transport(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# GUTI Reallocation
# ──────────────────────────────────────────────


@router.post(
    "/ue/{mme_ue_id}/guti-realloc",
    summary="GUTI reallocation",
    description="Trigger GUTI reallocation for a UE.",
)
async def guti_realloc(
    mme_ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Trigger GUTI reallocation."""
    try:
        ue_data = manager.mme.ue_get(mme_ue_id=mme_ue_id)
        ue_list = ue_data.get("ue_list", [])
        if ue_list:
            imsi = ue_list[0].get("imsi")
            if imsi:
                return manager.mme.guti_realloc(imsi=imsi)
        return {"error": "UE not found"}
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/ue/imsi/{imsi}/guti-realloc",
    summary="GUTI reallocation by IMSI",
    description="Trigger GUTI reallocation for a UE by IMSI.",
)
async def guti_realloc_by_imsi(
    imsi: str,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Trigger GUTI reallocation by IMSI."""
    try:
        return manager.mme.guti_realloc(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# CS Paging
# ──────────────────────────────────────────────


@router.post(
    "/paging/cs",
    summary="MT CS paging",
    description="Mobile Terminated Circuit Switched paging.",
)
async def mt_cs_paging(
    imsi: str = Query(..., description="IMSI of target UE"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send MT CS paging."""
    try:
        return manager.mme.mt_cs_paging(imsi=imsi)
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


# ──────────────────────────────────────────────
# CBC (Cell Broadcast Center)
# ──────────────────────────────────────────────


@router.post(
    "/cbc/subscribe",
    summary="CBC notification subscribe",
    description="Subscribe to CBC notifications.",
)
async def cbc_subscribe(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Subscribe to CBC notifications."""
    try:
        return manager.mme.cbc_notif_subscribe()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


@router.post(
    "/cbc/unsubscribe",
    summary="CBC notification unsubscribe",
    description="Unsubscribe from CBC notifications.",
)
async def cbc_unsubscribe(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Unsubscribe from CBC notifications."""
    try:
        return manager.mme.cbc_notif_unsubscribe()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e
