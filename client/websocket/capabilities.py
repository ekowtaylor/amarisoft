"""Device capabilities and constraints system for Amarisoft Callbox.

This module provides:
- DeviceCapabilities: Discovered capabilities from a connected device
- Constraints: Validation rules based on hardware/license limits
- CapabilityChecker: Validates operations against device constraints
- Validation decorators: Automatic parameter validation for API methods

Usage::

    from amarisoft import Callbox
    from amarisoft.capabilities import DeviceCapabilities, CapabilityChecker

    cb = Callbox("192.168.1.80", ims_port=9003)
    cb.connect_all()

    # Discover capabilities
    caps = DeviceCapabilities.from_callbox(cb)
    print(caps.summary())

    # Validate operations
    checker = CapabilityChecker(caps)
    checker.validate_cell_config(bandwidth=100, mimo_layers=4)
"""

from __future__ import annotations

import functools
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .callbox import Callbox

from .exceptions import InvalidParameterError

logger = logging.getLogger(__name__)


class RATType(Enum):
    """Radio Access Technology types."""

    LTE = "4g"
    NR = "5g"
    LTE_M = "lte-m"
    NB_IOT = "nb-iot"


class DuplexMode(Enum):
    """Duplex modes."""

    FDD = "fdd"
    TDD = "tdd"


class MIMOConfig(Enum):
    """MIMO configurations."""

    SISO = 1
    MIMO_2x2 = 2
    MIMO_4x4 = 4
    MIMO_8x8 = 8


@dataclass
class SDRInfo:
    """SDR hardware information."""

    device_id: int
    board_id: str
    board_type: str  # SDR50, SDR100
    serial: str
    fpga_revision: str
    software_version: str
    dna: str
    pcie_gen: int = 2
    pcie_lanes: int = 1
    max_bandwidth_mhz: int = 100
    max_mimo: MIMOConfig = MIMOConfig.MIMO_4x4
    board_revision: str = "0x0"

    @classmethod
    def from_dict(cls, data: dict[str, Any], device_id: int = 0) -> "SDRInfo":
        """Parse SDR info from device response."""
        board_id = data.get("board_id", "0x4b01")
        board_type = "SDR50" if "4b01" in str(board_id).lower() else "SDR100"

        return cls(
            device_id=device_id,
            board_id=str(board_id),
            board_type=board_type,
            serial=data.get("serial", "unknown"),
            fpga_revision=data.get("fpga_revision", "unknown"),
            software_version=data.get("software_version", "unknown"),
            dna=data.get("dna", "unknown"),
            board_revision=data.get("board_revision", "0x0"),
            max_bandwidth_mhz=100 if board_type == "SDR100" else 50,
        )

    @classmethod
    def from_log_output(cls, log_text: str, device_id: int = 0) -> "SDRInfo | None":
        """Parse SDR info from OTS log output.

        Args:
            log_text: Text from /var/log/lte/ots.log containing SDR info.
            device_id: Device ID to assign.

        Returns:
            SDRInfo if parsed successfully, None otherwise.
        """
        import re

        # Extract fields using regex
        board_id_match = re.search(
            r"Board ID:\s*(0x[0-9a-fA-F]+)\s*\((\w+)\)", log_text
        )
        serial_match = re.search(r"Serial\s*'([^']+)'", log_text)
        fpga_match = re.search(r"FPGA revision:\s*([^\n(]+)", log_text)
        pcie_match = re.search(r"PCIe.*gen(\d+)\s*x(\d+)", log_text)
        board_rev_match = re.search(r"Board revision:\s*(0x[0-9a-fA-F]+)", log_text)

        if not board_id_match:
            return None

        board_id = board_id_match.group(1)
        board_type = board_id_match.group(2)

        pcie_gen = int(pcie_match.group(1)) if pcie_match else 2
        pcie_lanes = int(pcie_match.group(2)) if pcie_match else 1

        return cls(
            device_id=device_id,
            board_id=board_id,
            board_type=board_type,
            serial=serial_match.group(1) if serial_match else "unknown",
            fpga_revision=fpga_match.group(1).strip() if fpga_match else "unknown",
            software_version="unknown",
            dna="unknown",
            board_revision=board_rev_match.group(1) if board_rev_match else "0x0",
            pcie_gen=pcie_gen,
            pcie_lanes=pcie_lanes,
            max_bandwidth_mhz=100 if board_type == "SDR100" else 50,
        )


@dataclass
class LicenseInfo:
    """License information and constraints."""

    user_name: str
    license_uid: str
    valid_until: str
    products: list[str] = field(default_factory=list)
    rat_support: list[RATType] = field(default_factory=list)
    max_cells: int = 1
    max_bandwidth_mhz: int = 40
    max_aggregation_mhz: int = 40
    features: dict[str, bool] = field(default_factory=dict)

    @property
    def has_ue_sim(self) -> bool:
        """Check if UE simulator is licensed."""
        return "lteue" in self.products or "uesim" in self.products

    @property
    def has_ims(self) -> bool:
        """Check if IMS is licensed."""
        return "lteims" in self.products

    @property
    def has_5gc(self) -> bool:
        """Check if 5G Core is licensed."""
        return "lte5gc" in self.products or "amf" in self.products

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LicenseInfo":
        """Parse license info from device response or key file."""
        rat_list = []
        rat_str = data.get("rat", "4g")
        if "4g" in rat_str:
            rat_list.append(RATType.LTE)
        if "5g" in rat_str:
            rat_list.append(RATType.NR)

        products = data.get("product_ids", "").split(",")

        return cls(
            user_name=data.get("user_name", "unknown"),
            license_uid=data.get("license_uid", "unknown"),
            valid_until=data.get("version", "unknown"),
            products=[p.strip().lower() for p in products if p.strip()],
            rat_support=rat_list,
            max_cells=int(data.get("cell_max", 1)),
            max_bandwidth_mhz=int(data.get("bandwidth_max", 40)),
            max_aggregation_mhz=int(
                data.get("aggregation_max", data.get("bandwidth_max", 40))
            ),
        )


@dataclass
class CellConfig:
    """Cell configuration constraints."""

    cell_id: int
    rat: RATType
    duplex_mode: DuplexMode
    band: int
    earfcn: int | None = None
    nr_arfcn: int | None = None
    bandwidth_rb: int = 100  # Resource blocks
    bandwidth_mhz: int = 20
    mimo_layers_dl: int = 2
    mimo_layers_ul: int = 2
    rf_port: int = 0

    @property
    def bandwidth_mhz_from_rb(self) -> int:
        """Convert RB to MHz for LTE."""
        rb_to_mhz = {6: 1.4, 15: 3, 25: 5, 50: 10, 75: 15, 100: 20}
        return rb_to_mhz.get(self.bandwidth_rb, 20)


@dataclass
class ServicePorts:
    """Remote API service ports."""

    enb: int = 9001
    mme: int = 9000
    ims: int = 9002
    ue: int = 9003
    mbms: int = 9004


@dataclass
class DeviceCapabilities:
    """Complete device capabilities discovered from a Callbox.

    This class captures hardware, license, and configuration constraints
    that determine what operations are valid on the device.
    """

    # Hardware
    hostname: str = "unknown"
    os_version: str = "unknown"
    amarisoft_version: str = "unknown"
    sdr_cards: list[SDRInfo] = field(default_factory=list)

    # License
    license_info: LicenseInfo | None = None

    # Configuration
    cells: list[CellConfig] = field(default_factory=list)
    service_ports: ServicePorts = field(default_factory=ServicePorts)

    # Constraints derived from hardware/license
    max_cells: int = 1
    max_bandwidth_mhz: int = 40
    max_aggregation_mhz: int = 40
    max_mimo_layers: int = 4
    supported_rats: list[RATType] = field(default_factory=list)
    supported_bands_lte: list[int] = field(default_factory=list)
    supported_bands_nr: list[int] = field(default_factory=list)

    # Feature flags
    features: dict[str, bool] = field(default_factory=dict)

    # Services available
    services_available: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_callbox(cls, callbox: "Callbox") -> "DeviceCapabilities":
        """Discover capabilities from a connected Callbox.

        Args:
            callbox: Connected Callbox instance.

        Returns:
            DeviceCapabilities with discovered constraints.
        """
        caps = cls()

        # Discover service availability
        caps.services_available = {
            "enb": callbox._enb_client.connected,
            "mme": callbox._mme_client.connected,
            "ims": callbox._ims_client.connected,
            "ue": callbox._ue_client.connected,
        }

        # Get service ports
        caps.service_ports = ServicePorts(
            enb=callbox._enb_client.port,
            mme=callbox._mme_client.port,
            ims=callbox._ims_client.port,
            ue=callbox._ue_client.port,
        )

        # Get eNB config if connected
        if caps.services_available.get("enb"):
            try:
                caps._discover_enb_capabilities(callbox)
            except Exception:
                pass

        # Get MME config if connected
        if caps.services_available.get("mme"):
            try:
                caps._discover_mme_capabilities(callbox)
            except Exception:
                pass

        # Get IMS license info if connected
        if caps.services_available.get("ims"):
            try:
                caps._discover_ims_capabilities(callbox)
            except Exception:
                pass

        # Calculate derived constraints
        caps._calculate_constraints()

        return caps

    def _discover_enb_capabilities(self, callbox: "Callbox") -> None:
        """Discover eNB/gNB capabilities."""
        # Get config
        config = callbox.enb.config_get()

        # Parse version
        self.amarisoft_version = config.get("version", "unknown")

        # Parse cells
        cells_data = config.get("cells", [])
        for i, cell_data in enumerate(cells_data):
            rat = RATType.NR if cell_data.get("nr", False) else RATType.LTE
            duplex = DuplexMode.TDD if cell_data.get("tdd", False) else DuplexMode.FDD

            cell = CellConfig(
                cell_id=cell_data.get("cell_id", i),
                rat=rat,
                duplex_mode=duplex,
                band=cell_data.get("band", 0),
                earfcn=cell_data.get("dl_earfcn"),
                nr_arfcn=cell_data.get("dl_nr_arfcn"),
                bandwidth_rb=cell_data.get("n_rb_dl", 100),
                mimo_layers_dl=cell_data.get("n_antenna_dl", 2),
                mimo_layers_ul=cell_data.get("n_antenna_ul", 2),
                rf_port=cell_data.get("rf_port", 0),
            )
            self.cells.append(cell)

        # Get stats for SDR info
        try:
            stats = callbox.enb.stats(rf=True)
            rf_info = stats.get("rf", {})
            if rf_info:
                sdr = SDRInfo.from_dict(rf_info, device_id=0)
                self.sdr_cards.append(sdr)
        except Exception:
            pass

    def _discover_mme_capabilities(self, callbox: "Callbox") -> None:
        """Discover MME/AMF capabilities."""
        config = callbox.mme.config_get()
        # Can extract PLMN, APN list, etc.
        self.features["5gc"] = config.get("amf", False) or config.get("5gc", False)
        self.features["ims_enabled"] = "ims" in str(config)

    def _discover_ims_capabilities(self, callbox: "Callbox") -> None:
        """Discover IMS capabilities and license info."""
        try:
            license_data = callbox.ims.license()
            if license_data and not license_data.get("error"):
                # Parse products from comma-separated string
                products_str = license_data.get("products", "")
                products = [
                    p.strip().lower() for p in products_str.split(",") if p.strip()
                ]

                # Try to get aggregation limit from license data
                # Note: Amarisoft may not expose this directly via API
                # The limit is typically only shown in startup logs
                aggregation_max = license_data.get(
                    "aggregation_max", license_data.get("bandwidth_max", None)
                )
                bandwidth_max = license_data.get("bandwidth_max", None)

                self.license_info = LicenseInfo(
                    user_name=license_data.get("user", "unknown"),
                    license_uid=license_data.get("uid", "unknown"),
                    valid_until=license_data.get("validity", "unknown"),
                    products=products,
                    rat_support=[RATType.LTE],  # Default, could be extended
                    max_cells=1,
                    # Use discovered values or None to trigger calculation later
                    max_bandwidth_mhz=bandwidth_max if bandwidth_max else 0,
                    max_aggregation_mhz=aggregation_max if aggregation_max else 0,
                )

                # Check for NR support in products
                if any("nr" in p or "5g" in p for p in products):
                    self.license_info.rat_support.append(RATType.NR)

                self.supported_rats = self.license_info.rat_support
        except Exception:
            pass

    def _calculate_constraints(self) -> None:
        """Calculate derived constraints from discovered capabilities.

        NOTE: License aggregation limits (max_aggregation_mhz) are enforced by
        Amarisoft at startup and may not be exposed via the Remote API.
        If not discovered, we use a conservative default of 40 MHz.
        Check your license or startup logs for the actual limit:
            grep "aggregation" /tmp/enb.log
        """
        # Max MIMO from SDR cards
        if self.sdr_cards:
            num_sdr_devices = len(self.sdr_cards) * 2  # Each card = 2 logical devices
            if num_sdr_devices >= 4:
                self.max_mimo_layers = 8
            elif num_sdr_devices >= 2:
                self.max_mimo_layers = 4

        # Supported RATs (default if not discovered)
        if not self.supported_rats:
            self.supported_rats = [RATType.LTE, RATType.NR]

        # License constraints - use discovered values or conservative defaults
        # IMPORTANT: 40 MHz is a common license limit; check your actual license
        # if you get "License error: total aggregation exceeds limit" errors
        if self.license_info is None or self.max_bandwidth_mhz <= 0:
            self.max_bandwidth_mhz = 40  # Conservative default
        if self.license_info is None or self.max_aggregation_mhz <= 0:
            self.max_aggregation_mhz = 40  # Conservative default (common limit)
        if self.license_info is None or self.max_cells == 0:
            self.max_cells = 1

        # Feature flags
        self.features.setdefault("carrier_aggregation", self.max_cells > 1)
        self.features.setdefault("endc", RATType.NR in self.supported_rats)
        self.features.setdefault("volte", self.services_available.get("ims", False))

        # UE Simulator support (from license)
        if self.license_info:
            self.features.setdefault("ue_sim", self.license_info.has_ue_sim)
            self.features.setdefault("ims", self.license_info.has_ims)
            self.features.setdefault("5gc", self.license_info.has_5gc)
        else:
            self.features.setdefault("ue_sim", False)
            self.features.setdefault("ims", self.services_available.get("ims", False))
            self.features.setdefault("5gc", False)

    def summary(self) -> str:
        """Generate a human-readable summary of capabilities."""
        lines = [
            "=" * 60,
            "AMARISOFT CALLBOX CAPABILITIES",
            "=" * 60,
            f"Hostname: {self.hostname}",
            f"Amarisoft Version: {self.amarisoft_version}",
            "",
            "--- Hardware ---",
            f"SDR Cards: {len(self.sdr_cards)}",
        ]

        for sdr in self.sdr_cards:
            lines.append(f"  - {sdr.board_type} (Serial: {sdr.serial})")

        lines.extend(
            [
                "",
                "--- License ---",
            ]
        )

        if self.license_info:
            lines.extend(
                [
                    f"User: {self.license_info.user_name}",
                    f"Valid Until: {self.license_info.valid_until}",
                    f"Products: {', '.join(self.license_info.products)}",
                ]
            )

        lines.extend(
            [
                "",
                "--- Constraints ---",
                f"Max Cells: {self.max_cells}",
                f"Max Bandwidth: {self.max_bandwidth_mhz} MHz",
                f"Max Aggregation: {self.max_aggregation_mhz} MHz (Σ bandwidth × MIMO)",
                f"Max MIMO Layers: {self.max_mimo_layers}",
                f"Supported RATs: {', '.join(r.value for r in self.supported_rats)}",
                "",
                "--- Services ---",
            ]
        )

        for svc, available in self.services_available.items():
            port = getattr(self.service_ports, svc, "?")
            status = "✅" if available else "❌"
            lines.append(f"  {svc.upper()}: {status} (port {port})")

        lines.extend(
            [
                "",
                "--- Features ---",
            ]
        )
        for feature, enabled in self.features.items():
            status = "✅" if enabled else "❌"
            lines.append(f"  {feature}: {status}")

        lines.extend(
            [
                "",
                "--- Active Cells ---",
            ]
        )

        for cell in self.cells:
            lines.append(
                f"  Cell {cell.cell_id}: {cell.rat.value} Band {cell.band} "
                f"{cell.bandwidth_mhz}MHz {cell.mimo_layers_dl}x{cell.mimo_layers_ul} MIMO"
            )

        lines.append("=" * 60)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Export capabilities as a dictionary."""
        return {
            "hostname": self.hostname,
            "amarisoft_version": self.amarisoft_version,
            "sdr_cards": [
                {
                    "device_id": s.device_id,
                    "board_type": s.board_type,
                    "serial": s.serial,
                    "max_bandwidth_mhz": s.max_bandwidth_mhz,
                }
                for s in self.sdr_cards
            ],
            "license": {
                "user_name": self.license_info.user_name if self.license_info else None,
                "valid_until": (
                    self.license_info.valid_until if self.license_info else None
                ),
                "products": self.license_info.products if self.license_info else [],
            },
            "constraints": {
                "max_cells": self.max_cells,
                "max_bandwidth_mhz": self.max_bandwidth_mhz,
                "max_aggregation_mhz": self.max_aggregation_mhz,
                "max_mimo_layers": self.max_mimo_layers,
                "supported_rats": [r.value for r in self.supported_rats],
            },
            "services": self.services_available,
            "service_ports": {
                "enb": self.service_ports.enb,
                "mme": self.service_ports.mme,
                "ims": self.service_ports.ims,
                "ue": self.service_ports.ue,
            },
            "features": self.features,
            "cells": [
                {
                    "cell_id": c.cell_id,
                    "rat": c.rat.value,
                    "band": c.band,
                    "bandwidth_mhz": c.bandwidth_mhz,
                    "mimo_dl": c.mimo_layers_dl,
                    "mimo_ul": c.mimo_layers_ul,
                }
                for c in self.cells
            ],
        }


# ══════════════════════════════════════════════════════════════
# Constraint Definitions
# ══════════════════════════════════════════════════════════════

# LTE bandwidth options (RB -> MHz)
LTE_BANDWIDTH_OPTIONS = {
    6: 1.4,
    15: 3,
    25: 5,
    50: 10,
    75: 15,
    100: 20,
}

# NR bandwidth options per subcarrier spacing
NR_BANDWIDTH_OPTIONS = {
    15: [5, 10, 15, 20, 25, 30, 40, 50],  # SCS 15kHz
    30: [5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100],  # SCS 30kHz
    60: [10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100],  # SCS 60kHz
    120: [50, 100, 200, 400],  # SCS 120kHz (FR2)
}

# QCI definitions
QCI_DEFINITIONS = {
    1: {
        "type": "gbr",
        "priority": 2,
        "delay_ms": 100,
        "loss": 1e-2,
        "name": "Conversational Voice",
    },
    2: {
        "type": "gbr",
        "priority": 4,
        "delay_ms": 150,
        "loss": 1e-3,
        "name": "Conversational Video",
    },
    3: {
        "type": "gbr",
        "priority": 3,
        "delay_ms": 50,
        "loss": 1e-3,
        "name": "Real Time Gaming",
    },
    4: {
        "type": "gbr",
        "priority": 5,
        "delay_ms": 300,
        "loss": 1e-6,
        "name": "Non-Conv Video (Buffered)",
    },
    5: {
        "type": "non-gbr",
        "priority": 1,
        "delay_ms": 100,
        "loss": 1e-6,
        "name": "IMS Signaling",
    },
    6: {
        "type": "non-gbr",
        "priority": 6,
        "delay_ms": 300,
        "loss": 1e-6,
        "name": "Video (Buffered)",
    },
    7: {
        "type": "non-gbr",
        "priority": 7,
        "delay_ms": 100,
        "loss": 1e-3,
        "name": "Voice/Video/Interactive Gaming",
    },
    8: {
        "type": "non-gbr",
        "priority": 8,
        "delay_ms": 300,
        "loss": 1e-6,
        "name": "Video (Buffered)",
    },
    9: {
        "type": "non-gbr",
        "priority": 9,
        "delay_ms": 300,
        "loss": 1e-6,
        "name": "Video (Buffered)/TCP",
    },
}

# TX/RX gain constraints
RF_GAIN_CONSTRAINTS = {
    "wired": {
        "tx_gain_min": 50,
        "tx_gain_max": 70,
        "rx_gain_min": 0,
        "rx_gain_max": 20,
    },
    "wireless": {
        "tx_gain_min": 80,
        "tx_gain_max": 95,
        "rx_gain_min": 50,
        "rx_gain_max": 70,
    },
    "absolute": {
        "tx_gain_min": 0,
        "tx_gain_max": 100,
        "rx_gain_min": 0,
        "rx_gain_max": 100,
    },
}

# MCS constraints
MCS_CONSTRAINTS = {
    "lte": {"min": 0, "max": 28},
    "nr": {"min": 0, "max": 31},
}


class CapabilityChecker:
    """Validates operations against device capabilities.

    Use this class to check if operations are valid before sending
    commands to the device, preventing errors and providing clear
    error messages.
    """

    def __init__(self, capabilities: DeviceCapabilities | None = None):
        """Initialize the checker.

        Args:
            capabilities: Device capabilities. If None, uses permissive defaults.
        """
        self.caps = capabilities or DeviceCapabilities()

    def validate_cell_config(
        self,
        bandwidth_mhz: int | None = None,
        mimo_layers: int | None = None,
        rat: RATType | None = None,
        band: int | None = None,
    ) -> None:
        """Validate cell configuration parameters.

        Raises:
            InvalidParameterError: If any parameter violates constraints.
        """
        if bandwidth_mhz is not None:
            if bandwidth_mhz > self.caps.max_bandwidth_mhz:
                raise InvalidParameterError(
                    f"Bandwidth {bandwidth_mhz}MHz exceeds license limit of "
                    f"{self.caps.max_bandwidth_mhz}MHz"
                )

        if mimo_layers is not None:
            if mimo_layers > self.caps.max_mimo_layers:
                raise InvalidParameterError(
                    f"MIMO {mimo_layers} layers exceeds hardware limit of "
                    f"{self.caps.max_mimo_layers} layers"
                )
            if mimo_layers not in [1, 2, 4, 8]:
                raise InvalidParameterError(
                    f"MIMO layers must be 1, 2, 4, or 8 (got {mimo_layers})"
                )

        if rat is not None:
            if rat not in self.caps.supported_rats:
                raise InvalidParameterError(
                    f"RAT {rat.value} not supported by license. "
                    f"Supported: {[r.value for r in self.caps.supported_rats]}"
                )

    def validate_rf_gain(
        self,
        tx_gain: float | None = None,
        rx_gain: float | None = None,
        mode: str = "absolute",
    ) -> None:
        """Validate RF gain parameters.

        Args:
            tx_gain: TX gain in dB.
            rx_gain: RX gain in dB.
            mode: Constraint mode ("wired", "wireless", or "absolute").

        Raises:
            InvalidParameterError: If gain values are out of range.
        """
        constraints = RF_GAIN_CONSTRAINTS.get(mode, RF_GAIN_CONSTRAINTS["absolute"])

        if tx_gain is not None:
            if not constraints["tx_gain_min"] <= tx_gain <= constraints["tx_gain_max"]:
                raise InvalidParameterError(
                    f"TX gain {tx_gain}dB out of range for {mode} mode "
                    f"({constraints['tx_gain_min']}-{constraints['tx_gain_max']}dB)"
                )

        if rx_gain is not None:
            if not constraints["rx_gain_min"] <= rx_gain <= constraints["rx_gain_max"]:
                raise InvalidParameterError(
                    f"RX gain {rx_gain}dB out of range for {mode} mode "
                    f"({constraints['rx_gain_min']}-{constraints['rx_gain_max']}dB)"
                )

    def validate_mcs(
        self,
        mcs: int,
        rat: RATType = RATType.LTE,
    ) -> None:
        """Validate MCS value.

        Raises:
            InvalidParameterError: If MCS is out of range.
        """
        key = "nr" if rat == RATType.NR else "lte"
        constraints = MCS_CONSTRAINTS[key]

        if not constraints["min"] <= mcs <= constraints["max"]:
            raise InvalidParameterError(
                f"MCS {mcs} out of range for {rat.value} "
                f"({constraints['min']}-{constraints['max']})"
            )

    def validate_qci(self, qci: int) -> None:
        """Validate QCI value.

        Raises:
            InvalidParameterError: If QCI is invalid.
        """
        if qci not in QCI_DEFINITIONS:
            raise InvalidParameterError(
                f"QCI {qci} is not a standard QCI value. "
                f"Valid QCIs: {list(QCI_DEFINITIONS.keys())}"
            )

    def validate_total_aggregation(
        self,
        cells: list[dict[str, int | float]] | None = None,
        total_aggregation_mhz: float | None = None,
    ) -> None:
        """Validate total aggregation against license limit.

        Amarisoft licenses limit total aggregation, calculated as:
            total_aggregation = Σ (cell_bandwidth × MIMO_layers)

        Args:
            cells: List of cell configurations, each with:
                - bandwidth_mhz: Cell bandwidth in MHz
                - mimo_layers: Number of MIMO layers (DL)
            total_aggregation_mhz: Pre-calculated total aggregation (alternative to cells)

        Raises:
            InvalidParameterError: If total aggregation exceeds license limit.

        Example:
            # Validate cell configurations
            checker.validate_total_aggregation(cells=[
                {"bandwidth_mhz": 20, "mimo_layers": 2},  # 40 MHz
                {"bandwidth_mhz": 20, "mimo_layers": 2},  # 40 MHz
            ])  # Total = 80 MHz

            # Or validate pre-calculated value
            checker.validate_total_aggregation(total_aggregation_mhz=80)
        """
        if total_aggregation_mhz is None and cells is None:
            raise InvalidParameterError(
                "Must provide either 'cells' or 'total_aggregation_mhz'"
            )

        if total_aggregation_mhz is None:
            total_aggregation_mhz = sum(
                cell.get("bandwidth_mhz", 0) * cell.get("mimo_layers", 1)
                for cell in (cells or [])
            )

        max_aggregation = self.caps.max_aggregation_mhz
        if total_aggregation_mhz > max_aggregation:
            raise InvalidParameterError(
                f"Total aggregation {total_aggregation_mhz} MHz exceeds license limit "
                f"of {max_aggregation} MHz. "
                f"Total aggregation = Σ(bandwidth × MIMO_layers). "
                f"Contact sales@amarisoft.com for license upgrade."
            )

    def calculate_total_aggregation(
        self,
        cells: list[dict[str, int | float]],
    ) -> float:
        """Calculate total aggregation for a list of cells.

        Args:
            cells: List of cell configurations, each with:
                - bandwidth_mhz: Cell bandwidth in MHz
                - mimo_layers: Number of MIMO layers (DL)

        Returns:
            Total aggregation in MHz.
        """
        return sum(
            cell.get("bandwidth_mhz", 0) * cell.get("mimo_layers", 1) for cell in cells
        )

    def validate_service_available(self, service: str) -> None:
        """Check if a service is available.

        Raises:
            InvalidParameterError: If service is not connected.
        """
        if not self.caps.services_available.get(service, False):
            raise InvalidParameterError(
                f"Service '{service}' is not available. "
                f"Connected services: {[k for k, v in self.caps.services_available.items() if v]}"
            )

    def validate_feature(self, feature: str) -> None:
        """Check if a feature is enabled.

        Raises:
            InvalidParameterError: If feature is not enabled.
        """
        if not self.caps.features.get(feature, False):
            raise InvalidParameterError(
                f"Feature '{feature}' is not enabled on this device."
            )

    def get_qci_info(self, qci: int) -> dict[str, Any]:
        """Get information about a QCI value.

        Args:
            qci: QCI value.

        Returns:
            Dictionary with QCI details.

        Raises:
            InvalidParameterError: If QCI is not valid (1-9).
        """
        if qci not in QCI_DEFINITIONS:
            raise InvalidParameterError(
                f"QCI {qci} is not a standard QCI value. "
                f"Valid QCIs: {list(QCI_DEFINITIONS.keys())}"
            )
        return QCI_DEFINITIONS[qci]


# ══════════════════════════════════════════════════════════════
# Default Callbox Configuration (CBM-2024121101)
# ══════════════════════════════════════════════════════════════


def get_default_capabilities() -> DeviceCapabilities:
    """Get default capabilities for CBM-2024121101 Callbox.

    Based on discovered configuration from device inspection.
    """
    caps = DeviceCapabilities(
        hostname="CBM-2024121101",
        os_version="Fedora 39",
        amarisoft_version="2024-09-13",
        sdr_cards=[
            SDRInfo(
                device_id=0,
                board_id="0x4b01",
                board_type="SDR50",
                serial="202405001019",
                fpga_revision="2024-07-02",
                software_version="2024-09-11",
                dna="0x006845482681a85c",
                max_bandwidth_mhz=100,
            ),
        ],
        license_info=LicenseInfo(
            user_name="Meta Platforms",
            license_uid="NISCBM02_FRE6530",
            valid_until="license_server",
            products=["ltemme", "lteims", "ltembmsgw", "lteenb", "lteview"],
            rat_support=[RATType.LTE, RATType.NR],
            max_cells=1,
            max_bandwidth_mhz=40,  # Conservative default - check your license!
            max_aggregation_mhz=40,  # Conservative default - check your license!
        ),
        service_ports=ServicePorts(
            enb=9001,
            mme=9000,
            ims=9003,  # Note: Non-default port
            ue=9003,
            mbms=9004,
        ),
        max_cells=1,
        max_bandwidth_mhz=40,  # Conservative default - check your license!
        max_aggregation_mhz=40,  # Conservative default - check your license!
        max_mimo_layers=4,
        supported_rats=[RATType.LTE, RATType.NR],
        features={
            "carrier_aggregation": False,
            "endc": True,
            "volte": True,
            "5gc": True,
        },
        services_available={
            "enb": True,
            "mme": True,
            "ims": True,
            "ue": False,
        },
    )

    return caps


def get_capabilities_with_aggregation_limit(
    max_aggregation_mhz: int,
    max_bandwidth_mhz: int | None = None,
) -> DeviceCapabilities:
    """Get default capabilities with a specific aggregation limit.

    Use this when you know your license's aggregation limit
    (e.g., from Amarisoft startup logs showing "License error: ... only allows up to X MHz").

    Args:
        max_aggregation_mhz: Your license's total aggregation limit in MHz.
            This is calculated as: Σ(cell_bandwidth × MIMO_layers)
        max_bandwidth_mhz: Optional per-cell bandwidth limit. Defaults to
            same as aggregation limit.

    Returns:
        DeviceCapabilities with the specified limits.

    Example:
        # If your license shows "only allows up to 40 MHz"
        caps = get_capabilities_with_aggregation_limit(40)
        checker = CapabilityChecker(caps)

        # Validate before applying config
        checker.validate_total_aggregation(cells=[
            {"bandwidth_mhz": 20, "mimo_layers": 2},  # 40 MHz - OK
        ])
    """
    caps = get_default_capabilities()
    caps.max_aggregation_mhz = max_aggregation_mhz
    caps.max_bandwidth_mhz = max_bandwidth_mhz or max_aggregation_mhz
    if caps.license_info:
        caps.license_info.max_aggregation_mhz = max_aggregation_mhz
        caps.license_info.max_bandwidth_mhz = max_bandwidth_mhz or max_aggregation_mhz
    return caps


# ══════════════════════════════════════════════════════════════
# Validation Decorators
# ══════════════════════════════════════════════════════════════


def validate_rf_params(
    tx_gain_param: str = "tx_gain",
    rx_gain_param: str = "rx_gain",
    mode: str = "absolute",
) -> Callable:
    """Decorator to validate RF gain parameters.

    Args:
        tx_gain_param: Parameter name for TX gain.
        rx_gain_param: Parameter name for RX gain.
        mode: Constraint mode ("wired", "wireless", "absolute").

    Example::

        @validate_rf_params(mode="wired")
        def set_rf_config(self, tx_gain=None, rx_gain=None):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get the capability checker if available
            checker = getattr(self, "_capability_checker", None)
            if checker is None:
                # Try to get from parent callbox
                callbox = getattr(self, "_callbox", None)
                if callbox:
                    checker = getattr(callbox, "_capability_checker", None)

            if checker:
                tx_gain = kwargs.get(tx_gain_param)
                rx_gain = kwargs.get(rx_gain_param)
                checker.validate_rf_gain(tx_gain=tx_gain, rx_gain=rx_gain, mode=mode)

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def validate_mcs_param(
    mcs_param: str = "mcs",
    rat: RATType = RATType.LTE,
) -> Callable:
    """Decorator to validate MCS parameters.

    Args:
        mcs_param: Parameter name for MCS value.
        rat: Radio access technology (LTE or NR).

    Example::

        @validate_mcs_param(mcs_param="pdsch_mcs", rat=RATType.LTE)
        def set_dl_config(self, pdsch_mcs=None):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            checker = getattr(self, "_capability_checker", None)
            if checker is None:
                callbox = getattr(self, "_callbox", None)
                if callbox:
                    checker = getattr(callbox, "_capability_checker", None)

            mcs = kwargs.get(mcs_param)
            if checker and mcs is not None:
                checker.validate_mcs(mcs, rat=rat)

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def validate_qci_param(qci_param: str = "qci") -> Callable:
    """Decorator to validate QCI parameters.

    Args:
        qci_param: Parameter name for QCI value.

    Example::

        @validate_qci_param()
        def activate_bearer(self, qci=5):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            checker = getattr(self, "_capability_checker", None)
            if checker is None:
                callbox = getattr(self, "_callbox", None)
                if callbox:
                    checker = getattr(callbox, "_capability_checker", None)

            qci = kwargs.get(qci_param)
            if checker and qci is not None:
                checker.validate_qci(qci)

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def require_service(service: str) -> Callable:
    """Decorator to require a specific service to be available.

    Args:
        service: Service name ("enb", "mme", "ims", "ue").

    Example::

        @require_service("ims")
        def make_call(self, ...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            checker = getattr(self, "_capability_checker", None)
            if checker is None:
                callbox = getattr(self, "_callbox", None)
                if callbox:
                    checker = getattr(callbox, "_capability_checker", None)

            if checker:
                checker.validate_service_available(service)

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def require_feature(feature: str) -> Callable:
    """Decorator to require a specific feature to be enabled.

    Args:
        feature: Feature name (e.g., "volte", "5gc", "carrier_aggregation").

    Example::

        @require_feature("volte")
        def setup_volte_call(self, ...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            checker = getattr(self, "_capability_checker", None)
            if checker is None:
                callbox = getattr(self, "_callbox", None)
                if callbox:
                    checker = getattr(callbox, "_capability_checker", None)

            if checker:
                checker.validate_feature(feature)

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def validate_bandwidth(bandwidth_param: str = "bandwidth_mhz") -> Callable:
    """Decorator to validate bandwidth against license constraints.

    Args:
        bandwidth_param: Parameter name for bandwidth value.

    Example::

        @validate_bandwidth()
        def configure_cell(self, bandwidth_mhz=20):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            checker = getattr(self, "_capability_checker", None)
            if checker is None:
                callbox = getattr(self, "_callbox", None)
                if callbox:
                    checker = getattr(callbox, "_capability_checker", None)

            bandwidth = kwargs.get(bandwidth_param)
            if checker and bandwidth is not None:
                checker.validate_cell_config(bandwidth_mhz=bandwidth)

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


# ══════════════════════════════════════════════════════════════
# Capability Context Manager
# ══════════════════════════════════════════════════════════════


class ValidationContext:
    """Context manager for enabling validation on a Callbox.

    Example::

        from amarisoft import Callbox
        from amarisoft.capabilities import ValidationContext

        with Callbox("192.168.1.80") as cb:
            cb.connect_all()

            # Enable validation
            with ValidationContext(cb):
                # These operations will be validated
                cb.enb.rf(tx_gain=90)  # Raises if out of range

            # Outside the context, no validation
            cb.enb.rf(tx_gain=150)  # No error from validation
    """

    def __init__(
        self, callbox: "Callbox", capabilities: DeviceCapabilities | None = None
    ):
        """Initialize validation context.

        Args:
            callbox: Callbox instance to validate.
            capabilities: Override capabilities. If None, discovers from device.
        """
        self.callbox = callbox
        self.capabilities = capabilities
        self._old_checker = None

    def __enter__(self) -> "ValidationContext":
        """Enter validation context."""
        if self.capabilities is None:
            self.capabilities = DeviceCapabilities.from_callbox(self.callbox)

        self._old_checker = getattr(self.callbox, "_capability_checker", None)
        self.callbox._capability_checker = CapabilityChecker(self.capabilities)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit validation context."""
        self.callbox._capability_checker = self._old_checker
        return False

    @property
    def checker(self) -> CapabilityChecker:
        """Get the capability checker."""
        return self.callbox._capability_checker
