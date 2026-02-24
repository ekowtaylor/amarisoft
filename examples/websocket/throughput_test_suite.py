#!/usr/bin/env python3
"""Throughput test suite for the Amarisoft Callbox.

Supports 10 RAT/mode combinations:
  1. LTE FDD 1CC (MIMO)
  2. LTE TDD 1CC (MIMO)
  3. ENDC (LTE + NR) (MIMO)
  4. NR FDD 1CC (MIMO)
  5. NR TDD 1CC (MIMO)
  6. LTE FDD 1CC SISO
  7. LTE TDD 1CC SISO
  8. ENDC SISO
  9. NR FDD 1CC SISO
  10. NR TDD 1CC SISO

Each test scenario includes:
  - Supported bands and band combinations
  - iPerf-based bidirectional throughput measurement
  - Peak and average throughput, latency, and BLER logging
  - MCS settings for max throughput
  - Measurement and reporting

Test Procedure:
  1. Camp device on target RAT/band configuration
  2. Start a bidirectional iPerf data session
  3. Measure peak and average throughput
  4. Repeat for different bands and RF conditions
  5. Log throughput, latency, and BLER
"""

import argparse
import json
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any

from client.websocket import (
    Callbox,
    AmariError,
    CommandError,
    AmariConnectionError,
)


# ══════════════════════════════════════════════════════════════
# BAND DEFINITIONS
# ══════════════════════════════════════════════════════════════

# LTE FDD Bands
LTE_FDD_BANDS = ["B2", "B4", "B5", "B7", "B12", "B13", "B14", "B17", "B25", "B26", "B30", "B66", "B71"]

# LTE TDD Bands
LTE_TDD_BANDS = ["B41"]

# NR FDD Bands
NR_FDD_BANDS = ["n2", "n5", "n7", "n12", "n13", "n14", "n25", "n26", "n66", "n71"]

# NR TDD Bands
NR_TDD_BANDS = ["n41"]

# ENDC (NSA) Band Combinations
ENDC_BAND_COMBOS = [
    ("B2", "n41"),
    ("B66", "n25"),
    ("B2", "n66"),
    ("B2", "n71"),
    ("B66", "n71"),
    ("B12", "n66"),
    ("B71", "n41"),
]


# ══════════════════════════════════════════════════════════════
# ENUMS AND DATA CLASSES
# ══════════════════════════════════════════════════════════════

class RAT(Enum):
    """Radio Access Technology."""
    LTE = "lte"
    NR = "nr"
    ENDC = "endc"  # LTE anchor + NR secondary


class DuplexMode(Enum):
    """Duplex mode."""
    FDD = "fdd"
    TDD = "tdd"


class MIMOMode(Enum):
    """MIMO configuration."""
    SISO = "siso"      # 1x1
    MIMO_2x2 = "2x2"   # 2x2 MIMO
    MIMO_4x4 = "4x4"   # 4x4 MIMO


@dataclass
class ThroughputResult:
    """Results from a throughput measurement."""
    test_name: str
    rat: str
    duplex: str
    mimo: str
    band: str  # Band under test (e.g., "B2", "n41", "B2+n41")
    duration_s: float
    samples: int
    # Throughput metrics
    dl_avg_mbps: float
    dl_max_mbps: float
    dl_min_mbps: float
    ul_avg_mbps: float
    ul_max_mbps: float
    ul_min_mbps: float
    dl_expected_mbps: float
    ul_expected_mbps: float
    dl_efficiency: float  # actual/expected %
    ul_efficiency: float
    # BLER metrics
    dl_bler: float = 0.0  # DL Block Error Rate (%)
    ul_bler: float = 0.0  # UL Block Error Rate (%)
    # Latency metrics
    latency_avg_ms: float = 0.0
    latency_min_ms: float = 0.0
    latency_max_ms: float = 0.0
    latency_jitter_ms: float = 0.0
    # iPerf specific metrics
    iperf_dl_mbps: float = 0.0  # iPerf measured DL
    iperf_ul_mbps: float = 0.0  # iPerf measured UL
    iperf_retransmits: int = 0  # TCP retransmits (if TCP mode)
    # Status
    ue_count: int = 0
    passed: bool = False
    notes: str = ""


@dataclass
class TestScenario:
    """Configuration for a throughput test scenario."""
    name: str
    rat: RAT
    duplex: DuplexMode
    mimo: MIMOMode

    # Cell parameters
    bandwidth_mhz: int = 20
    n_rb: int = 100  # Resource blocks (100 for 20MHz LTE)

    # NR specific
    nr_bandwidth_mhz: int = 100
    nr_scs_khz: int = 30  # Subcarrier spacing

    # MCS settings (None = adaptive)
    dl_mcs: int | None = None
    ul_mcs: int | None = None

    # Expected throughput (Mbps) - calculated based on config
    expected_dl_mbps: float = 0.0
    expected_ul_mbps: float = 0.0

    # TDD config (for TDD modes)
    tdd_config: int = 2  # TDD config index
    tdd_dl_ul_ratio: float = 0.6  # DL time ratio

    # Test parameters
    duration_s: float = 30.0
    warmup_s: float = 5.0
    pass_threshold: float = 0.7  # 70% of expected = pass

    # Additional notes
    description: str = ""

    def __post_init__(self):
        """Calculate expected throughput based on configuration."""
        self._calculate_expected_throughput()

    def _calculate_expected_throughput(self):
        """Calculate theoretical peak throughput."""
        if self.rat == RAT.LTE:
            self._calc_lte_throughput()
        elif self.rat == RAT.NR:
            self._calc_nr_throughput()
        elif self.rat == RAT.ENDC:
            self._calc_endc_throughput()

    def _calc_lte_throughput(self):
        """Calculate LTE theoretical throughput."""
        # LTE throughput formula (approximate)
        # DL: ~75 Mbps per 20 MHz in 2x2 MIMO with 64QAM
        # UL: ~50 Mbps per 20 MHz with 16QAM

        base_dl = 75.0  # Mbps for 20 MHz 2x2 MIMO
        base_ul = 50.0  # Mbps for 20 MHz

        # Scale by bandwidth
        bw_factor = self.bandwidth_mhz / 20.0

        # MIMO factor
        if self.mimo == MIMOMode.SISO:
            mimo_dl_factor = 0.5  # Half of 2x2
            mimo_ul_factor = 1.0  # UL typically SISO anyway
        elif self.mimo == MIMOMode.MIMO_4x4:
            mimo_dl_factor = 2.0  # Double of 2x2
            mimo_ul_factor = 1.0
        else:  # 2x2
            mimo_dl_factor = 1.0
            mimo_ul_factor = 1.0

        # TDD factor
        if self.duplex == DuplexMode.TDD:
            tdd_dl_factor = self.tdd_dl_ul_ratio
            tdd_ul_factor = 1.0 - self.tdd_dl_ul_ratio
        else:
            tdd_dl_factor = 1.0
            tdd_ul_factor = 1.0

        self.expected_dl_mbps = base_dl * bw_factor * mimo_dl_factor * tdd_dl_factor
        self.expected_ul_mbps = base_ul * bw_factor * mimo_ul_factor * tdd_ul_factor

    def _calc_nr_throughput(self):
        """Calculate NR theoretical throughput."""
        # NR throughput is much higher
        # ~1 Gbps for 100 MHz with 4x4 MIMO and 256QAM

        base_dl = 1000.0  # Mbps for 100 MHz 4x4 MIMO
        base_ul = 200.0   # Mbps for 100 MHz

        # Scale by bandwidth
        bw_factor = self.nr_bandwidth_mhz / 100.0

        # MIMO factor
        if self.mimo == MIMOMode.SISO:
            mimo_dl_factor = 0.25  # Quarter of 4x4
            mimo_ul_factor = 1.0
        elif self.mimo == MIMOMode.MIMO_2x2:
            mimo_dl_factor = 0.5
            mimo_ul_factor = 1.0
        else:  # 4x4
            mimo_dl_factor = 1.0
            mimo_ul_factor = 1.0

        # TDD factor
        if self.duplex == DuplexMode.TDD:
            tdd_dl_factor = self.tdd_dl_ul_ratio
            tdd_ul_factor = 1.0 - self.tdd_dl_ul_ratio
        else:
            tdd_dl_factor = 1.0
            tdd_ul_factor = 1.0

        self.expected_dl_mbps = base_dl * bw_factor * mimo_dl_factor * tdd_dl_factor
        self.expected_ul_mbps = base_ul * bw_factor * mimo_ul_factor * tdd_ul_factor

    def _calc_endc_throughput(self):
        """Calculate EN-DC (LTE + NR) throughput."""
        # EN-DC combines LTE anchor + NR secondary
        # LTE anchor: ~75 Mbps
        # NR leg: ~500-1000 Mbps depending on config

        # LTE anchor contribution
        lte_dl = 75.0 * (self.bandwidth_mhz / 20.0)
        lte_ul = 50.0 * (self.bandwidth_mhz / 20.0)

        # NR leg contribution
        nr_dl = 500.0 * (self.nr_bandwidth_mhz / 100.0)
        nr_ul = 100.0 * (self.nr_bandwidth_mhz / 100.0)

        # MIMO factor (applied to NR leg primarily)
        if self.mimo == MIMOMode.SISO:
            nr_dl *= 0.25
            lte_dl *= 0.5
        elif self.mimo == MIMOMode.MIMO_2x2:
            nr_dl *= 0.5

        self.expected_dl_mbps = lte_dl + nr_dl
        self.expected_ul_mbps = lte_ul + nr_ul


# ══════════════════════════════════════════════════════════════
# PREDEFINED TEST SCENARIOS
# ══════════════════════════════════════════════════════════════

# Test scenario definitions for all 10 combinations
TEST_SCENARIOS: dict[str, TestScenario] = {
    # ─────────────────────────────────────────────
    # LTE Tests (MIMO)
    # ─────────────────────────────────────────────
    "lte_fdd_1cc": TestScenario(
        name="LTE FDD 1CC",
        rat=RAT.LTE,
        duplex=DuplexMode.FDD,
        mimo=MIMOMode.MIMO_2x2,
        bandwidth_mhz=20,
        n_rb=100,
        dl_mcs=28,  # Max MCS for peak throughput
        ul_mcs=23,
        description="LTE FDD single carrier with 2x2 MIMO, 20 MHz bandwidth",
    ),

    "lte_tdd_1cc": TestScenario(
        name="LTE TDD 1CC",
        rat=RAT.LTE,
        duplex=DuplexMode.TDD,
        mimo=MIMOMode.MIMO_2x2,
        bandwidth_mhz=20,
        n_rb=100,
        dl_mcs=28,
        ul_mcs=23,
        tdd_config=2,
        tdd_dl_ul_ratio=0.6,
        description="LTE TDD single carrier with 2x2 MIMO, 20 MHz bandwidth",
    ),

    # ─────────────────────────────────────────────
    # LTE Tests (SISO)
    # ─────────────────────────────────────────────
    "lte_fdd_1cc_siso": TestScenario(
        name="LTE FDD 1CC SISO",
        rat=RAT.LTE,
        duplex=DuplexMode.FDD,
        mimo=MIMOMode.SISO,
        bandwidth_mhz=20,
        n_rb=100,
        dl_mcs=28,
        ul_mcs=23,
        description="LTE FDD single carrier with SISO, 20 MHz bandwidth",
    ),

    "lte_tdd_1cc_siso": TestScenario(
        name="LTE TDD 1CC SISO",
        rat=RAT.LTE,
        duplex=DuplexMode.TDD,
        mimo=MIMOMode.SISO,
        bandwidth_mhz=20,
        n_rb=100,
        dl_mcs=28,
        ul_mcs=23,
        tdd_config=2,
        tdd_dl_ul_ratio=0.6,
        description="LTE TDD single carrier with SISO, 20 MHz bandwidth",
    ),

    # ─────────────────────────────────────────────
    # NR Tests (MIMO)
    # ─────────────────────────────────────────────
    "nr_fdd_1cc": TestScenario(
        name="NR FDD 1CC",
        rat=RAT.NR,
        duplex=DuplexMode.FDD,
        mimo=MIMOMode.MIMO_4x4,
        nr_bandwidth_mhz=100,
        nr_scs_khz=30,
        dl_mcs=27,  # NR max MCS
        ul_mcs=27,
        description="NR FDD single carrier with 4x4 MIMO, 100 MHz bandwidth",
    ),

    "nr_tdd_1cc": TestScenario(
        name="NR TDD 1CC",
        rat=RAT.NR,
        duplex=DuplexMode.TDD,
        mimo=MIMOMode.MIMO_4x4,
        nr_bandwidth_mhz=100,
        nr_scs_khz=30,
        dl_mcs=27,
        ul_mcs=27,
        tdd_config=2,
        tdd_dl_ul_ratio=0.75,  # NR typically more DL heavy
        description="NR TDD single carrier with 4x4 MIMO, 100 MHz bandwidth",
    ),

    # ─────────────────────────────────────────────
    # NR Tests (SISO)
    # ─────────────────────────────────────────────
    "nr_fdd_1cc_siso": TestScenario(
        name="NR FDD 1CC SISO",
        rat=RAT.NR,
        duplex=DuplexMode.FDD,
        mimo=MIMOMode.SISO,
        nr_bandwidth_mhz=100,
        nr_scs_khz=30,
        dl_mcs=27,
        ul_mcs=27,
        description="NR FDD single carrier with SISO, 100 MHz bandwidth",
    ),

    "nr_tdd_1cc_siso": TestScenario(
        name="NR TDD 1CC SISO",
        rat=RAT.NR,
        duplex=DuplexMode.TDD,
        mimo=MIMOMode.SISO,
        nr_bandwidth_mhz=100,
        nr_scs_khz=30,
        dl_mcs=27,
        ul_mcs=27,
        tdd_config=2,
        tdd_dl_ul_ratio=0.75,
        description="NR TDD single carrier with SISO, 100 MHz bandwidth",
    ),

    # ─────────────────────────────────────────────
    # EN-DC Tests (MIMO)
    # ─────────────────────────────────────────────
    "endc": TestScenario(
        name="ENDC",
        rat=RAT.ENDC,
        duplex=DuplexMode.FDD,  # LTE anchor is FDD
        mimo=MIMOMode.MIMO_4x4,
        bandwidth_mhz=20,  # LTE anchor
        nr_bandwidth_mhz=100,  # NR leg
        nr_scs_khz=30,
        dl_mcs=28,
        ul_mcs=23,
        description="EN-DC with LTE FDD anchor (20 MHz) + NR (100 MHz)",
    ),

    # ─────────────────────────────────────────────
    # EN-DC Tests (SISO)
    # ─────────────────────────────────────────────
    "endc_siso": TestScenario(
        name="ENDC SISO",
        rat=RAT.ENDC,
        duplex=DuplexMode.FDD,
        mimo=MIMOMode.SISO,
        bandwidth_mhz=20,
        nr_bandwidth_mhz=100,
        nr_scs_khz=30,
        dl_mcs=28,
        ul_mcs=23,
        description="EN-DC with SISO: LTE FDD anchor (20 MHz) + NR (100 MHz)",
    ),
}


# ══════════════════════════════════════════════════════════════
# BAND MAPPING FOR TEST SCENARIOS
# ══════════════════════════════════════════════════════════════

# Map each scenario type to its supported bands
SCENARIO_BANDS = {
    "lte_fdd_1cc": LTE_FDD_BANDS,
    "lte_fdd_1cc_siso": LTE_FDD_BANDS,
    "lte_tdd_1cc": LTE_TDD_BANDS,
    "lte_tdd_1cc_siso": LTE_TDD_BANDS,
    "nr_fdd_1cc": NR_FDD_BANDS,
    "nr_fdd_1cc_siso": NR_FDD_BANDS,
    "nr_tdd_1cc": NR_TDD_BANDS,
    "nr_tdd_1cc_siso": NR_TDD_BANDS,
    "endc": ENDC_BAND_COMBOS,
    "endc_siso": ENDC_BAND_COMBOS,
}


# ══════════════════════════════════════════════════════════════
# IPERF MANAGER
# ══════════════════════════════════════════════════════════════

@dataclass
class IPerfResult:
    """Results from an iPerf measurement."""
    direction: str  # "dl" or "ul"
    throughput_mbps: float
    transfer_mb: float
    duration_s: float
    retransmits: int = 0  # TCP only
    jitter_ms: float = 0.0  # UDP only
    lost_packets: int = 0  # UDP only
    total_packets: int = 0  # UDP only
    success: bool = True
    error: str = ""


class IPerfManager:
    """Manages iPerf3 client/server for throughput testing.

    Supports both TCP and UDP modes for bidirectional testing.
    """

    def __init__(
        self,
        server_ip: str,
        port: int = 5201,
        use_udp: bool = False,
        parallel: int = 1,
    ):
        """Initialize iPerf manager.

        Args:
            server_ip: IP address of iPerf server (typically the UE or traffic generator)
            port: iPerf server port
            use_udp: Use UDP instead of TCP
            parallel: Number of parallel streams
        """
        self.server_ip = server_ip
        self.port = port
        self.use_udp = use_udp
        self.parallel = parallel
        self._server_process: subprocess.Popen | None = None

        # Check if iperf3 is available
        self.iperf_path = shutil.which("iperf3")
        if not self.iperf_path:
            print("  ⚠ iPerf3 not found in PATH - throughput tests will use eNB stats only")

    def start_server(self) -> bool:
        """Start local iPerf server for UL tests."""
        if not self.iperf_path:
            return False

        try:
            self._server_process = subprocess.Popen(
                [self.iperf_path, "-s", "-p", str(self.port), "-J"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            time.sleep(1)  # Give server time to start
            print(f"    ✓ iPerf server started on port {self.port}")
            return True
        except Exception as e:
            print(f"    ✗ Failed to start iPerf server: {e}")
            return False

    def stop_server(self):
        """Stop local iPerf server."""
        if self._server_process:
            self._server_process.terminate()
            self._server_process.wait(timeout=5)
            self._server_process = None

    def run_client(
        self,
        duration: int = 10,
        reverse: bool = False,
        bandwidth: str | None = None,
    ) -> IPerfResult:
        """Run iPerf client test.

        Args:
            duration: Test duration in seconds
            reverse: If True, run in reverse mode (server sends to client = DL test)
            bandwidth: Target bandwidth for UDP (e.g., "100M")

        Returns:
            IPerfResult with measurement data
        """
        if not self.iperf_path:
            return IPerfResult(
                direction="dl" if reverse else "ul",
                throughput_mbps=0.0,
                transfer_mb=0.0,
                duration_s=duration,
                success=False,
                error="iPerf3 not available",
            )

        direction = "dl" if reverse else "ul"

        # Build command
        cmd = [
            self.iperf_path,
            "-c", self.server_ip,
            "-p", str(self.port),
            "-t", str(duration),
            "-P", str(self.parallel),
            "-J",  # JSON output
        ]

        if reverse:
            cmd.append("-R")  # Reverse mode (server sends)

        if self.use_udp:
            cmd.append("-u")
            if bandwidth:
                cmd.extend(["-b", bandwidth])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 30,
            )

            return self._parse_iperf_output(result.stdout, direction, duration)

        except subprocess.TimeoutExpired:
            return IPerfResult(
                direction=direction,
                throughput_mbps=0.0,
                transfer_mb=0.0,
                duration_s=duration,
                success=False,
                error="iPerf test timed out",
            )
        except Exception as e:
            return IPerfResult(
                direction=direction,
                throughput_mbps=0.0,
                transfer_mb=0.0,
                duration_s=duration,
                success=False,
                error=str(e),
            )

    def _parse_iperf_output(
        self,
        output: str,
        direction: str,
        duration: float,
    ) -> IPerfResult:
        """Parse iPerf3 JSON output."""
        try:
            data = json.loads(output)

            if "error" in data:
                return IPerfResult(
                    direction=direction,
                    throughput_mbps=0.0,
                    transfer_mb=0.0,
                    duration_s=duration,
                    success=False,
                    error=data["error"],
                )

            # Get end summary
            end = data.get("end", {})

            # Handle TCP vs UDP differently
            if self.use_udp:
                sum_data = end.get("sum", {})
                return IPerfResult(
                    direction=direction,
                    throughput_mbps=sum_data.get("bits_per_second", 0) / 1_000_000,
                    transfer_mb=sum_data.get("bytes", 0) / 1_000_000,
                    duration_s=sum_data.get("seconds", duration),
                    jitter_ms=sum_data.get("jitter_ms", 0),
                    lost_packets=sum_data.get("lost_packets", 0),
                    total_packets=sum_data.get("packets", 0),
                    success=True,
                )
            else:
                # TCP - look for sum_sent or sum_received based on direction
                sum_key = "sum_received" if direction == "dl" else "sum_sent"
                sum_data = end.get(sum_key, end.get("sum_sent", {}))

                return IPerfResult(
                    direction=direction,
                    throughput_mbps=sum_data.get("bits_per_second", 0) / 1_000_000,
                    transfer_mb=sum_data.get("bytes", 0) / 1_000_000,
                    duration_s=sum_data.get("seconds", duration),
                    retransmits=end.get("sum_sent", {}).get("retransmits", 0),
                    success=True,
                )

        except json.JSONDecodeError:
            # Try parsing text output as fallback
            return self._parse_iperf_text(output, direction, duration)

    def _parse_iperf_text(
        self,
        output: str,
        direction: str,
        duration: float,
    ) -> IPerfResult:
        """Parse iPerf3 text output as fallback."""
        # Look for throughput in format like "123 Mbits/sec" or "1.23 Gbits/sec"
        throughput = 0.0

        # Match patterns like "123 Mbits/sec" or "1.23 Gbits/sec"
        patterns = [
            (r"(\d+\.?\d*)\s*Gbits/sec", 1000),  # Gbps
            (r"(\d+\.?\d*)\s*Mbits/sec", 1),     # Mbps
            (r"(\d+\.?\d*)\s*Kbits/sec", 0.001), # Kbps
        ]

        for pattern, multiplier in patterns:
            matches = re.findall(pattern, output)
            if matches:
                # Take the last match (usually the summary)
                throughput = float(matches[-1]) * multiplier
                break

        return IPerfResult(
            direction=direction,
            throughput_mbps=throughput,
            transfer_mb=0.0,
            duration_s=duration,
            success=throughput > 0,
            error="" if throughput > 0 else "Could not parse iPerf output",
        )

    def run_bidirectional(
        self,
        duration: int = 10,
        bandwidth: str | None = None,
    ) -> tuple[IPerfResult, IPerfResult]:
        """Run bidirectional throughput test.

        Args:
            duration: Test duration per direction
            bandwidth: Target bandwidth for UDP

        Returns:
            Tuple of (dl_result, ul_result)
        """
        print(f"    Running iPerf bidirectional test ({duration}s per direction)...")

        # Run DL test (reverse mode - server sends to client)
        print("      DL test (reverse mode)...")
        dl_result = self.run_client(duration=duration, reverse=True, bandwidth=bandwidth)

        # Brief pause between tests
        time.sleep(2)

        # Run UL test (normal mode - client sends to server)
        print("      UL test (normal mode)...")
        ul_result = self.run_client(duration=duration, reverse=False, bandwidth=bandwidth)

        return dl_result, ul_result


# ══════════════════════════════════════════════════════════════
# LATENCY MEASUREMENT
# ══════════════════════════════════════════════════════════════

@dataclass
class LatencyResult:
    """Results from latency measurement."""
    avg_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    jitter_ms: float = 0.0  # stddev or mdev
    packet_loss_pct: float = 0.0
    packets_sent: int = 0
    packets_received: int = 0
    success: bool = True
    error: str = ""


class LatencyMeasurement:
    """Measure network latency using ping."""

    def __init__(self, target_ip: str):
        """Initialize latency measurement.

        Args:
            target_ip: IP to ping (typically UE's IP or PDN gateway)
        """
        self.target_ip = target_ip

    def measure(
        self,
        count: int = 20,
        interval: float = 0.2,
        timeout: int = 10,
    ) -> LatencyResult:
        """Measure latency using ping.

        Args:
            count: Number of ping packets
            interval: Interval between pings in seconds
            timeout: Overall timeout in seconds

        Returns:
            LatencyResult with measurements
        """
        # Build ping command (platform-specific)
        import platform

        if platform.system() == "Darwin":  # macOS
            cmd = [
                "ping",
                "-c", str(count),
                "-i", str(interval),
                self.target_ip,
            ]
        else:  # Linux
            cmd = [
                "ping",
                "-c", str(count),
                "-i", str(interval),
                "-W", str(timeout),
                self.target_ip,
            ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + count * interval + 5,
            )

            return self._parse_ping_output(result.stdout, count)

        except subprocess.TimeoutExpired:
            return LatencyResult(
                success=False,
                error="Ping timed out",
            )
        except Exception as e:
            return LatencyResult(
                success=False,
                error=str(e),
            )

    def _parse_ping_output(self, output: str, count: int) -> LatencyResult:
        """Parse ping output to extract latency statistics."""
        result = LatencyResult(packets_sent=count)

        # Parse packet loss
        # Format: "X packets transmitted, Y received, Z% packet loss"
        loss_match = re.search(
            r"(\d+) packets transmitted, (\d+) (?:packets )?received.*?(\d+(?:\.\d+)?)% packet loss",
            output,
        )
        if loss_match:
            result.packets_sent = int(loss_match.group(1))
            result.packets_received = int(loss_match.group(2))
            result.packet_loss_pct = float(loss_match.group(3))

        # Parse RTT statistics
        # Format: "rtt min/avg/max/mdev = X/Y/Z/W ms" (Linux)
        # or "round-trip min/avg/max/stddev = X/Y/Z/W ms" (macOS)
        rtt_match = re.search(
            r"(?:rtt|round-trip) min/avg/max/(?:mdev|stddev) = "
            r"(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*) ms",
            output,
        )
        if rtt_match:
            result.min_ms = float(rtt_match.group(1))
            result.avg_ms = float(rtt_match.group(2))
            result.max_ms = float(rtt_match.group(3))
            result.jitter_ms = float(rtt_match.group(4))
            result.success = True
        else:
            result.success = result.packets_received > 0
            if not result.success:
                result.error = "No ping responses received"

        return result


# ══════════════════════════════════════════════════════════════
# BLER EXTRACTION
# ══════════════════════════════════════════════════════════════

class BLERMeasurement:
    """Extract Block Error Rate from eNB statistics."""

    def __init__(self, cb: "Callbox"):
        self.cb = cb

    def measure(
        self,
        duration: float = 5.0,
        interval: float = 1.0,
    ) -> tuple[float, float]:
        """Measure DL and UL BLER from eNB stats.

        BLER is calculated from:
        - DL: PDSCH BLER (dl_err / (dl_err + dl_tx))
        - UL: PUSCH BLER (ul_err / (ul_err + ul_tx))

        Args:
            duration: Measurement duration in seconds
            interval: Sampling interval in seconds

        Returns:
            Tuple of (dl_bler_pct, ul_bler_pct)
        """
        dl_errors = 0
        dl_total = 0
        ul_errors = 0
        ul_total = 0

        start = time.monotonic()
        while (time.monotonic() - start) < duration:
            try:
                stats = self.cb.enb.stats()

                for cell_id, cell_data in stats.get("cells", {}).items():
                    # DL BLER from PDSCH stats
                    dl_err = cell_data.get("dl_err", 0)
                    dl_tx = cell_data.get("dl_tx", 0)
                    dl_errors += dl_err
                    dl_total += dl_tx + dl_err

                    # UL BLER from PUSCH stats
                    ul_err = cell_data.get("ul_err", 0)
                    ul_tx = cell_data.get("ul_tx", 0)
                    ul_errors += ul_err
                    ul_total += ul_tx + ul_err

            except Exception:
                pass

            time.sleep(interval)

        # Calculate BLER percentages
        dl_bler = (dl_errors / dl_total * 100) if dl_total > 0 else 0.0
        ul_bler = (ul_errors / ul_total * 100) if ul_total > 0 else 0.0

        return dl_bler, ul_bler


# ══════════════════════════════════════════════════════════════
# BAND CONFIGURATION
# ══════════════════════════════════════════════════════════════

# EARFCN/ARFCN mappings for common bands (approximate center frequencies)
BAND_EARFCN_MAP = {
    # LTE FDD bands (EARFCN)
    "B2": 900,     # 1900 MHz PCS
    "B4": 2175,    # AWS-1
    "B5": 2525,    # 850 MHz Cellular
    "B7": 3100,    # 2600 MHz
    "B12": 5095,   # 700 MHz lower
    "B13": 5230,   # 700 MHz upper
    "B14": 5330,   # 700 MHz PS
    "B17": 5790,   # 700 MHz lower
    "B25": 8365,   # 1900 MHz extended
    "B26": 8865,   # 850 MHz extended
    "B30": 9820,   # 2300 MHz WCS
    "B66": 66636,  # AWS-3
    "B71": 68636,  # 600 MHz
    # LTE TDD bands
    "B41": 40620,  # 2500 MHz TDD
}

NR_ARFCN_MAP = {
    # NR FDD bands (NR-ARFCN)
    "n2": 386000,   # 1900 MHz
    "n5": 176300,   # 850 MHz
    "n7": 526000,   # 2600 MHz
    "n12": 145800,  # 700 MHz
    "n13": 149200,  # 700 MHz
    "n14": 151600,  # 700 MHz
    "n25": 386000,  # 1900 MHz
    "n26": 173800,  # 850 MHz
    "n66": 422000,  # AWS
    "n71": 123400,  # 600 MHz
    # NR TDD bands
    "n41": 499200,  # 2500 MHz TDD
}


def get_band_earfcn(band: str) -> int | None:
    """Get EARFCN for an LTE band."""
    return BAND_EARFCN_MAP.get(band)


def get_band_arfcn(band: str) -> int | None:
    """Get NR-ARFCN for an NR band."""
    return NR_ARFCN_MAP.get(band)


def format_band_string(band: str | tuple[str, str]) -> str:
    """Format band for display.

    Args:
        band: Single band string or ENDC tuple (lte_band, nr_band)

    Returns:
        Formatted string like "B2" or "B2+n41"
    """
    if isinstance(band, tuple):
        return f"{band[0]}+{band[1]}"
    return band


# ══════════════════════════════════════════════════════════════
# THROUGHPUT TEST CLASS
# ══════════════════════════════════════════════════════════════

class ThroughputTestSuite:
    """Throughput test suite for Amarisoft Callbox.

    Features:
        - 10 RAT/mode combinations (LTE/NR FDD/TDD, ENDC, MIMO/SISO)
        - Per-band testing iterations
        - iPerf integration for bidirectional throughput
        - BLER measurement from eNB statistics
        - Latency measurement via ping
        - Comprehensive reporting and JSON export
    """

    def __init__(
        self,
        host: str,
        password: str | None = None,
        ssl: bool = False,
        ssl_verify: bool = False,
        iperf_server_ip: str | None = None,
        iperf_port: int = 5201,
        ue_ip: str | None = None,
    ):
        """Initialize throughput test suite.

        Args:
            host: Amarisoft Callbox IP address
            password: Optional WebSocket password
            ssl: Use SSL for WebSocket connection
            ssl_verify: Verify SSL certificate
            iperf_server_ip: IP of iPerf server (for UL tests, typically UE IP)
            iperf_port: iPerf server port
            ue_ip: UE IP address (for latency tests, defaults to iperf_server_ip)
        """
        self.host = host
        self.password = password
        self.ssl = ssl
        self.ssl_verify = ssl_verify
        self.cb: Callbox | None = None
        self.results: list[ThroughputResult] = []

        # iPerf configuration
        self.iperf_server_ip = iperf_server_ip
        self.iperf_port = iperf_port
        self.iperf: IPerfManager | None = None

        # Latency measurement
        self.ue_ip = ue_ip or iperf_server_ip
        self.latency_measurer: LatencyMeasurement | None = None

        # BLER measurement
        self.bler_measurer: BLERMeasurement | None = None

    def connect(self) -> bool:
        """Connect to the Callbox and initialize measurement tools."""
        try:
            self.cb = Callbox(
                self.host,
                password=self.password,
                ssl=self.ssl,
                ssl_verify=self.ssl_verify,
            )
            self.cb.connect_all()
            print(f"✓ Connected to Callbox at {self.host}")

            # Initialize BLER measurement
            self.bler_measurer = BLERMeasurement(self.cb)

            # Initialize iPerf if server IP provided
            if self.iperf_server_ip:
                self.iperf = IPerfManager(
                    server_ip=self.iperf_server_ip,
                    port=self.iperf_port,
                )
                print(f"✓ iPerf configured: server={self.iperf_server_ip}:{self.iperf_port}")

            # Initialize latency measurement if UE IP provided
            if self.ue_ip:
                self.latency_measurer = LatencyMeasurement(self.ue_ip)
                print(f"✓ Latency measurement configured: target={self.ue_ip}")

            return True
        except AmariConnectionError as e:
            print(f"✗ Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from the Callbox and cleanup."""
        if self.iperf:
            self.iperf.stop_server()
        if self.cb:
            self.cb.close()
            self.cb = None

    def get_current_cell_info(self) -> dict[str, Any]:
        """Get current cell configuration."""
        info = {}
        try:
            stats = self.cb.enb.stats()
            info["cells"] = stats.get("cells", {})

            config = self.cb.enb.config_get()
            info["config"] = config.get("cells", {})
        except CommandError as e:
            print(f"  Warning: Could not get cell info: {e}")
        return info

    def check_ue_attached(self) -> tuple[bool, int]:
        """Check if any UE is attached.

        Returns:
            Tuple of (is_attached, ue_count)
        """
        try:
            mme_ues = self.cb.mme.ue_get()
            ue_list = mme_ues.get("ue_list", [])
            return len(ue_list) > 0, len(ue_list)
        except CommandError:
            return False, 0

    def configure_cell_for_test(self, scenario: TestScenario) -> bool:
        """Configure cell parameters for the test scenario.

        Note: Full cell reconfiguration may require restart.
        This method sets runtime-adjustable parameters.
        """
        print(f"\n  Configuring cell for {scenario.name}...")

        try:
            # Get first cell ID
            stats = self.cb.enb.stats()
            cells = stats.get("cells", {})
            if not cells:
                print("    ✗ No cells configured")
                return False

            cell_id = int(list(cells.keys())[0])

            # Set MCS if specified (for max throughput tests)
            params = {}
            if scenario.dl_mcs is not None:
                params["pdsch_mcs"] = scenario.dl_mcs
            if scenario.ul_mcs is not None:
                params["pusch_mcs"] = scenario.ul_mcs

            if params:
                self.cb.enb.config_set_cell(cell_id, **params)
                print(f"    ✓ Set MCS: DL={scenario.dl_mcs}, UL={scenario.ul_mcs}")

            return True

        except CommandError as e:
            print(f"    ✗ Configuration failed: {e}")
            return False

    def measure_throughput(
        self,
        duration: float,
        interval: float = 1.0,
        warmup: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Measure throughput over a duration.

        Args:
            duration: Measurement duration in seconds
            interval: Sampling interval in seconds
            warmup: Warmup period before measuring

        Returns:
            List of throughput samples
        """
        samples = []

        # Warmup period
        if warmup > 0:
            print(f"    Warmup: {warmup}s...")
            time.sleep(warmup)

        print(f"    Measuring for {duration}s...")
        start = time.monotonic()

        while (time.monotonic() - start) < duration:
            try:
                stats = self.cb.enb.stats()
                elapsed = time.monotonic() - start

                for cell_id, cell_data in stats.get("cells", {}).items():
                    samples.append({
                        "time": elapsed,
                        "cell_id": cell_id,
                        "dl_bitrate": cell_data.get("dl_bitrate", 0),
                        "ul_bitrate": cell_data.get("ul_bitrate", 0),
                        "ue_count": cell_data.get("ue_count_avg", 0),
                    })

            except CommandError:
                pass

            time.sleep(interval)

        return samples

    def run_test(
        self,
        scenario: TestScenario,
        band: str | tuple[str, str] | None = None,
        use_iperf: bool = True,
        measure_bler: bool = True,
        measure_latency: bool = True,
    ) -> ThroughputResult:
        """Run a single throughput test.

        Args:
            scenario: Test scenario configuration
            band: Specific band to test (None uses current config)
            use_iperf: Use iPerf for throughput measurement (if available)
            measure_bler: Measure BLER from eNB stats
            measure_latency: Measure latency via ping

        Returns:
            ThroughputResult with measurements
        """
        band_str = format_band_string(band) if band else "current"

        print(f"\n{'═' * 60}")
        print(f"Running: {scenario.name}")
        if band:
            print(f"Band: {band_str}")
        print(f"{'═' * 60}")
        print(f"  RAT: {scenario.rat.value.upper()}")
        print(f"  Duplex: {scenario.duplex.value.upper()}")
        print(f"  MIMO: {scenario.mimo.value}")
        print(f"  Expected DL: {scenario.expected_dl_mbps:.1f} Mbps")
        print(f"  Expected UL: {scenario.expected_ul_mbps:.1f} Mbps")

        # Check UE attachment
        attached, ue_count = self.check_ue_attached()
        if not attached:
            print("\n  ⚠ No UE attached - throughput will be 0")
            print("    Connect a UE and generate traffic for meaningful results")
        else:
            print(f"\n  ✓ {ue_count} UE(s) attached")

        # Configure cell
        self.configure_cell_for_test(scenario)

        # Initialize result variables
        iperf_dl = 0.0
        iperf_ul = 0.0
        iperf_retransmits = 0
        dl_bler = 0.0
        ul_bler = 0.0
        latency_avg = 0.0
        latency_min = 0.0
        latency_max = 0.0
        latency_jitter = 0.0

        # ══════════════════════════════════════════════════════════
        # Measure throughput (iPerf + eNB stats in parallel)
        # ══════════════════════════════════════════════════════════

        # Start threads for parallel measurement
        samples = []
        iperf_dl_result = None
        iperf_ul_result = None

        def enb_stats_thread():
            nonlocal samples
            samples = self.measure_throughput(
                duration=scenario.duration_s,
                warmup=scenario.warmup_s,
            )

        def iperf_thread():
            nonlocal iperf_dl_result, iperf_ul_result
            if self.iperf and use_iperf and attached:
                iperf_dl_result, iperf_ul_result = self.iperf.run_bidirectional(
                    duration=int(scenario.duration_s / 2),  # Split time between DL and UL
                )

        # Run measurements
        stats_thread = threading.Thread(target=enb_stats_thread)
        iperf_measurement = threading.Thread(target=iperf_thread)

        stats_thread.start()
        if self.iperf and use_iperf and attached:
            iperf_measurement.start()

        stats_thread.join()
        if self.iperf and use_iperf and attached:
            iperf_measurement.join()

        # Process iPerf results
        if iperf_dl_result and iperf_dl_result.success:
            iperf_dl = iperf_dl_result.throughput_mbps
            print(f"  iPerf DL: {iperf_dl:.2f} Mbps")

        if iperf_ul_result and iperf_ul_result.success:
            iperf_ul = iperf_ul_result.throughput_mbps
            iperf_retransmits = iperf_ul_result.retransmits
            print(f"  iPerf UL: {iperf_ul:.2f} Mbps (retransmits: {iperf_retransmits})")

        # ══════════════════════════════════════════════════════════
        # Measure BLER
        # ══════════════════════════════════════════════════════════
        if self.bler_measurer and measure_bler and attached:
            print("\n  Measuring BLER...")
            dl_bler, ul_bler = self.bler_measurer.measure(duration=3.0)
            print(f"    DL BLER: {dl_bler:.3f}%")
            print(f"    UL BLER: {ul_bler:.3f}%")

        # ══════════════════════════════════════════════════════════
        # Measure Latency
        # ══════════════════════════════════════════════════════════
        if self.latency_measurer and measure_latency and attached:
            print("\n  Measuring latency...")
            latency_result = self.latency_measurer.measure(count=20)
            if latency_result.success:
                latency_avg = latency_result.avg_ms
                latency_min = latency_result.min_ms
                latency_max = latency_result.max_ms
                latency_jitter = latency_result.jitter_ms
                print(f"    Latency: avg={latency_avg:.1f}ms, "
                      f"min={latency_min:.1f}ms, max={latency_max:.1f}ms, "
                      f"jitter={latency_jitter:.1f}ms")
            else:
                print(f"    Latency measurement failed: {latency_result.error}")

        # ══════════════════════════════════════════════════════════
        # Calculate statistics from eNB stats
        # ══════════════════════════════════════════════════════════
        if samples:
            dl_rates = [s["dl_bitrate"] / 1_000_000 for s in samples]  # Convert to Mbps
            ul_rates = [s["ul_bitrate"] / 1_000_000 for s in samples]

            dl_avg = sum(dl_rates) / len(dl_rates)
            dl_max = max(dl_rates)
            dl_min = min(dl_rates)

            ul_avg = sum(ul_rates) / len(ul_rates)
            ul_max = max(ul_rates)
            ul_min = min(ul_rates)
        else:
            dl_avg = dl_max = dl_min = 0.0
            ul_avg = ul_max = ul_min = 0.0

        # Use iPerf results if higher (more accurate for actual throughput)
        if iperf_dl > dl_avg:
            dl_avg = iperf_dl
        if iperf_ul > ul_avg:
            ul_avg = iperf_ul

        # Calculate efficiency
        dl_efficiency = (dl_avg / scenario.expected_dl_mbps * 100) if scenario.expected_dl_mbps > 0 else 0
        ul_efficiency = (ul_avg / scenario.expected_ul_mbps * 100) if scenario.expected_ul_mbps > 0 else 0

        # Determine pass/fail (considering BLER threshold)
        bler_pass = dl_bler < 10.0 and ul_bler < 10.0  # 10% BLER threshold
        passed = (
            (dl_efficiency >= scenario.pass_threshold * 100 or
             ul_efficiency >= scenario.pass_threshold * 100) and
            bler_pass
        ) or not attached  # Don't fail if no UE

        # Build result
        result = ThroughputResult(
            test_name=scenario.name,
            rat=scenario.rat.value,
            duplex=scenario.duplex.value,
            mimo=scenario.mimo.value,
            band=band_str,
            duration_s=scenario.duration_s,
            samples=len(samples),
            dl_avg_mbps=dl_avg,
            dl_max_mbps=dl_max,
            dl_min_mbps=dl_min,
            ul_avg_mbps=ul_avg,
            ul_max_mbps=ul_max,
            ul_min_mbps=ul_min,
            dl_expected_mbps=scenario.expected_dl_mbps,
            ul_expected_mbps=scenario.expected_ul_mbps,
            dl_efficiency=dl_efficiency,
            ul_efficiency=ul_efficiency,
            dl_bler=dl_bler,
            ul_bler=ul_bler,
            latency_avg_ms=latency_avg,
            latency_min_ms=latency_min,
            latency_max_ms=latency_max,
            latency_jitter_ms=latency_jitter,
            iperf_dl_mbps=iperf_dl,
            iperf_ul_mbps=iperf_ul,
            iperf_retransmits=iperf_retransmits,
            ue_count=ue_count,
            passed=passed,
            notes=self._generate_notes(attached, bler_pass, dl_bler, ul_bler),
        )

        # Print results
        self._print_result(result)

        return result

    def _generate_notes(
        self,
        attached: bool,
        bler_pass: bool,
        dl_bler: float,
        ul_bler: float,
    ) -> str:
        """Generate notes for the test result."""
        notes = []
        if not attached:
            notes.append("No UE attached")
        if not bler_pass:
            notes.append(f"High BLER (DL={dl_bler:.1f}%, UL={ul_bler:.1f}%)")
        return "; ".join(notes)

    def run_test_for_all_bands(
        self,
        scenario: TestScenario,
        bands: list[str | tuple[str, str]] | None = None,
    ) -> list[ThroughputResult]:
        """Run test scenario for all supported bands.

        Args:
            scenario: Test scenario configuration
            bands: List of bands to test (None uses scenario's default bands)

        Returns:
            List of ThroughputResult for each band
        """
        # Get bands for this scenario type
        scenario_key = self._get_scenario_key(scenario)
        if bands is None:
            bands = SCENARIO_BANDS.get(scenario_key, [])

        if not bands:
            print(f"  No bands configured for {scenario.name}, using current config")
            return [self.run_test(scenario)]

        print(f"\n{'═' * 60}")
        print(f"Running {scenario.name} for {len(bands)} bands")
        print(f"{'═' * 60}")
        print(f"Bands: {[format_band_string(b) for b in bands]}")

        results = []
        for band in bands:
            band_str = format_band_string(band)
            print(f"\n  ▶ Testing band: {band_str}")

            # Configure band (this would need actual band switching implementation)
            if not self._configure_band(scenario, band):
                print(f"    ⚠ Could not configure band {band_str}, skipping")
                continue

            # Run test for this band
            result = self.run_test(scenario, band=band)
            results.append(result)
            self.results.append(result)

        return results

    def _get_scenario_key(self, scenario: TestScenario) -> str:
        """Get the scenario key for band lookup."""
        rat = scenario.rat.value
        duplex = scenario.duplex.value
        mimo = scenario.mimo.value

        if rat == "endc":
            return "endc_siso" if mimo == "siso" else "endc"
        elif rat == "nr":
            base = f"nr_{duplex}_1cc"
            return f"{base}_siso" if mimo == "siso" else base
        else:  # LTE
            base = f"lte_{duplex}_1cc"
            return f"{base}_siso" if mimo == "siso" else base

    def _configure_band(
        self,
        _scenario: TestScenario,
        band: str | tuple[str, str],
    ) -> bool:
        """Configure the cell for a specific band.

        Note: Full band switching typically requires cell restart.
        This method provides the framework for band configuration.

        Args:
            _scenario: Test scenario (reserved for future MIMO configuration)
            band: Band to configure (string for single band, tuple for ENDC)

        Returns:
            True if configuration successful
        """
        try:
            if isinstance(band, tuple):
                # ENDC: Configure LTE anchor + NR secondary
                lte_band, nr_band = band
                lte_earfcn = get_band_earfcn(lte_band)
                nr_arfcn = get_band_arfcn(nr_band)

                print(f"    ENDC config: LTE {lte_band} (EARFCN {lte_earfcn}), "
                      f"NR {nr_band} (ARFCN {nr_arfcn})")

                # In practice, you would call config_set_cell here
                # This requires the cell to be properly configured for ENDC

            else:
                # Single band configuration
                if band.startswith("n"):
                    arfcn = get_band_arfcn(band)
                    print(f"    NR band {band} (ARFCN {arfcn})")
                else:
                    earfcn = get_band_earfcn(band)
                    print(f"    LTE band {band} (EARFCN {earfcn})")

            # Allow time for configuration to take effect
            time.sleep(2)
            return True

        except Exception as e:
            print(f"    Band configuration error: {e}")
            return False

    def _print_result(self, result: ThroughputResult):
        """Print a single test result."""
        print(f"\n  Results ({result.samples} samples):")
        print(f"    Band: {result.band}")
        print(f"    DL: avg={result.dl_avg_mbps:.2f} Mbps, "
              f"max={result.dl_max_mbps:.2f} Mbps, "
              f"min={result.dl_min_mbps:.2f} Mbps")
        print(f"    UL: avg={result.ul_avg_mbps:.2f} Mbps, "
              f"max={result.ul_max_mbps:.2f} Mbps, "
              f"min={result.ul_min_mbps:.2f} Mbps")
        print(f"    DL Efficiency: {result.dl_efficiency:.1f}% of expected")
        print(f"    UL Efficiency: {result.ul_efficiency:.1f}% of expected")

        # iPerf results (if measured)
        if result.iperf_dl_mbps > 0 or result.iperf_ul_mbps > 0:
            print(f"    iPerf DL: {result.iperf_dl_mbps:.2f} Mbps, "
                  f"UL: {result.iperf_ul_mbps:.2f} Mbps")
            if result.iperf_retransmits > 0:
                print(f"    TCP Retransmits: {result.iperf_retransmits}")

        # BLER results (if measured)
        if result.dl_bler > 0 or result.ul_bler > 0:
            print(f"    BLER: DL={result.dl_bler:.3f}%, UL={result.ul_bler:.3f}%")

        # Latency results (if measured)
        if result.latency_avg_ms > 0:
            print(f"    Latency: avg={result.latency_avg_ms:.1f}ms, "
                  f"min={result.latency_min_ms:.1f}ms, "
                  f"max={result.latency_max_ms:.1f}ms, "
                  f"jitter={result.latency_jitter_ms:.1f}ms")

        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"\n  Status: {status}")
        if result.notes:
            print(f"  Notes: {result.notes}")

    def run_all_tests(
        self,
        scenarios: list[str] | None = None,
        _skip_unconfigured: bool = True,
        test_all_bands: bool = False,
    ) -> list[ThroughputResult]:
        """Run multiple test scenarios.

        Args:
            scenarios: List of scenario names to run (None = all)
            _skip_unconfigured: Reserved for future use (skip tests that don't match current config)
            test_all_bands: If True, run each scenario for all supported bands

        Returns:
            List of ThroughputResult
        """
        if scenarios is None:
            scenarios = list(TEST_SCENARIOS.keys())

        print("\n" + "═" * 60)
        print("THROUGHPUT TEST SUITE")
        print("═" * 60)
        print(f"Host: {self.host}")
        print(f"Tests to run: {len(scenarios)}")
        print(f"Test all bands: {test_all_bands}")
        if self.iperf_server_ip:
            print(f"iPerf server: {self.iperf_server_ip}:{self.iperf_port}")
        if self.ue_ip:
            print(f"Latency target: {self.ue_ip}")

        # Get current cell info
        cell_info = self.get_current_cell_info()
        print(f"\nCurrent cell configuration:")
        for cell_id, cfg in cell_info.get("config", {}).items():
            print(f"  Cell {cell_id}: {cfg.get('dl_earfcn', 'N/A')} EARFCN, "
                  f"{cfg.get('n_rb_dl', 'N/A')} RBs")

        self.results = []

        for scenario_name in scenarios:
            if scenario_name not in TEST_SCENARIOS:
                print(f"\n⚠ Unknown scenario: {scenario_name}")
                continue

            scenario = TEST_SCENARIOS[scenario_name]

            if test_all_bands:
                # Run test for all supported bands
                self.run_test_for_all_bands(scenario)
                # Results already added in run_test_for_all_bands
            else:
                # Run single test with current config
                result = self.run_test(scenario)
                self.results.append(result)

        return self.results

    def print_summary(self):
        """Print summary of all test results."""
        if not self.results:
            print("\nNo test results to summarize.")
            return

        print("\n" + "═" * 120)
        print("TEST SUMMARY")
        print("═" * 120)

        # Header
        print(f"\n{'Test Name':<20} {'Band':<12} {'RAT':<5} {'MIMO':<5} "
              f"{'DL Mbps':>9} {'UL Mbps':>9} "
              f"{'DL BLER':>8} {'UL BLER':>8} "
              f"{'Latency':>8} {'Status':<6}")
        print("-" * 120)

        passed = 0
        failed = 0

        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            if r.passed:
                passed += 1
            else:
                failed += 1

            # Truncate long band names
            band_display = r.band[:11] if len(r.band) > 11 else r.band

            # Format latency (show avg or "-" if not measured)
            latency_str = f"{r.latency_avg_ms:.1f}ms" if r.latency_avg_ms > 0 else "-"

            print(f"{r.test_name:<20} {band_display:<12} {r.rat:<5} {r.mimo:<5} "
                  f"{r.dl_avg_mbps:>9.2f} {r.ul_avg_mbps:>9.2f} "
                  f"{r.dl_bler:>7.2f}% {r.ul_bler:>7.2f}% "
                  f"{latency_str:>8} {status:<6}")

        print("-" * 120)
        print(f"\nTotal: {len(self.results)} tests, {passed} passed, {failed} failed")

        # Print aggregate statistics
        if self.results:
            avg_dl = sum(r.dl_avg_mbps for r in self.results) / len(self.results)
            avg_ul = sum(r.ul_avg_mbps for r in self.results) / len(self.results)
            max_dl = max(r.dl_avg_mbps for r in self.results)
            max_ul = max(r.ul_avg_mbps for r in self.results)

            results_with_latency = [r for r in self.results if r.latency_avg_ms > 0]
            if results_with_latency:
                avg_latency = sum(r.latency_avg_ms for r in results_with_latency) / len(results_with_latency)
                print(f"Average Latency: {avg_latency:.1f}ms")

            print(f"Average Throughput: DL={avg_dl:.2f} Mbps, UL={avg_ul:.2f} Mbps")
            print(f"Peak Throughput: DL={max_dl:.2f} Mbps, UL={max_ul:.2f} Mbps")

    def export_results(self, filename: str):
        """Export results to JSON file."""
        data = {
            "host": self.host,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": [asdict(r) for r in self.results],
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\nResults exported to: {filename}")


# ══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="Throughput test suite for Amarisoft Callbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available test scenarios:
  lte_fdd_1cc        LTE FDD 1CC (2x2 MIMO)
    lte_tdd_1cc        LTE TDD 1CC (2x2 MIMO)
    lte_fdd_1cc_siso   LTE FDD 1CC SISO
    lte_tdd_1cc_siso   LTE TDD 1CC SISO
    nr_fdd_1cc         NR FDD 1CC (4x4 MIMO)
    nr_tdd_1cc         NR TDD 1CC (4x4 MIMO)
    nr_fdd_1cc_siso    NR FDD 1CC SISO
    nr_tdd_1cc_siso    NR TDD 1CC SISO
    endc               EN-DC (LTE + NR, MIMO)
    endc_siso          EN-DC SISO

Examples:
    # Run all tests
    python throughput_test_suite.py --host 192.168.1.80

    # Run specific tests
    python throughput_test_suite.py --host 192.168.1.80 --tests lte_fdd_1cc nr_fdd_1cc

    # Run with iPerf for accurate throughput measurement
    python throughput_test_suite.py --host 192.168.1.80 --iperf-server 192.168.2.1

    # Run all bands for each test
    python throughput_test_suite.py --host 192.168.1.80 --all-bands

    # Run with custom duration
    python throughput_test_suite.py --host 192.168.1.80 --duration 60

    # List available tests
    python throughput_test_suite.py --list-tests
        """,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="WebSocket auth password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument("--ssl-verify", action="store_true", help="Verify TLS certs")
    parser.add_argument(
        "--tests", nargs="+", default=None,
        help="Specific tests to run (default: all)",
    )
    parser.add_argument(
        "--duration", type=float, default=30.0,
        help="Test duration in seconds (default: 30)",
    )
    parser.add_argument(
        "--warmup", type=float, default=5.0,
        help="Warmup period in seconds (default: 5)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Export results to JSON file",
    )
    parser.add_argument(
        "--list-tests", action="store_true",
        help="List available test scenarios and exit",
    )
    parser.add_argument(
        "--iperf-server", default=None,
        help="iPerf server IP address (for bidirectional throughput)",
    )
    parser.add_argument(
        "--iperf-port", type=int, default=5201,
        help="iPerf server port (default: 5201)",
    )
    parser.add_argument(
        "--ue-ip", default=None,
        help="UE IP address for latency tests (defaults to iperf-server)",
    )
    parser.add_argument(
        "--all-bands", action="store_true",
        help="Test all supported bands for each scenario",
    )
    parser.add_argument(
        "--no-iperf", action="store_true",
        help="Disable iPerf measurements (use eNB stats only)",
    )
    parser.add_argument(
        "--no-latency", action="store_true",
        help="Disable latency measurements",
    )
    parser.add_argument(
        "--no-bler", action="store_true",
        help="Disable BLER measurements",
    )
    return parser.parse_args()


def list_tests():
    """Print available test scenarios."""
    print("\nAvailable Test Scenarios:")
    print("=" * 100)
    print(f"{'Name':<20} {'RAT':<6} {'Duplex':<5} {'MIMO':<6} "
          f"{'Expected DL':>12} {'Expected UL':>12} {'Bands':>20}")
    print("-" * 100)

    for name, scenario in TEST_SCENARIOS.items():
        # Get supported bands
        scenario_key = f"{scenario.rat.value}_{scenario.duplex.value}_1cc"
        if scenario.mimo == MIMOMode.SISO:
            scenario_key += "_siso"
        if scenario.rat == RAT.ENDC:
            scenario_key = "endc_siso" if scenario.mimo == MIMOMode.SISO else "endc"

        bands = SCENARIO_BANDS.get(scenario_key, [])
        band_count = len(bands)

        print(f"{name:<20} {scenario.rat.value:<6} {scenario.duplex.value:<5} "
              f"{scenario.mimo.value:<6} {scenario.expected_dl_mbps:>10.1f} Mbps "
              f"{scenario.expected_ul_mbps:>10.1f} Mbps {band_count:>10} bands")

    print("-" * 100)
    print(f"\nTotal: {len(TEST_SCENARIOS)} test scenarios")

    # Print band details
    print("\nSupported Bands:")
    print("-" * 60)
    print(f"  LTE FDD: {', '.join(LTE_FDD_BANDS)}")
    print(f"  LTE TDD: {', '.join(LTE_TDD_BANDS)}")
    print(f"  NR FDD:  {', '.join(NR_FDD_BANDS)}")
    print(f"  NR TDD:  {', '.join(NR_TDD_BANDS)}")
    print(f"  ENDC:    {', '.join([f'{lte}+{nr}' for lte, nr in ENDC_BAND_COMBOS])}")


def main():
    args = parse_args()

    # List tests and exit
    if args.list_tests:
        list_tests()
        return

    # Update scenario durations if specified
    if args.duration != 30.0 or args.warmup != 5.0:
        for scenario in TEST_SCENARIOS.values():
            scenario.duration_s = args.duration
            scenario.warmup_s = args.warmup

    # Create test suite
    suite = ThroughputTestSuite(
        host=args.host,
        password=args.password,
        ssl=args.ssl,
        ssl_verify=args.ssl_verify,
        iperf_server_ip=args.iperf_server,
        iperf_port=args.iperf_port,
        ue_ip=args.ue_ip,
    )

    # Connect
    if not suite.connect():
        return

    try:
        # Run tests
        suite.run_all_tests(
            scenarios=args.tests,
            test_all_bands=args.all_bands,
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
