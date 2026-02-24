"""Pydantic models for REST API request and response validation.

Provides type-safe request bodies and documented response schemas
for the Amarisoft REST API endpoints.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Common Models
# ──────────────────────────────────────────────


class MessageResponse(BaseModel):
    """Generic response with a message field."""

    message: str


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = True
    message: str | None = None


# ──────────────────────────────────────────────
# eNB/gNB Models
# ──────────────────────────────────────────────


class CellGainRequest(BaseModel):
    """Request to set cell gain."""

    gain: float = Field(..., ge=-140, le=0, description="Gain in dB (-140 to 0)")


class CellPowerRequest(BaseModel):
    """Request to set cell power."""

    power: float = Field(..., description="Power in dBm")


class CellActivateRequest(BaseModel):
    """Request to activate a cell."""

    activate: bool = Field(True, description="True to activate, False to deactivate")


class HandoverRequest(BaseModel):
    """Request to trigger a handover."""

    target_cell_id: int = Field(..., description="Target cell ID for handover")
    target_pci: int | None = Field(None, description="Target Physical Cell ID")


class RrcReleaseRequest(BaseModel):
    """Request to release RRC connection."""

    cause: str | None = Field(None, description="Release cause")
    redirect_freq: int | None = Field(None, description="Redirect frequency (EARFCN)")


class PagingRequest(BaseModel):
    """Request to send paging."""

    imsi: str = Field(..., description="IMSI of UE to page")
    domain: str = Field("ps", description="Paging domain: 'cs' or 'ps'")


# ──────────────────────────────────────────────
# MME/AMF Models
# ──────────────────────────────────────────────


class UeReleaseRequest(BaseModel):
    """Request to release/detach a UE."""

    cause: str | None = Field(None, description="Release cause")


class PdnConnectRequest(BaseModel):
    """Request to create a PDN connection."""

    apn: str = Field(..., description="Access Point Name")
    pdn_type: str = Field("ipv4", description="PDN type: 'ipv4', 'ipv6', or 'ipv4v6'")
    qci: int | None = Field(None, ge=1, le=9, description="QoS Class Identifier")


class PdnDisconnectRequest(BaseModel):
    """Request to disconnect a PDN."""

    pdn_id: int = Field(..., description="PDN connection ID")


class BearerModifyRequest(BaseModel):
    """Request to modify a bearer."""

    bearer_id: int = Field(..., description="Bearer ID to modify")
    qci: int | None = Field(None, ge=1, le=9, description="New QCI value")
    gbr_dl: int | None = Field(None, description="Guaranteed bit rate downlink (kbps)")
    gbr_ul: int | None = Field(None, description="Guaranteed bit rate uplink (kbps)")
    mbr_dl: int | None = Field(None, description="Maximum bit rate downlink (kbps)")
    mbr_ul: int | None = Field(None, description="Maximum bit rate uplink (kbps)")


class DedicatedBearerRequest(BaseModel):
    """Request to create a dedicated bearer."""

    qci: int = Field(..., ge=1, le=9, description="QoS Class Identifier")
    gbr_dl: int | None = Field(None, description="Guaranteed bit rate downlink (kbps)")
    gbr_ul: int | None = Field(None, description="Guaranteed bit rate uplink (kbps)")
    mbr_dl: int | None = Field(None, description="Maximum bit rate downlink (kbps)")
    mbr_ul: int | None = Field(None, description="Maximum bit rate uplink (kbps)")
    arp_priority: int | None = Field(None, ge=1, le=15, description="ARP priority level")
    tft: dict[str, Any] | None = Field(None, description="Traffic Flow Template")


# ──────────────────────────────────────────────
# IMS Models
# ──────────────────────────────────────────────


class ImsCallRequest(BaseModel):
    """Request to initiate an IMS call."""

    to_uri: str = Field(..., description="SIP URI of the callee")
    audio: bool = Field(True, description="Enable audio")
    video: bool = Field(False, description="Enable video")


class ImsSmsRequest(BaseModel):
    """Request to send an IMS SMS."""

    to_uri: str = Field(..., description="SIP URI of the recipient")
    message: str = Field(..., description="SMS message content")


class ImsRegistrationRequest(BaseModel):
    """Request to register/deregister with IMS."""

    register: bool = Field(True, description="True to register, False to deregister")


# ──────────────────────────────────────────────
# UE Simulator Models
# ──────────────────────────────────────────────


class UePowerRequest(BaseModel):
    """Request to power on/off a UE."""

    ue_id: int | None = Field(None, description="Specific UE ID, or None for all UEs")


class UeCreateRequest(BaseModel):
    """Request to create a simulated UE."""

    imsi: str = Field(..., description="IMSI for the UE")
    key: str | None = Field(None, description="Authentication key (K)")
    opc: str | None = Field(None, description="OPc value")
    apn: str | None = Field(None, description="Default APN")


class UeDeleteRequest(BaseModel):
    """Request to delete a simulated UE."""

    ue_id: int = Field(..., description="UE ID to delete")


# ──────────────────────────────────────────────
# Configuration Models
# ──────────────────────────────────────────────


class ConfigSetRequest(BaseModel):
    """Generic configuration set request."""

    config: dict[str, Any] = Field(..., description="Configuration parameters to set")


class LogConfigRequest(BaseModel):
    """Request to configure logging."""

    layers: dict[str, dict[str, Any]] | None = Field(
        None,
        description="Per-layer log settings, e.g., {'PHY': {'level': 'debug'}}",
    )
    max_size: int | None = Field(None, description="Maximum log buffer size")


# ──────────────────────────────────────────────
# Query Parameters as Models
# ──────────────────────────────────────────────


class StatsQueryParams(BaseModel):
    """Query parameters for stats endpoint."""

    samples: bool = Field(False, description="Include sample data")
    rf: bool = Field(False, description="Include RF statistics")


class UeQueryParams(BaseModel):
    """Query parameters for UE queries."""

    imsi: str | None = Field(None, description="Filter by IMSI")
    ue_id: int | None = Field(None, description="Filter by UE ID")
    enb_ue_id: int | None = Field(None, description="Filter by eNB UE ID")
    mme_ue_id: int | None = Field(None, description="Filter by MME UE ID")


class LogQueryParams(BaseModel):
    """Query parameters for log retrieval."""

    min_index: int | None = Field(None, description="Minimum log index")
    max_index: int | None = Field(None, description="Maximum log index")
    layer: str | None = Field(None, description="Filter by layer (PHY, RRC, etc.)")
    timeout: float | None = Field(None, description="Query timeout in seconds")
