"""eNB/gNB REST API endpoints.

Provides HTTP REST interface for eNB/gNB (base station) operations
including cell management, UE control, and statistics.
"""

from __future__ import annotations

from typing import Any

from client.websocket.exceptions import AmariError
from fastapi import APIRouter, Depends, Query

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
    """List all cells.

    Attempts to use cell_list message first, falls back to extracting
    cell info from config_get if cell_list is not supported.
    """
    try:
        # Try cell_list first (newer Amarisoft versions)
        return manager.enb.cell_list()
    except AmariError as e:
        # If cell_list not supported, extract from config_get
        error_str = str(e).lower()
        error_code = getattr(e, "error_code", None)
        if "unknown message" in error_str or error_code in ("BAD_REQUEST", 400):
            try:
                config = manager.enb.config_get()
                # Extract cell_list from config if available
                cells = config.get("cell_list", config.get("cells", []))
                return {"cell_list": cells if isinstance(cells, list) else []}
            except AmariError:
                pass
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
    """Get specific cell information.

    Attempts to use cell_list and filter, falls back to config_get.
    """
    try:
        # Try cell_list first
        result = manager.enb.cell_list()
        cell_list = result.get("cell_list", [])
        for cell in cell_list:
            if cell.get("cell_id") == cell_id:
                return {"cell": cell}
        return result
    except AmariError as e:
        # If cell_list not supported, extract from config_get
        error_str = str(e).lower()
        error_code = getattr(e, "error_code", None)
        if "unknown message" in error_str or error_code in ("BAD_REQUEST", 400):
            try:
                config = manager.enb.config_get()
                cells = config.get("cell_list", config.get("cells", []))
                if isinstance(cells, list):
                    for cell in cells:
                        if cell.get("cell_id") == cell_id:
                            return {"cell": cell}
                return {"cell_list": cells if isinstance(cells, list) else []}
            except AmariError:
                pass
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
    """Send paging to a UE using page_ue message."""
    try:
        return manager.enb.page_ue(
            cell_ids=[1],  # Default to cell 1
            imsi=request.imsi,
            cn_domain=request.domain,
        )
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


# License endpoint removed - not supported by Amarisoft WebSocket API


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


# ──────────────────────────────────────────────
# Command Execution
# ──────────────────────────────────────────────


@router.post(
    "/cmd",
    summary="Execute command",
    description="Execute a shell command on the eNB/gNB.",
)
async def execute_cmd(
    command: str = Query(..., description="Command to execute"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Execute a command on the eNB/gNB."""
    try:
        return manager.enb.cmd(command)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


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
        return manager.enb.register()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


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
        return manager.enb.echo(data)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


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
        return manager.enb.cancel(message_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


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
        return manager.enb.monitor()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# KPI / Additional Logging
# ──────────────────────────────────────────────


@router.get(
    "/kpi",
    summary="Get KPIs",
    description="Get Key Performance Indicators.",
)
async def get_kpi(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get KPIs."""
    try:
        return manager.enb.kpi_get()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/logs/binary",
    summary="Get binary logs",
    description="Get binary log data.",
)
async def get_binary_logs(
    min_index: int | None = Query(None, alias="min", description="Minimum log index"),
    max_index: int | None = Query(None, alias="max", description="Maximum log index"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get binary log data."""
    try:
        return manager.enb.log_bin_get(min_=min_index, max_=max_index)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


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
        return manager.enb.log_reset()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# RF Control
# ──────────────────────────────────────────────


@router.get(
    "/rf",
    summary="Get RF parameters",
    description="Get RF (Radio Frequency) parameters.",
)
async def get_rf(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get RF parameters."""
    try:
        return manager.enb.rf()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/rf",
    summary="Set RF parameters",
    description="Set RF (Radio Frequency) parameters.",
)
async def set_rf(
    tx_gain: float | None = Query(None, description="Transmit gain in dB"),
    rx_gain: float | None = Query(None, description="Receive gain in dB"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Set RF parameters."""
    try:
        return manager.enb.rf(tx_gain=tx_gain, rx_gain=rx_gain)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/rf/gain",
    summary="Get RF gain",
    description="Get RF gain values.",
)
async def get_rf_gain(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get RF gain."""
    try:
        return manager.enb.rf_gain()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/rf/gain",
    summary="Set RF gain",
    description="Set RF gain values.",
)
async def set_rf_gain(
    tx_gain: float | None = Query(None, description="Transmit gain in dB"),
    rx_gain: float | None = Query(None, description="Receive gain in dB"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Set RF gain."""
    try:
        return manager.enb.rf_gain(tx_gain=tx_gain, rx_gain=rx_gain)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/rf/power",
    summary="Get RF power",
    description="Get RF power information.",
)
async def get_rf_power(
    cell_id: int | None = Query(None, description="Cell ID filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get RF power."""
    try:
        return manager.enb.rf_power(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/snr",
    summary="Get SNR",
    description="Get Signal-to-Noise Ratio information.",
)
async def get_snr(
    enb_ue_id: int | None = Query(None, description="UE ID filter"),
    cell_id: int | None = Query(None, description="Cell ID filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get SNR information."""
    try:
        return manager.enb.snr(enb_ue_id=enb_ue_id, cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/noise-level",
    summary="Get noise level",
    description="Get noise level for cells.",
)
async def get_noise_level(
    cell_id: int | None = Query(None, description="Cell ID filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get noise level."""
    try:
        return manager.enb.noise_level(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/noise-level",
    summary="Set noise level",
    description="Set noise level for a cell.",
)
async def set_noise_level(
    cell_id: int = Query(..., description="Cell ID"),
    noise: float = Query(..., description="Noise level in dB"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Set noise level."""
    try:
        return manager.enb.noise_level(cell_id=cell_id, noise=noise)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# TRX (Transceiver)
# ──────────────────────────────────────────────


@router.get(
    "/trx",
    summary="Get TRX parameters",
    description="Get transceiver parameters.",
)
async def get_trx(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get TRX parameters."""
    try:
        return manager.enb.trx()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/trx/iq-dump",
    summary="Dump IQ samples",
    description="Dump IQ samples to file.",
)
async def trx_iq_dump(
    filename: str = Query(..., description="Output filename"),
    duration: float | None = Query(None, description="Duration in seconds"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Dump IQ samples."""
    try:
        return manager.enb.trx_iq_dump(filename=filename, duration=duration)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# Bearer / E-RAB / QoS
# ──────────────────────────────────────────────


@router.get(
    "/erab",
    summary="Get E-RAB info",
    description="Get E-RAB (Evolved Radio Access Bearer) information.",
)
async def get_erab(
    enb_ue_id: int | None = Query(None, description="UE ID filter"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get E-RAB information."""
    try:
        if enb_ue_id:
            return manager.enb.erab_get(enb_ue_id=enb_ue_id)
        return manager.enb.erab_get()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/qos-flow",
    summary="Get QoS flows",
    description="Get QoS flow information (5G NR).",
)
async def get_qos_flow(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get QoS flow information."""
    try:
        return manager.enb.qos_flow_get()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# RRC Procedures
# ──────────────────────────────────────────────


@router.post(
    "/ue/{enb_ue_id}/rrc-reconf",
    summary="RRC reconfiguration",
    description="Trigger RRC connection reconfiguration.",
)
async def rrc_reconf(
    enb_ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Trigger RRC reconfiguration."""
    try:
        return manager.enb.rrc_cnx_reconf(enb_ue_id=enb_ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ue/{enb_ue_id}/ue-cap-enquiry",
    summary="UE capability enquiry",
    description="Query UE radio capabilities.",
)
async def ue_cap_enquiry(
    enb_ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Query UE capabilities."""
    try:
        return manager.enb.rrc_ue_cap_enquiry(enb_ue_id=enb_ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ue/{enb_ue_id}/ue-info-req",
    summary="UE info request",
    description="Request UE information via RRC.",
)
async def ue_info_req(
    enb_ue_id: int,
    req_mask: int = Query(..., description="Request mask"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Request UE information."""
    try:
        return manager.enb.rrc_ue_info_req(enb_ue_id=enb_ue_id, req_mask=req_mask)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ue/{enb_ue_id}/pdcch-order-prach",
    summary="PDCCH order PRACH",
    description="Issue PDCCH order to trigger PRACH from UE.",
)
async def pdcch_order_prach(
    enb_ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Issue PDCCH order."""
    try:
        return manager.enb.pdcch_order_prach(enb_ue_id=enb_ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# Dual Connectivity / Carrier Aggregation
# ──────────────────────────────────────────────


@router.post(
    "/ue/{enb_ue_id}/en-dc-split-ratio",
    summary="EN-DC split ratio",
    description="Change DL split ratio for EN-DC UE.",
)
async def en_dc_split_ratio(
    enb_ue_id: int,
    ratio: int = Query(..., description="Split ratio (0-100)"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Change EN-DC split ratio."""
    try:
        return manager.enb.en_dc_split_dl_ratio_change(enb_ue_id=enb_ue_id, ratio=ratio)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ue/{enb_ue_id}/mr-dc-split-ratio",
    summary="MR-DC split ratio",
    description="Change DL split ratio for MR-DC UE.",
)
async def mr_dc_split_ratio(
    enb_ue_id: int,
    ratio: int = Query(..., description="Split ratio (0-100)"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Change MR-DC split ratio."""
    try:
        return manager.enb.mr_dc_split_dl_ratio_change(enb_ue_id=enb_ue_id, ratio=ratio)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ue/{enb_ue_id}/mr-dc-scg-release",
    summary="MR-DC SCG release",
    description="Release SCG for MR-DC UE.",
)
async def mr_dc_scg_release(
    enb_ue_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Release MR-DC SCG."""
    try:
        return manager.enb.mr_dc_scg_release(enb_ue_id=enb_ue_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ue/{enb_ue_id}/nr-pscell-change",
    summary="NR PSCell change",
    description="Change PSCell for NR UE.",
)
async def nr_pscell_change(
    enb_ue_id: int,
    target_cell_id: int = Query(..., description="Target PSCell ID"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Change NR PSCell."""
    try:
        return manager.enb.nr_pscell_change(enb_ue_id=enb_ue_id, target_cell_id=target_cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ue/{enb_ue_id}/scells",
    summary="Activate/deactivate SCells",
    description="Activate or deactivate secondary cells.",
)
async def scells_act_deact(
    enb_ue_id: int,
    scell_ids: str = Query(..., description="Comma-separated SCell IDs"),
    activate: bool = Query(True, description="True to activate, False to deactivate"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Activate/deactivate SCells."""
    try:
        ids = [int(x.strip()) for x in scell_ids.split(",")]
        return manager.enb.scells_act_deact(enb_ue_id=enb_ue_id, scell_ids=ids, activate=activate)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ue/{enb_ue_id}/dci-bwp-switch",
    summary="DCI BWP switch",
    description="Switch BWP via DCI (5G NR).",
)
async def dci_bwp_switch(
    enb_ue_id: int,
    dl_bwp_id: int | None = Query(None, description="Downlink BWP ID"),
    ul_bwp_id: int | None = Query(None, description="Uplink BWP ID"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Switch BWP via DCI."""
    try:
        return manager.enb.dci_bwp_switch(enb_ue_id=enb_ue_id, dl_bwp_id=dl_bwp_id, ul_bwp_id=ul_bwp_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# Cell Configuration
# ──────────────────────────────────────────────


@router.post(
    "/cells/{cell_id}/ul-disable",
    summary="Disable cell uplink",
    description="Disable/enable uplink for a cell.",
)
async def cell_ul_disable(
    cell_id: int,
    disable: bool = Query(True, description="True to disable, False to enable"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disable/enable cell uplink."""
    try:
        return manager.enb.cell_ul_disable(cell_id=cell_id, disable=disable)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/cells/{cell_id}/sib14",
    summary="Configure SIB14",
    description="Enable/disable SIB14 (ETWS/CMAS).",
)
async def configure_sib14(
    cell_id: int,
    enable: bool = Query(True, description="Enable SIB14"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Configure SIB14."""
    try:
        return manager.enb.sib14(cell_id=cell_id, enable=enable)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# Neighbor Cell Management
# ──────────────────────────────────────────────


@router.post(
    "/cells/{cell_id}/ncell/add",
    summary="Add neighbor cell",
    description="Add a neighbor cell to the neighbor list.",
)
async def ncell_add(
    cell_id: int,
    ncell_id: int = Query(..., description="Neighbor cell ID"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Add neighbor cell."""
    try:
        return manager.enb.ncell_list_add(cell_id=cell_id, ncell={"cell_id": ncell_id})
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.delete(
    "/cells/{cell_id}/ncell/{ncell_id}",
    summary="Delete neighbor cell",
    description="Remove a neighbor cell from the list.",
)
async def ncell_del(
    cell_id: int,
    ncell_id: int,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Delete neighbor cell."""
    try:
        return manager.enb.ncell_list_del(cell_id=cell_id, ncell_id=ncell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# PWS (Public Warning System)
# ──────────────────────────────────────────────


@router.post(
    "/pws/enb-failure",
    summary="eNB PWS failure",
    description="Simulate PWS failure on eNB.",
)
async def enb_pws_failure(
    cell_id: int | None = Query(None, description="Cell ID"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Simulate eNB PWS failure."""
    try:
        return manager.enb.enb_pws_failure(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/pws/enb-restart",
    summary="eNB PWS restart",
    description="Restart PWS on eNB.",
)
async def enb_pws_restart(
    cell_id: int | None = Query(None, description="Cell ID"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Restart eNB PWS."""
    try:
        return manager.enb.enb_pws_restart(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/pws/gnb-failure",
    summary="gNB PWS failure",
    description="Simulate PWS failure on gNB.",
)
async def gnb_pws_failure(
    cell_id: int | None = Query(None, description="Cell ID"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Simulate gNB PWS failure."""
    try:
        return manager.enb.gnb_pws_failure(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/pws/gnb-restart",
    summary="gNB PWS restart",
    description="Restart PWS on gNB.",
)
async def gnb_pws_restart(
    cell_id: int | None = Query(None, description="Cell ID"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Restart gNB PWS."""
    try:
        return manager.enb.gnb_pws_restart(cell_id=cell_id)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# NTN (Non-Terrestrial Network)
# ──────────────────────────────────────────────


@router.post(
    "/ntn/satellite-update",
    summary="Update NTN satellite",
    description="Update NTN satellite parameters.",
)
async def ntn_satellite_update(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Update NTN satellite."""
    try:
        return manager.enb.ntn_satellite_update()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/ntn/sv-file-update",
    summary="Update NTN SV file",
    description="Update NTN state vector file.",
)
async def ntn_sv_file_update(
    filename: str | None = Query(None, description="State vector filename"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Update NTN SV file."""
    try:
        return manager.enb.ntn_sv_file_update(filename=filename)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


# ──────────────────────────────────────────────
# Interface Status/Control (S1/NG/X2/Xn/M2)
# ──────────────────────────────────────────────


@router.get(
    "/interface/s1",
    summary="S1 status",
    description="Get S1 interface status.",
)
async def s1_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get S1 status."""
    try:
        return manager.enb.s1_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/s1/connect",
    summary="S1 connect",
    description="Connect to MME via S1.",
)
async def s1_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect S1."""
    try:
        return manager.enb.s1_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/s1/disconnect",
    summary="S1 disconnect",
    description="Disconnect from MME via S1.",
)
async def s1_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect S1."""
    try:
        return manager.enb.s1_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/s1/add",
    summary="Add MME",
    description="Add an MME to S1 interface.",
)
async def s1_add(
    mme_addr: str = Query(..., description="MME address"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Add MME."""
    try:
        return manager.enb.s1_add(mme_addr=mme_addr)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.delete(
    "/interface/s1/{mme_addr}",
    summary="Delete MME",
    description="Remove an MME from S1 interface.",
)
async def s1_delete(
    mme_addr: str,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Delete MME."""
    try:
        return manager.enb.s1_delete(mme_addr=mme_addr)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/s1/reset",
    summary="S1 reset",
    description="Reset S1 interface.",
)
async def s1_reset(
    mme_addr: str | None = Query(None, description="MME address"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Reset S1."""
    try:
        return manager.enb.s1_reset(mme_addr=mme_addr)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/s1/config-update",
    summary="S1 config update",
    description="Send eNB Configuration Update to MME.",
)
async def s1_config_update(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Send S1 config update."""
    try:
        return manager.enb.s1_enb_config_upd()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/interface/ng",
    summary="NG status",
    description="Get NG interface status (5G).",
)
async def ng_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get NG status."""
    try:
        return manager.enb.ng_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/ng/connect",
    summary="NG connect",
    description="Connect to AMF via NG.",
)
async def ng_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect NG."""
    try:
        return manager.enb.ng_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/ng/disconnect",
    summary="NG disconnect",
    description="Disconnect from AMF via NG.",
)
async def ng_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect NG."""
    try:
        return manager.enb.ng_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/ng/add",
    summary="Add AMF",
    description="Add an AMF to NG interface.",
)
async def ng_add(
    amf_addr: str = Query(..., description="AMF address"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Add AMF."""
    try:
        return manager.enb.ng_add(amf_addr=amf_addr)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.delete(
    "/interface/ng/{amf_addr}",
    summary="Delete AMF",
    description="Remove an AMF from NG interface.",
)
async def ng_delete(
    amf_addr: str,
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Delete AMF."""
    try:
        return manager.enb.ng_delete(amf_addr=amf_addr)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/interface/x2",
    summary="X2 status",
    description="Get X2 interface status.",
)
async def x2_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get X2 status."""
    try:
        return manager.enb.x2_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/x2/connect",
    summary="X2 connect",
    description="Connect to peer eNB via X2.",
)
async def x2_connect(
    peer_addr: str | None = Query(None, description="Peer eNB address"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect X2."""
    try:
        return manager.enb.x2_connect(peer_addr=peer_addr)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/x2/disconnect",
    summary="X2 disconnect",
    description="Disconnect from peer eNB via X2.",
)
async def x2_disconnect(
    peer_addr: str | None = Query(None, description="Peer eNB address"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect X2."""
    try:
        return manager.enb.x2_disconnect(peer_addr=peer_addr)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/interface/xn",
    summary="Xn status",
    description="Get Xn interface status (5G).",
)
async def xn_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get Xn status."""
    try:
        return manager.enb.xn_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/xn/connect",
    summary="Xn connect",
    description="Connect to peer gNB via Xn.",
)
async def xn_connect(
    peer_addr: str | None = Query(None, description="Peer gNB address"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect Xn."""
    try:
        return manager.enb.xn_connect(peer_addr=peer_addr)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/xn/disconnect",
    summary="Xn disconnect",
    description="Disconnect from peer gNB via Xn.",
)
async def xn_disconnect(
    peer_addr: str | None = Query(None, description="Peer gNB address"),
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect Xn."""
    try:
        return manager.enb.xn_disconnect(peer_addr=peer_addr)
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.get(
    "/interface/m2",
    summary="M2 status",
    description="Get M2 interface status (MBMS).",
)
async def m2_status(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Get M2 status."""
    try:
        return manager.enb.m2_status()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/m2/connect",
    summary="M2 connect",
    description="Connect to MCE via M2.",
)
async def m2_connect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Connect M2."""
    try:
        return manager.enb.m2_connect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e


@router.post(
    "/interface/m2/disconnect",
    summary="M2 disconnect",
    description="Disconnect from MCE via M2.",
)
async def m2_disconnect(
    manager: CallboxManager = Depends(get_manager),
) -> dict[str, Any]:
    """Disconnect M2."""
    try:
        return manager.enb.m2_disconnect()
    except AmariError as e:
        raise map_amarisoft_exception(e, "eNB") from e
