"""MME/AMF REST API endpoints.

Provides HTTP REST interface for MME/AMF (core network) operations
including UE management, PDN connections, bearers, and statistics.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from amarisoft.exceptions import AmariError

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
    "/version",
    summary="Get MME version",
    description="Get the software version of the MME/AMF service.",
)
async def get_version(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get MME/AMF version information."""
    try:
        return manager.mme.version()
    except AmariError as e:
        raise map_amarisoft_exception(e, "MME") from e


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
