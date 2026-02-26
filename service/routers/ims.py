"""IMS REST API endpoints.

Provides HTTP REST interface for IMS (IP Multimedia Subsystem) operations
including VoLTE/VoNR calls, IMS registration, and messaging.
"""

from __future__ import annotations

from typing import Any

from client.websocket.exceptions import AmariError
from fastapi import APIRouter, Depends, Query

from ..exceptions import map_amarisoft_exception
from ..manager import CallboxManager, get_manager
from ..models import ConfigSetRequest, LogConfigRequest

router = APIRouter(prefix="/ims", tags=["IMS"])


# ──────────────────────────────────────────────
# System Information
# ──────────────────────────────────────────────


@router.get(
    "/help",
    summary="Get available commands",
    description="List all available Remote API messages for the IMS service.",
)
async def get_help(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get list of available IMS API commands."""
    try:
        return manager.ims.help()
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


# ──────────────────────────────────────────────
# Statistics
# ──────────────────────────────────────────────


@router.get(
    "/stats",
    summary="Get IMS statistics",
    description="Retrieve current IMS statistics.",
)
async def get_stats(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get IMS statistics."""
    try:
        return manager.ims.stats()
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────


@router.get(
    "/config",
    summary="Get IMS configuration",
    description="Retrieve the current IMS configuration.",
)
async def get_config(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get IMS configuration."""
    try:
        return manager.ims.config_get()
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


@router.post(
    "/config",
    summary="Set IMS configuration",
    description="Update IMS configuration parameters.",
)
async def set_config(
    request: ConfigSetRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Set IMS configuration parameters."""
    try:
        return manager.ims.config_set(**request.config)
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


# ──────────────────────────────────────────────
# UE/Registration Management
# ──────────────────────────────────────────────


@router.get(
    "/ue",
    summary="List IMS registered UEs",
    description="Get information about UEs registered with IMS.",
)
async def list_ues(
    imsi: str | None = Query(None, description="Filter by IMSI"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """List UEs registered with IMS."""
    try:
        filters: dict[str, Any] = {}
        if imsi is not None:
            filters["imsi"] = imsi
        return manager.ims.ue_get(**filters)
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


@router.get(
    "/ue/{ue_id}",
    summary="Get UE by ID",
    description="Get information about a specific IMS UE.",
)
async def get_ue(
    ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get specific IMS UE information."""
    try:
        return manager.ims.ue_get(ue_id=ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


# ──────────────────────────────────────────────
# Call Management
# ──────────────────────────────────────────────


@router.get(
    "/calls",
    summary="List active calls",
    description="Get information about active IMS calls.",
)
async def list_calls(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """List active IMS calls."""
    try:
        return manager.ims.call_get()
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


@router.get(
    "/calls/{call_id}",
    summary="Get call by ID",
    description="Get information about a specific IMS call.",
)
async def get_call(
    call_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get specific call information."""
    try:
        return manager.ims.call_get(call_id=call_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


@router.post(
    "/calls",
    summary="Initiate a call",
    description="Initiate an IMS voice/video call between two UEs.",
)
async def initiate_call(
    from_imsi: str = Query(..., description="IMSI of the calling UE"),
    to_imsi: str = Query(..., description="IMSI of the called UE"),
    audio: bool = Query(True, description="Enable audio"),
    video: bool = Query(False, description="Enable video"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Initiate an IMS call."""
    try:
        return manager.ims.call_start(
            from_imsi=from_imsi,
            to_imsi=to_imsi,
            audio=audio,
            video=video,
        )
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


@router.post(
    "/calls/{call_id}/answer",
    summary="Answer a call",
    description="Answer an incoming IMS call.",
)
async def answer_call(
    call_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Answer an IMS call."""
    try:
        return manager.ims.call_answer(call_id=call_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


@router.post(
    "/calls/{call_id}/hangup",
    summary="Hang up a call",
    description="Hang up/terminate an IMS call.",
)
async def hangup_call(
    call_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Hang up an IMS call."""
    try:
        return manager.ims.call_hangup(call_id=call_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


@router.post(
    "/calls/{call_id}/hold",
    summary="Hold a call",
    description="Put an IMS call on hold.",
)
async def hold_call(
    call_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Put an IMS call on hold."""
    try:
        return manager.ims.call_hold(call_id=call_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


@router.post(
    "/calls/{call_id}/resume",
    summary="Resume a call",
    description="Resume a held IMS call.",
)
async def resume_call(
    call_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Resume a held IMS call."""
    try:
        return manager.ims.call_resume(call_id=call_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


# ──────────────────────────────────────────────
# SMS Messaging
# ──────────────────────────────────────────────


@router.post(
    "/sms",
    summary="Send IMS SMS",
    description="Send an SMS message via IMS.",
)
async def send_sms(
    from_imsi: str = Query(..., description="IMSI of the sender"),
    to_imsi: str = Query(..., description="IMSI of the recipient"),
    message: str = Query(..., description="SMS message content"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send an SMS via IMS."""
    try:
        return manager.ims.sms_send(
            from_imsi=from_imsi,
            to_imsi=to_imsi,
            message=message,
        )
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────


@router.get(
    "/logs",
    summary="Get logs",
    description="Retrieve log entries from the IMS service.",
)
async def get_logs(
    min_index: int | None = Query(None, alias="min", description="Minimum log index"),
    max_index: int | None = Query(None, alias="max", description="Maximum log index"),
    layer: str | None = Query(None, description="Filter by layer"),
    timeout: float | None = Query(None, description="Query timeout in seconds"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get IMS logs."""
    try:
        return manager.ims.log_get(
            min_=min_index,
            max_=max_index,
            layer=layer,
            timeout=timeout,
        )
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


@router.post(
    "/logs/config",
    summary="Configure logging",
    description="Configure IMS logging options.",
)
async def configure_logs(
    request: LogConfigRequest,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Configure IMS logging."""
    try:
        kwargs: dict[str, Any] = {}
        if request.layers:
            kwargs["layers"] = request.layers
        if request.max_size:
            kwargs["max_size"] = request.max_size
        return manager.ims.log_set(**kwargs)
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e


# ──────────────────────────────────────────────
# System Control
# ──────────────────────────────────────────────


@router.post(
    "/quit",
    summary="Terminate IMS",
    description="Terminate the IMS process. Use with caution!",
)
async def quit_ims(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Terminate the IMS process."""
    try:
        return manager.ims.quit()
    except AmariError as e:
        raise map_amarisoft_exception(e, "IMS") from e
