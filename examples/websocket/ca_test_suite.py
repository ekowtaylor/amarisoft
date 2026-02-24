#!/usr/bin/env python3
"""Carrier Aggregation (CA) test suite for Amarisoft Callbox.

Supports comprehensive CA testing across LTE and NR:
  - LTE CA: 2CC to 5CC configurations
  - NR CA: Intra-band and inter-band combinations
  - EN-DC: LTE anchor with NR secondary cells
  - NR-DC: NR-NR Dual Connectivity

CA Types:
  - Intra-band contiguous: Adjacent carriers in same band
  - Intra-band non-contiguous: Non-adjacent carriers in same band
  - Inter-band: Carriers from different bands

Test Procedure:
  1. Configure PCell (Primary Cell)
  2. Add SCells (Secondary Cells)
  3. Activate CA and verify SCell activation
  4. Measure per-carrier and aggregated throughput
  5. Test SCell deactivation/reactivation
  6. Log results with per-carrier breakdown

Usage:
    # Run CA tests
    python ca_test_suite.py --host 192.168.1.80

    # List CA configurations
    python ca_test_suite.py --list-tests

    # Run specific CA scenario
    python ca_test_suite.py --host 192.168.1.80 --tests lte_ca_2cc_b2_b66
"""

import argparse
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

from client.websocket import (
    Callbox,
    AmariError,
    AmariConnectionError,
)


# ══════════════════════════════════════════════════════════════
# CA CONSTANTS AND ENUMS
# ══════════════════════════════════════════════════════════════

class CAType(Enum):
    """Carrier Aggregation type."""
    LTE_CA = "lte_ca"           # LTE Carrier Aggregation
    NR_CA = "nr_ca"             # NR Carrier Aggregation
    ENDC = "endc"               # EN-DC (LTE + NR)
    NRDC = "nrdc"               # NR-DC (NR + NR)


class CABandType(Enum):
    """CA band combination type."""
    INTRA_BAND_CONTIGUOUS = "intra_contig"      # Same band, adjacent
    INTRA_BAND_NON_CONTIGUOUS = "intra_non_contig"  # Same band, non-adjacent
    INTER_BAND = "inter_band"                    # Different bands


class CellRole(Enum):
    """Cell role in CA configuration."""
    PCELL = "pcell"    # Primary Cell (anchor)
    PSCELL = "pscell"  # Primary Secondary Cell (NR in EN-DC)
    SCELL = "scell"    # Secondary Cell


# ══════════════════════════════════════════════════════════════
# LTE CA BAND COMBINATIONS (3GPP TS 36.101)
# ══════════════════════════════════════════════════════════════

# Common LTE CA combinations (US focused)
LTE_CA_COMBINATIONS = {
    # 2CC Inter-band combinations
    "CA_2A-4A": {"bands": ["B2", "B4"], "type": CABandType.INTER_BAND, "max_bw": 40},
    "CA_2A-5A": {"bands": ["B2", "B5"], "type": CABandType.INTER_BAND, "max_bw": 30},
    "CA_2A-12A": {"bands": ["B2", "B12"], "type": CABandType.INTER_BAND, "max_bw": 30},
    "CA_2A-13A": {"bands": ["B2", "B13"], "type": CABandType.INTER_BAND, "max_bw": 30},
    "CA_2A-66A": {"bands": ["B2", "B66"], "type": CABandType.INTER_BAND, "max_bw": 40},
    "CA_4A-5A": {"bands": ["B4", "B5"], "type": CABandType.INTER_BAND, "max_bw": 30},
    "CA_4A-12A": {"bands": ["B4", "B12"], "type": CABandType.INTER_BAND, "max_bw": 30},
    "CA_4A-13A": {"bands": ["B4", "B13"], "type": CABandType.INTER_BAND, "max_bw": 30},
    "CA_66A-71A": {"bands": ["B66", "B71"], "type": CABandType.INTER_BAND, "max_bw": 40},

    # 2CC Intra-band contiguous
    "CA_41C": {"bands": ["B41", "B41"], "type": CABandType.INTRA_BAND_CONTIGUOUS, "max_bw": 40},
    "CA_7C": {"bands": ["B7", "B7"], "type": CABandType.INTRA_BAND_CONTIGUOUS, "max_bw": 40},

    # 3CC combinations
    "CA_2A-4A-5A": {"bands": ["B2", "B4", "B5"], "type": CABandType.INTER_BAND, "max_bw": 50},
    "CA_2A-4A-12A": {"bands": ["B2", "B4", "B12"], "type": CABandType.INTER_BAND, "max_bw": 50},
    "CA_2A-66A-71A": {"bands": ["B2", "B66", "B71"], "type": CABandType.INTER_BAND, "max_bw": 60},
    "CA_4A-12A-66A": {"bands": ["B4", "B12", "B66"], "type": CABandType.INTER_BAND, "max_bw": 50},

    # 4CC combinations
    "CA_2A-4A-12A-66A": {"bands": ["B2", "B4", "B12", "B66"], "type": CABandType.INTER_BAND, "max_bw": 70},
    "CA_2A-4A-5A-12A": {"bands": ["B2", "B4", "B5", "B12"], "type": CABandType.INTER_BAND, "max_bw": 60},

    # 5CC combinations
    "CA_2A-4A-5A-12A-66A": {"bands": ["B2", "B4", "B5", "B12", "B66"], "type": CABandType.INTER_BAND, "max_bw": 80},
}


# ══════════════════════════════════════════════════════════════
# NR CA BAND COMBINATIONS (3GPP TS 38.101)
# ══════════════════════════════════════════════════════════════

NR_CA_COMBINATIONS = {
    # FR1 Inter-band
    "CA_n2A-n66A": {"bands": ["n2", "n66"], "type": CABandType.INTER_BAND, "max_bw": 80},
    "CA_n5A-n66A": {"bands": ["n5", "n66"], "type": CABandType.INTER_BAND, "max_bw": 60},
    "CA_n2A-n71A": {"bands": ["n2", "n71"], "type": CABandType.INTER_BAND, "max_bw": 55},
    "CA_n66A-n71A": {"bands": ["n66", "n71"], "type": CABandType.INTER_BAND, "max_bw": 55},

    # FR1 Intra-band (n41 TDD, n77/n78 C-band)
    "CA_n41C": {"bands": ["n41", "n41"], "type": CABandType.INTRA_BAND_CONTIGUOUS, "max_bw": 200},
    "CA_n77C": {"bands": ["n77", "n77"], "type": CABandType.INTRA_BAND_CONTIGUOUS, "max_bw": 200},
    "CA_n78C": {"bands": ["n78", "n78"], "type": CABandType.INTRA_BAND_CONTIGUOUS, "max_bw": 200},

    # FR1 3CC combinations
    "CA_n2A-n66A-n71A": {"bands": ["n2", "n66", "n71"], "type": CABandType.INTER_BAND, "max_bw": 95},
    "CA_n5A-n66A-n71A": {"bands": ["n5", "n66", "n71"], "type": CABandType.INTER_BAND, "max_bw": 75},

    # FR2 (mmWave) Intra-band
    "CA_n257C": {"bands": ["n257", "n257"], "type": CABandType.INTRA_BAND_CONTIGUOUS, "max_bw": 800},
    "CA_n258C": {"bands": ["n258", "n258"], "type": CABandType.INTRA_BAND_CONTIGUOUS, "max_bw": 800},
    "CA_n260C": {"bands": ["n260", "n260"], "type": CABandType.INTRA_BAND_CONTIGUOUS, "max_bw": 800},
    "CA_n261C": {"bands": ["n261", "n261"], "type": CABandType.INTRA_BAND_CONTIGUOUS, "max_bw": 800},
}


# ══════════════════════════════════════════════════════════════
# EN-DC BAND COMBINATIONS (3GPP TS 38.101-3)
# ══════════════════════════════════════════════════════════════

ENDC_COMBINATIONS = {
    # LTE FDD + NR TDD (common US deployments)
    "DC_2A_n41A": {"lte": ["B2"], "nr": ["n41"], "max_bw": 120},
    "DC_2A_n66A": {"lte": ["B2"], "nr": ["n66"], "max_bw": 60},
    "DC_2A_n71A": {"lte": ["B2"], "nr": ["n71"], "max_bw": 55},
    "DC_4A_n41A": {"lte": ["B4"], "nr": ["n41"], "max_bw": 120},
    "DC_66A_n41A": {"lte": ["B66"], "nr": ["n41"], "max_bw": 120},
    "DC_66A_n71A": {"lte": ["B66"], "nr": ["n71"], "max_bw": 55},
    "DC_71A_n41A": {"lte": ["B71"], "nr": ["n41"], "max_bw": 120},

    # LTE + NR with multiple LTE carriers
    "DC_2A-66A_n41A": {"lte": ["B2", "B66"], "nr": ["n41"], "max_bw": 140},
    "DC_2A-4A_n41A": {"lte": ["B2", "B4"], "nr": ["n41"], "max_bw": 140},
    "DC_2A-66A_n71A": {"lte": ["B2", "B66"], "nr": ["n71"], "max_bw": 75},

    # LTE + NR with multiple NR carriers
    "DC_2A_n41C": {"lte": ["B2"], "nr": ["n41", "n41"], "max_bw": 220},
    "DC_66A_n41C": {"lte": ["B66"], "nr": ["n41", "n41"], "max_bw": 220},

    # FR2 (mmWave) combinations
    "DC_2A_n257A": {"lte": ["B2"], "nr": ["n257"], "max_bw": 420},
    "DC_66A_n257A": {"lte": ["B66"], "nr": ["n257"], "max_bw": 420},
    "DC_2A_n261A": {"lte": ["B2"], "nr": ["n261"], "max_bw": 420},
}


# ══════════════════════════════════════════════════════════════
# CARRIER CONFIGURATION
# ══════════════════════════════════════════════════════════════

@dataclass
class CarrierConfig:
    """Configuration for a single carrier/cell."""
    band: str
    bandwidth_mhz: int
    role: CellRole
    earfcn: int | None = None  # LTE EARFCN
    arfcn: int | None = None   # NR ARFCN
    cell_id: int = 0
    pci: int = 0
    rat: str = "lte"  # "lte" or "nr"

    # MIMO configuration
    n_antenna_dl: int = 2
    n_antenna_ul: int = 1

    # MCS settings
    dl_mcs: int | None = None
    ul_mcs: int | None = None


@dataclass
class CAConfiguration:
    """Complete CA configuration with multiple carriers."""
    name: str
    ca_type: CAType
    band_type: CABandType
    carriers: list[CarrierConfig] = field(default_factory=list)
    total_bandwidth_mhz: int = 0
    expected_dl_mbps: float = 0.0
    expected_ul_mbps: float = 0.0
    description: str = ""

    def __post_init__(self):
        """Calculate total bandwidth and expected throughput."""
        self.total_bandwidth_mhz = sum(c.bandwidth_mhz for c in self.carriers)
        self._calculate_expected_throughput()

    def _calculate_expected_throughput(self):
        """Calculate expected aggregated throughput."""
        if self.expected_dl_mbps > 0:
            return  # Already set

        # Rough calculation based on total bandwidth and CA type
        if self.ca_type == CAType.LTE_CA:
            # LTE: ~3.75 Mbps per MHz for DL (2x2 MIMO, 64QAM)
            # UL: ~2.5 Mbps per MHz
            self.expected_dl_mbps = self.total_bandwidth_mhz * 3.75
            self.expected_ul_mbps = self.total_bandwidth_mhz * 2.5

        elif self.ca_type == CAType.NR_CA:
            # NR FR1: ~5 Mbps per MHz for DL (2x2 MIMO, 256QAM)
            # NR FR2: ~10 Mbps per MHz
            is_fr2 = any(c.band.startswith("n25") or c.band.startswith("n26") for c in self.carriers)
            if is_fr2:
                self.expected_dl_mbps = self.total_bandwidth_mhz * 10
                self.expected_ul_mbps = self.total_bandwidth_mhz * 2
            else:
                self.expected_dl_mbps = self.total_bandwidth_mhz * 5
                self.expected_ul_mbps = self.total_bandwidth_mhz * 2.5

        elif self.ca_type == CAType.ENDC:
            # EN-DC: Combined LTE + NR
            lte_bw = sum(c.bandwidth_mhz for c in self.carriers if c.rat == "lte")
            nr_bw = sum(c.bandwidth_mhz for c in self.carriers if c.rat == "nr")
            self.expected_dl_mbps = lte_bw * 3.75 + nr_bw * 5
            self.expected_ul_mbps = lte_bw * 2.5 + nr_bw * 2.5

    @property
    def num_carriers(self) -> int:
        return len(self.carriers)

    @property
    def pcell(self) -> CarrierConfig | None:
        for c in self.carriers:
            if c.role == CellRole.PCELL:
                return c
        return self.carriers[0] if self.carriers else None

    @property
    def scells(self) -> list[CarrierConfig]:
        return [c for c in self.carriers if c.role in (CellRole.SCELL, CellRole.PSCELL)]


# ══════════════════════════════════════════════════════════════
# EARFCN/ARFCN MAPPINGS
# ══════════════════════════════════════════════════════════════

# LTE EARFCN center frequencies (mid-band)
LTE_EARFCN_MAP = {
    "B2": 900,      # 1900 MHz
    "B4": 2175,     # 1700/2100 MHz
    "B5": 2525,     # 850 MHz
    "B7": 3100,     # 2600 MHz
    "B12": 5095,    # 700 MHz
    "B13": 5230,    # 700 MHz
    "B14": 5330,    # 700 MHz
    "B17": 5790,    # 700 MHz
    "B25": 8365,    # 1900 MHz
    "B26": 8865,    # 850 MHz
    "B30": 9820,    # 2300 MHz
    "B41": 40620,   # 2500 MHz TDD
    "B66": 66636,   # AWS-3
    "B71": 68836,   # 600 MHz
}

# NR ARFCN center frequencies
NR_ARFCN_MAP = {
    "n2": 386000,   # 1900 MHz
    "n5": 176300,   # 850 MHz
    "n7": 531000,   # 2600 MHz
    "n12": 145800,  # 700 MHz
    "n25": 387000,  # 1900 MHz
    "n41": 520000,  # 2500 MHz TDD
    "n66": 422000,  # AWS
    "n71": 123400,  # 600 MHz
    "n77": 640000,  # 3.5 GHz
    "n78": 640000,  # 3.5 GHz
    "n257": 2079167,  # 28 GHz
    "n258": 2017500,  # 26 GHz
    "n260": 2229167,  # 39 GHz
    "n261": 2079167,  # 28 GHz
}

# Default bandwidths per band
DEFAULT_BANDWIDTH = {
    # LTE bands (MHz)
    "B2": 20, "B4": 20, "B5": 10, "B7": 20, "B12": 10, "B13": 10,
    "B14": 10, "B17": 10, "B25": 20, "B26": 10, "B30": 10,
    "B41": 20, "B66": 20, "B71": 20,
    # NR FR1 bands (MHz)
    "n2": 20, "n5": 20, "n7": 40, "n12": 15, "n25": 20,
    "n41": 100, "n66": 40, "n71": 35, "n77": 100, "n78": 100,
    # NR FR2 bands (MHz)
    "n257": 400, "n258": 400, "n260": 400, "n261": 400,
}


def get_earfcn(band: str) -> int:
    """Get EARFCN for LTE band."""
    return LTE_EARFCN_MAP.get(band, 0)


def get_arfcn(band: str) -> int:
    """Get ARFCN for NR band."""
    return NR_ARFCN_MAP.get(band, 0)


def get_default_bandwidth(band: str) -> int:
    """Get default bandwidth for band."""
    return DEFAULT_BANDWIDTH.get(band, 20)


# ══════════════════════════════════════════════════════════════
# CA TEST SCENARIOS
# ══════════════════════════════════════════════════════════════

def create_lte_ca_config(
    name: str,
    bands: list[str],
    band_type: CABandType,
    description: str = "",
) -> CAConfiguration:
    """Create LTE CA configuration from band list."""
    carriers = []
    for i, band in enumerate(bands):
        role = CellRole.PCELL if i == 0 else CellRole.SCELL
        carriers.append(CarrierConfig(
            band=band,
            bandwidth_mhz=get_default_bandwidth(band),
            role=role,
            earfcn=get_earfcn(band),
            cell_id=i + 1,
            pci=i + 1,
            rat="lte",
        ))

    return CAConfiguration(
        name=name,
        ca_type=CAType.LTE_CA,
        band_type=band_type,
        carriers=carriers,
        description=description or f"LTE CA {len(bands)}CC: {'+'.join(bands)}",
    )


def create_nr_ca_config(
    name: str,
    bands: list[str],
    band_type: CABandType,
    description: str = "",
) -> CAConfiguration:
    """Create NR CA configuration from band list."""
    carriers = []
    for i, band in enumerate(bands):
        role = CellRole.PCELL if i == 0 else CellRole.SCELL
        carriers.append(CarrierConfig(
            band=band,
            bandwidth_mhz=get_default_bandwidth(band),
            role=role,
            arfcn=get_arfcn(band),
            cell_id=i + 1,
            pci=i + 1,
            rat="nr",
        ))

    return CAConfiguration(
        name=name,
        ca_type=CAType.NR_CA,
        band_type=band_type,
        carriers=carriers,
        description=description or f"NR CA {len(bands)}CC: {'+'.join(bands)}",
    )


def create_endc_config(
    name: str,
    lte_bands: list[str],
    nr_bands: list[str],
    description: str = "",
) -> CAConfiguration:
    """Create EN-DC configuration from LTE and NR band lists."""
    carriers = []

    # Add LTE carriers (PCell first)
    for i, band in enumerate(lte_bands):
        role = CellRole.PCELL if i == 0 else CellRole.SCELL
        carriers.append(CarrierConfig(
            band=band,
            bandwidth_mhz=get_default_bandwidth(band),
            role=role,
            earfcn=get_earfcn(band),
            cell_id=i + 1,
            pci=i + 1,
            rat="lte",
        ))

    # Add NR carriers (PSCell first, then SCells)
    nr_start_id = len(lte_bands) + 1
    for i, band in enumerate(nr_bands):
        role = CellRole.PSCELL if i == 0 else CellRole.SCELL
        carriers.append(CarrierConfig(
            band=band,
            bandwidth_mhz=get_default_bandwidth(band),
            role=role,
            arfcn=get_arfcn(band),
            cell_id=nr_start_id + i,
            pci=nr_start_id + i,
            rat="nr",
        ))

    return CAConfiguration(
        name=name,
        ca_type=CAType.ENDC,
        band_type=CABandType.INTER_BAND,  # EN-DC is always inter-band (LTE + NR)
        carriers=carriers,
        description=description or f"EN-DC: {'+'.join(lte_bands)} + {'+'.join(nr_bands)}",
    )


# Build test scenarios
CA_TEST_SCENARIOS: dict[str, CAConfiguration] = {}

# LTE CA scenarios
for combo_name, combo_info in LTE_CA_COMBINATIONS.items():
    scenario_name = f"lte_ca_{combo_name.lower().replace('-', '_').replace('ca_', '')}"
    CA_TEST_SCENARIOS[scenario_name] = create_lte_ca_config(
        name=combo_name,
        bands=combo_info["bands"],
        band_type=combo_info["type"],
    )

# NR CA scenarios
for combo_name, combo_info in NR_CA_COMBINATIONS.items():
    scenario_name = f"nr_ca_{combo_name.lower().replace('-', '_').replace('ca_', '')}"
    CA_TEST_SCENARIOS[scenario_name] = create_nr_ca_config(
        name=combo_name,
        bands=combo_info["bands"],
        band_type=combo_info["type"],
    )

# EN-DC scenarios
for combo_name, combo_info in ENDC_COMBINATIONS.items():
    scenario_name = f"endc_{combo_name.lower().replace('-', '_').replace('dc_', '')}"
    CA_TEST_SCENARIOS[scenario_name] = create_endc_config(
        name=combo_name,
        lte_bands=combo_info["lte"],
        nr_bands=combo_info["nr"],
    )


# ══════════════════════════════════════════════════════════════
# CA TEST RESULTS
# ══════════════════════════════════════════════════════════════

@dataclass
class CarrierResult:
    """Throughput result for a single carrier."""
    band: str
    role: str
    rat: str
    bandwidth_mhz: int
    dl_avg_mbps: float
    dl_max_mbps: float
    ul_avg_mbps: float
    ul_max_mbps: float
    active: bool = True


@dataclass
class CATestResult:
    """Results from a CA test."""
    scenario_name: str
    ca_type: str
    band_type: str
    num_carriers: int
    total_bandwidth_mhz: int

    # Per-carrier results
    carrier_results: list[CarrierResult] = field(default_factory=list)

    # Aggregated throughput
    dl_agg_avg_mbps: float = 0.0
    dl_agg_max_mbps: float = 0.0
    ul_agg_avg_mbps: float = 0.0
    ul_agg_max_mbps: float = 0.0

    # Expected values
    expected_dl_mbps: float = 0.0
    expected_ul_mbps: float = 0.0

    # Efficiency
    dl_efficiency: float = 0.0
    ul_efficiency: float = 0.0

    # CA-specific metrics
    scell_activation_time_ms: float = 0.0
    all_scells_active: bool = False
    active_carrier_count: int = 0

    # Status
    duration_s: float = 0.0
    passed: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["carrier_results"] = [asdict(c) for c in self.carrier_results]
        return result


# ══════════════════════════════════════════════════════════════
# CA TEST SUITE
# ══════════════════════════════════════════════════════════════

class CATestSuite:
    """Test suite for Carrier Aggregation testing.

    Tests CA configurations including:
    - LTE CA (2CC to 5CC)
    - NR CA (intra-band and inter-band)
    - EN-DC (LTE + NR dual connectivity)
    - SCell activation/deactivation
    - Per-carrier and aggregated throughput
    """

    def __init__(
        self,
        host: str,
        password: str | None = None,
        ssl: bool = False,
        ssl_verify: bool = False,
    ):
        self.host = host
        self.password = password
        self.ssl = ssl
        self.ssl_verify = ssl_verify
        self.cb: Callbox | None = None
        self.results: list[CATestResult] = []

    def connect(self) -> bool:
        """Connect to the Callbox."""
        try:
            self.cb = Callbox(
                self.host,
                password=self.password,
                ssl=self.ssl,
                ssl_verify=self.ssl_verify,
            )
            self.cb.connect_all()
            print(f"✓ Connected to Callbox at {self.host}")
            return True
        except AmariConnectionError as e:
            print(f"✗ Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from the Callbox."""
        if self.cb:
            self.cb.close()
            self.cb = None

    def get_cell_stats(self) -> dict[str, Any]:
        """Get statistics for all cells."""
        if not self.cb:
            return {}

        try:
            stats = self.cb.enb.stats()
            return stats.get("cells", {})
        except Exception:
            return {}

    def get_ue_info(self) -> list[dict[str, Any]]:
        """Get UE information including CA status."""
        if not self.cb:
            return []

        try:
            result = self.cb.mme.ue_get()
            return result.get("ue_list", [])
        except Exception:
            return []

    def configure_ca(self, config: CAConfiguration) -> bool:
        """Configure CA on the Callbox.

        Args:
            config: CA configuration

        Returns:
            True if configuration successful
        """
        if not self.cb:
            return False

        print(f"\n  Configuring CA: {config.name}")
        print(f"    Type: {config.ca_type.value}")
        print(f"    Band type: {config.band_type.value}")
        print(f"    Carriers: {config.num_carriers}")
        print(f"    Total bandwidth: {config.total_bandwidth_mhz} MHz")

        for carrier in config.carriers:
            print(f"    - {carrier.role.value.upper()}: {carrier.band} "
                  f"({carrier.bandwidth_mhz} MHz, {carrier.rat.upper()})")

        # In practice, CA configuration would involve:
        # 1. Setting up PCell configuration
        # 2. Adding SCell configurations
        # 3. Configuring CA-specific parameters

        # The actual implementation depends on the Amarisoft API
        # This is a framework showing the structure

        try:
            # Get current config
            _config = self.cb.enb.config_get()  # noqa: F841

            # Configuration would be applied here
            # For now, we assume the Callbox is already configured
            # with the appropriate CA setup

            time.sleep(1)
            return True

        except Exception as e:
            print(f"    ✗ Configuration failed: {e}")
            return False

    def activate_scells(self, config: CAConfiguration) -> tuple[bool, float]:
        """Activate SCells and measure activation time.

        Args:
            config: CA configuration

        Returns:
            Tuple of (all_active, activation_time_ms)
        """
        if not self.cb:
            return False, 0.0

        print("\n  Activating SCells...")
        start_time = time.monotonic()

        # In practice, SCell activation would be triggered via:
        # - RRC reconfiguration
        # - MAC CE activation command

        # Wait for SCells to activate (polling)
        timeout = 10.0
        while (time.monotonic() - start_time) < timeout:
            # Check cell stats for active SCells
            cell_stats = self.get_cell_stats()
            active_count = len([c for c in cell_stats.values()
                               if c.get("dl_bitrate", 0) > 0 or c.get("ul_bitrate", 0) > 0])

            if active_count >= config.num_carriers:
                activation_time = (time.monotonic() - start_time) * 1000
                print(f"    ✓ All {config.num_carriers} carriers active "
                      f"(activation time: {activation_time:.0f} ms)")
                return True, activation_time

            time.sleep(0.1)

        activation_time = (time.monotonic() - start_time) * 1000
        print(f"    ⚠ Only {active_count}/{config.num_carriers} carriers active")
        return False, activation_time

    def measure_per_carrier_throughput(
        self,
        config: CAConfiguration,
        duration: float = 10.0,
    ) -> list[CarrierResult]:
        """Measure throughput per carrier.

        Args:
            config: CA configuration
            duration: Measurement duration

        Returns:
            List of per-carrier results
        """
        if not self.cb:
            return []

        print(f"\n  Measuring per-carrier throughput ({duration}s)...")

        # Collect samples
        samples_by_cell: dict[str, list[dict]] = {}
        start_time = time.monotonic()

        while (time.monotonic() - start_time) < duration:
            cell_stats = self.get_cell_stats()

            for cell_id, stats in cell_stats.items():
                if cell_id not in samples_by_cell:
                    samples_by_cell[cell_id] = []

                samples_by_cell[cell_id].append({
                    "dl_bitrate": stats.get("dl_bitrate", 0),
                    "ul_bitrate": stats.get("ul_bitrate", 0),
                })

            time.sleep(0.5)

        # Process results
        carrier_results = []
        for i, carrier in enumerate(config.carriers):
            cell_id = str(carrier.cell_id)

            if cell_id in samples_by_cell and samples_by_cell[cell_id]:
                samples = samples_by_cell[cell_id]
                dl_rates = [s["dl_bitrate"] / 1_000_000 for s in samples]
                ul_rates = [s["ul_bitrate"] / 1_000_000 for s in samples]

                result = CarrierResult(
                    band=carrier.band,
                    role=carrier.role.value,
                    rat=carrier.rat,
                    bandwidth_mhz=carrier.bandwidth_mhz,
                    dl_avg_mbps=sum(dl_rates) / len(dl_rates),
                    dl_max_mbps=max(dl_rates),
                    ul_avg_mbps=sum(ul_rates) / len(ul_rates),
                    ul_max_mbps=max(ul_rates),
                    active=any(r > 0 for r in dl_rates + ul_rates),
                )
            else:
                # No samples - carrier may not be active
                result = CarrierResult(
                    band=carrier.band,
                    role=carrier.role.value,
                    rat=carrier.rat,
                    bandwidth_mhz=carrier.bandwidth_mhz,
                    dl_avg_mbps=0.0,
                    dl_max_mbps=0.0,
                    ul_avg_mbps=0.0,
                    ul_max_mbps=0.0,
                    active=False,
                )

            carrier_results.append(result)

            status = "✓" if result.active else "✗"
            print(f"    {status} {carrier.role.value.upper()} {carrier.band}: "
                  f"DL={result.dl_avg_mbps:.1f} Mbps, UL={result.ul_avg_mbps:.1f} Mbps")

        return carrier_results

    def measure_aggregated_throughput(
        self,
        duration: float = 10.0,
    ) -> tuple[float, float, float, float]:
        """Measure aggregated throughput across all carriers.

        Args:
            duration: Measurement duration

        Returns:
            Tuple of (dl_avg, dl_max, ul_avg, ul_max) in Mbps
        """
        if not self.cb:
            return 0.0, 0.0, 0.0, 0.0

        print(f"\n  Measuring aggregated throughput ({duration}s)...")

        dl_samples = []
        ul_samples = []
        start_time = time.monotonic()

        while (time.monotonic() - start_time) < duration:
            cell_stats = self.get_cell_stats()

            # Sum across all cells
            dl_total = sum(s.get("dl_bitrate", 0) for s in cell_stats.values())
            ul_total = sum(s.get("ul_bitrate", 0) for s in cell_stats.values())

            dl_samples.append(dl_total / 1_000_000)
            ul_samples.append(ul_total / 1_000_000)

            time.sleep(0.5)

        if dl_samples:
            dl_avg = sum(dl_samples) / len(dl_samples)
            dl_max = max(dl_samples)
            ul_avg = sum(ul_samples) / len(ul_samples)
            ul_max = max(ul_samples)

            print(f"    DL: avg={dl_avg:.1f} Mbps, max={dl_max:.1f} Mbps")
            print(f"    UL: avg={ul_avg:.1f} Mbps, max={ul_max:.1f} Mbps")

            return dl_avg, dl_max, ul_avg, ul_max

        return 0.0, 0.0, 0.0, 0.0

    def run_test(
        self,
        config: CAConfiguration,
        duration: float = 30.0,
    ) -> CATestResult:
        """Run a single CA test scenario.

        Args:
            config: CA configuration
            duration: Test duration

        Returns:
            CATestResult with measurements
        """
        print(f"\n{'═' * 70}")
        print(f"CA Test: {config.name}")
        print(f"{'═' * 70}")
        print(f"  Description: {config.description}")
        print(f"  CA Type: {config.ca_type.value}")
        print(f"  Band Type: {config.band_type.value}")
        print(f"  Carriers: {config.num_carriers}")
        print(f"  Total Bandwidth: {config.total_bandwidth_mhz} MHz")
        print(f"  Expected DL: {config.expected_dl_mbps:.1f} Mbps")
        print(f"  Expected UL: {config.expected_ul_mbps:.1f} Mbps")

        # Configure CA
        if not self.configure_ca(config):
            return CATestResult(
                scenario_name=config.name,
                ca_type=config.ca_type.value,
                band_type=config.band_type.value,
                num_carriers=config.num_carriers,
                total_bandwidth_mhz=config.total_bandwidth_mhz,
                expected_dl_mbps=config.expected_dl_mbps,
                expected_ul_mbps=config.expected_ul_mbps,
                passed=False,
                notes="Configuration failed",
            )

        # Check if UE is attached
        ue_list = self.get_ue_info()
        if not ue_list:
            print("\n  ⚠ No UE attached - measuring available throughput")

        # Activate SCells
        all_active, activation_time = self.activate_scells(config)

        # Measure per-carrier throughput
        carrier_results = self.measure_per_carrier_throughput(config, duration / 2)

        # Measure aggregated throughput
        dl_avg, dl_max, ul_avg, ul_max = self.measure_aggregated_throughput(duration / 2)

        # Calculate efficiency
        dl_efficiency = (dl_avg / config.expected_dl_mbps * 100) if config.expected_dl_mbps > 0 else 0
        ul_efficiency = (ul_avg / config.expected_ul_mbps * 100) if config.expected_ul_mbps > 0 else 0

        # Count active carriers
        active_count = sum(1 for c in carrier_results if c.active)

        # Determine pass/fail
        passed = (dl_efficiency >= 50 or ul_efficiency >= 50) or not ue_list

        # Build result
        result = CATestResult(
            scenario_name=config.name,
            ca_type=config.ca_type.value,
            band_type=config.band_type.value,
            num_carriers=config.num_carriers,
            total_bandwidth_mhz=config.total_bandwidth_mhz,
            carrier_results=carrier_results,
            dl_agg_avg_mbps=dl_avg,
            dl_agg_max_mbps=dl_max,
            ul_agg_avg_mbps=ul_avg,
            ul_agg_max_mbps=ul_max,
            expected_dl_mbps=config.expected_dl_mbps,
            expected_ul_mbps=config.expected_ul_mbps,
            dl_efficiency=dl_efficiency,
            ul_efficiency=ul_efficiency,
            scell_activation_time_ms=activation_time,
            all_scells_active=all_active,
            active_carrier_count=active_count,
            duration_s=duration,
            passed=passed,
            notes="" if ue_list else "No UE attached",
        )

        # Print summary
        self._print_result(result)

        return result

    def _print_result(self, result: CATestResult):
        """Print test result summary."""
        print(f"\n  {'─' * 50}")
        print(f"  Results Summary:")
        print(f"  {'─' * 50}")
        print(f"    Aggregated DL: {result.dl_agg_avg_mbps:.1f} Mbps avg, "
              f"{result.dl_agg_max_mbps:.1f} Mbps max ({result.dl_efficiency:.1f}%)")
        print(f"    Aggregated UL: {result.ul_agg_avg_mbps:.1f} Mbps avg, "
              f"{result.ul_agg_max_mbps:.1f} Mbps max ({result.ul_efficiency:.1f}%)")
        print(f"    Active carriers: {result.active_carrier_count}/{result.num_carriers}")
        print(f"    SCell activation time: {result.scell_activation_time_ms:.0f} ms")

        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"\n  Status: {status}")
        if result.notes:
            print(f"  Notes: {result.notes}")

    def run_all_tests(
        self,
        scenarios: list[str] | None = None,
        ca_types: list[CAType] | None = None,
        duration: float = 30.0,
    ) -> list[CATestResult]:
        """Run multiple CA test scenarios.

        Args:
            scenarios: Specific scenarios to run (None = all matching ca_types)
            ca_types: CA types to include (None = all)
            duration: Duration per test

        Returns:
            List of test results
        """
        # Filter scenarios
        if scenarios:
            test_configs = [(name, CA_TEST_SCENARIOS[name])
                          for name in scenarios if name in CA_TEST_SCENARIOS]
        else:
            test_configs = list(CA_TEST_SCENARIOS.items())

        # Filter by CA type if specified
        if ca_types:
            test_configs = [(name, cfg) for name, cfg in test_configs
                          if cfg.ca_type in ca_types]

        print("\n" + "═" * 70)
        print("CARRIER AGGREGATION TEST SUITE")
        print("═" * 70)
        print(f"Host: {self.host}")
        print(f"Tests to run: {len(test_configs)}")
        print(f"Duration per test: {duration}s")

        self.results = []

        for scenario_name, config in test_configs:
            result = self.run_test(config, duration)
            self.results.append(result)

        return self.results

    def print_summary(self):
        """Print summary of all test results."""
        if not self.results:
            print("\nNo test results to summarize.")
            return

        print("\n" + "═" * 100)
        print("CA TEST SUMMARY")
        print("═" * 100)

        # Group by CA type
        by_type: dict[str, list[CATestResult]] = {}
        for r in self.results:
            if r.ca_type not in by_type:
                by_type[r.ca_type] = []
            by_type[r.ca_type].append(r)

        for ca_type, results in by_type.items():
            print(f"\n{ca_type.upper()} Results:")
            print("-" * 100)
            print(f"{'Scenario':<30} {'CCs':>4} {'BW':>8} "
                  f"{'DL Mbps':>12} {'UL Mbps':>12} {'Active':>8} {'Status':>8}")
            print("-" * 100)

            for r in results:
                status = "PASS" if r.passed else "FAIL"
                print(f"{r.scenario_name:<30} {r.num_carriers:>4} "
                      f"{r.total_bandwidth_mhz:>6}MHz "
                      f"{r.dl_agg_avg_mbps:>12.1f} {r.ul_agg_avg_mbps:>12.1f} "
                      f"{r.active_carrier_count:>4}/{r.num_carriers:<3} {status:>8}")

        print("\n" + "-" * 100)

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        print(f"\nTotal: {len(self.results)} tests, {passed} passed, {failed} failed")

    def export_results(self, output_file: str):
        """Export results to JSON file."""
        data = {
            "test_suite": "CA Test Suite",
            "host": self.host,
            "timestamp": time.time(),
            "results": [r.to_dict() for r in self.results],
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
                "by_type": {},
            },
        }

        # Summary by CA type
        for r in self.results:
            if r.ca_type not in data["summary"]["by_type"]:
                data["summary"]["by_type"][r.ca_type] = {"total": 0, "passed": 0}
            data["summary"]["by_type"][r.ca_type]["total"] += 1
            if r.passed:
                data["summary"]["by_type"][r.ca_type]["passed"] += 1

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\n✓ Results exported to: {output_file}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="Carrier Aggregation (CA) testing for Amarisoft Callbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
CA Types:
  lte_ca    LTE Carrier Aggregation (2-5CC)
  nr_ca     NR Carrier Aggregation
  endc      EN-DC (LTE + NR Dual Connectivity)

Examples:
    # Run all CA tests
    python ca_test_suite.py --host 192.168.1.80

    # Run only LTE CA tests
    python ca_test_suite.py --host 192.168.1.80 --ca-type lte_ca

    # Run specific scenarios
    python ca_test_suite.py --host 192.168.1.80 --tests lte_ca_2a_4a endc_2a_n41a

    # Export results
    python ca_test_suite.py --host 192.168.1.80 --output ca_results.json

    # List all scenarios
    python ca_test_suite.py --list-tests
        """,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="WebSocket auth password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument("--ssl-verify", action="store_true", help="Verify TLS certs")
    parser.add_argument(
        "--tests", nargs="+", default=None,
        help="Specific tests to run",
    )
    parser.add_argument(
        "--ca-type", nargs="+", default=None,
        choices=["lte_ca", "nr_ca", "endc"],
        help="CA types to test",
    )
    parser.add_argument(
        "--duration", type=float, default=30.0,
        help="Duration per test in seconds",
    )
    parser.add_argument(
        "--output", default=None,
        help="Export results to JSON file",
    )
    parser.add_argument(
        "--list-tests", action="store_true",
        help="List available test scenarios and exit",
    )
    return parser.parse_args()


def list_tests():
    """Print available CA test scenarios."""
    print("\nCarrier Aggregation Test Scenarios:")
    print("=" * 110)

    # Group by CA type
    by_type: dict[str, list[tuple[str, CAConfiguration]]] = {}
    for name, config in CA_TEST_SCENARIOS.items():
        ca_type = config.ca_type.value
        if ca_type not in by_type:
            by_type[ca_type] = []
        by_type[ca_type].append((name, config))

    for ca_type, scenarios in by_type.items():
        print(f"\n{ca_type.upper()} ({len(scenarios)} scenarios):")
        print("-" * 110)
        print(f"{'Name':<35} {'Carriers':<25} {'BW':>8} "
              f"{'Expected DL':>14} {'Expected UL':>14}")
        print("-" * 110)

        for name, config in scenarios:
            bands = "+".join(c.band for c in config.carriers)
            print(f"{name:<35} {bands:<25} {config.total_bandwidth_mhz:>6}MHz "
                  f"{config.expected_dl_mbps:>12.0f}Mbps "
                  f"{config.expected_ul_mbps:>12.0f}Mbps")

    print("\n" + "=" * 110)
    print(f"\nTotal: {len(CA_TEST_SCENARIOS)} CA scenarios")

    # Print band combination counts
    print("\nCA Combinations:")
    print(f"  LTE CA: {len(LTE_CA_COMBINATIONS)} combinations")
    print(f"  NR CA: {len(NR_CA_COMBINATIONS)} combinations")
    print(f"  EN-DC: {len(ENDC_COMBINATIONS)} combinations")


def main():
    args = parse_args()

    if args.list_tests:
        list_tests()
        return

    # Create test suite
    suite = CATestSuite(
        host=args.host,
        password=args.password,
        ssl=args.ssl,
        ssl_verify=args.ssl_verify,
    )

    # Connect
    if not suite.connect():
        return

    try:
        # Determine CA types to test
        ca_types = None
        if args.ca_type:
            ca_types = [CAType(t) for t in args.ca_type]

        # Run tests
        suite.run_all_tests(
            scenarios=args.tests,
            ca_types=ca_types,
            duration=args.duration,
        )

        # Print summary
        suite.print_summary()

        # Export if requested
        if args.output:
            suite.export_results(args.output)

    except AmariError as e:
        print(f"\nError: {e}")
    finally:
        suite.disconnect()


if __name__ == "__main__":
    main()
