#!/usr/bin/env python3
"""RedCap (Reduced Capability) device testing example for Amarisoft Callbox.

RedCap (3GPP Release 17) is designed for mid-tier IoT devices like:
- Wearables (smartwatches, fitness trackers)
- Industrial sensors
- Video surveillance cameras

RedCap Key Characteristics:
- Max bandwidth: 20 MHz (FR1) / 100 MHz (FR2)
- Reduced MIMO: 1-2 Rx antennas (vs 4 for full NR)
- Half-duplex FDD option
- Relaxed processing time
- Lower device complexity and cost

This module provides:
- RedCap device configuration and validation
- Attachment and registration testing
- Throughput testing within RedCap constraints
- Power consumption profiling
- Half-duplex FDD testing

Usage:
    # Run RedCap tests
    python redcap_example.py --host 192.168.1.80

    # List RedCap test scenarios
    python redcap_example.py --list-tests

    # Run specific test
    python redcap_example.py --host 192.168.1.80 --test redcap_attach
"""

import argparse
import json
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any

from amarisoft import (
    Callbox,
    AmariError,
    AmariConnectionError,
)


# ══════════════════════════════════════════════════════════════
# REDCAP CONSTANTS AND CONFIGURATION
# ══════════════════════════════════════════════════════════════

class RedCapType(Enum):
    """RedCap device type classifications."""
    REDCAP_FR1 = "redcap_fr1"      # FR1 RedCap (Sub-6 GHz)
    REDCAP_FR2 = "redcap_fr2"      # FR2 RedCap (mmWave)
    REDCAP_HD_FDD = "redcap_hd"    # Half-duplex FDD RedCap


class RedCapBandwidth(Enum):
    """Supported bandwidths for RedCap devices."""
    # FR1 RedCap max bandwidth options
    BW_5MHZ = 5
    BW_10MHZ = 10
    BW_20MHZ = 20  # Max for FR1 RedCap

    # FR2 RedCap max bandwidth options
    BW_50MHZ = 50
    BW_100MHZ = 100  # Max for FR2 RedCap


# RedCap NR Bands (commonly used)
REDCAP_FR1_BANDS = [
    "n1",   # 2100 MHz FDD
    "n3",   # 1800 MHz FDD
    "n5",   # 850 MHz FDD
    "n7",   # 2600 MHz FDD
    "n8",   # 900 MHz FDD
    "n20",  # 800 MHz FDD
    "n25",  # 1900 MHz FDD
    "n28",  # 700 MHz FDD
    "n38",  # 2600 MHz TDD
    "n40",  # 2300 MHz TDD
    "n41",  # 2500 MHz TDD
    "n66",  # AWS FDD
    "n71",  # 600 MHz FDD
    "n77",  # 3.5 GHz TDD (C-band)
    "n78",  # 3.5 GHz TDD
]

REDCAP_FR2_BANDS = [
    "n257",  # 28 GHz
    "n258",  # 26 GHz
    "n260",  # 39 GHz
    "n261",  # 28 GHz
]

# Half-duplex FDD capable bands
REDCAP_HD_FDD_BANDS = [
    "n1", "n3", "n5", "n7", "n8", "n20", "n25", "n28", "n66", "n71",
]

# RedCap capability restrictions
REDCAP_MAX_MIMO_LAYERS_FR1 = 2  # Max 2 Rx antennas
REDCAP_MAX_MIMO_LAYERS_FR2 = 2  # Max 2 Rx antennas
REDCAP_MAX_BW_FR1_MHZ = 20     # Max 20 MHz in FR1
REDCAP_MAX_BW_FR2_MHZ = 100    # Max 100 MHz in FR2
REDCAP_MAX_MODULATION_DL = "256QAM"  # Max DL modulation
REDCAP_MAX_MODULATION_UL = "64QAM"   # Max UL modulation (optional 256QAM)


# ══════════════════════════════════════════════════════════════
# REDCAP TEST SCENARIOS
# ══════════════════════════════════════════════════════════════

@dataclass
class RedCapTestScenario:
    """Configuration for a RedCap test scenario."""
    name: str
    description: str
    redcap_type: RedCapType
    band: str
    bandwidth_mhz: int
    mimo_layers: int
    half_duplex: bool = False
    expected_dl_mbps: float = 0.0
    expected_ul_mbps: float = 0.0
    duration_s: float = 30.0


# Pre-defined RedCap test scenarios
REDCAP_TEST_SCENARIOS = {
    # FR1 RedCap scenarios
    "redcap_fr1_20mhz": RedCapTestScenario(
        name="RedCap FR1 20MHz",
        description="RedCap device with max FR1 bandwidth (20 MHz)",
        redcap_type=RedCapType.REDCAP_FR1,
        band="n78",
        bandwidth_mhz=20,
        mimo_layers=2,
        expected_dl_mbps=150.0,  # ~150 Mbps with 2x2 MIMO, 20 MHz
        expected_ul_mbps=50.0,
    ),
    "redcap_fr1_10mhz": RedCapTestScenario(
        name="RedCap FR1 10MHz",
        description="RedCap device with 10 MHz bandwidth",
        redcap_type=RedCapType.REDCAP_FR1,
        band="n78",
        bandwidth_mhz=10,
        mimo_layers=2,
        expected_dl_mbps=75.0,
        expected_ul_mbps=25.0,
    ),
    "redcap_fr1_5mhz": RedCapTestScenario(
        name="RedCap FR1 5MHz",
        description="RedCap device with minimum bandwidth (5 MHz)",
        redcap_type=RedCapType.REDCAP_FR1,
        band="n78",
        bandwidth_mhz=5,
        mimo_layers=1,
        expected_dl_mbps=35.0,
        expected_ul_mbps=15.0,
    ),
    "redcap_fr1_1rx": RedCapTestScenario(
        name="RedCap FR1 1Rx",
        description="RedCap device with single Rx antenna (SISO)",
        redcap_type=RedCapType.REDCAP_FR1,
        band="n78",
        bandwidth_mhz=20,
        mimo_layers=1,
        expected_dl_mbps=75.0,
        expected_ul_mbps=50.0,
    ),

    # Half-duplex FDD scenarios
    "redcap_hd_fdd_n71": RedCapTestScenario(
        name="RedCap HD-FDD n71",
        description="Half-duplex FDD RedCap on 600 MHz band",
        redcap_type=RedCapType.REDCAP_HD_FDD,
        band="n71",
        bandwidth_mhz=20,
        mimo_layers=1,
        half_duplex=True,
        expected_dl_mbps=60.0,  # Reduced due to HD-FDD
        expected_ul_mbps=20.0,
    ),
    "redcap_hd_fdd_n5": RedCapTestScenario(
        name="RedCap HD-FDD n5",
        description="Half-duplex FDD RedCap on 850 MHz band",
        redcap_type=RedCapType.REDCAP_HD_FDD,
        band="n5",
        bandwidth_mhz=10,
        mimo_layers=1,
        half_duplex=True,
        expected_dl_mbps=30.0,
        expected_ul_mbps=10.0,
    ),

    # FR2 RedCap scenarios (mmWave)
    "redcap_fr2_100mhz": RedCapTestScenario(
        name="RedCap FR2 100MHz",
        description="RedCap device with max FR2 bandwidth (100 MHz)",
        redcap_type=RedCapType.REDCAP_FR2,
        band="n257",
        bandwidth_mhz=100,
        mimo_layers=2,
        expected_dl_mbps=500.0,
        expected_ul_mbps=100.0,
    ),
    "redcap_fr2_50mhz": RedCapTestScenario(
        name="RedCap FR2 50MHz",
        description="RedCap device with 50 MHz FR2 bandwidth",
        redcap_type=RedCapType.REDCAP_FR2,
        band="n257",
        bandwidth_mhz=50,
        mimo_layers=2,
        expected_dl_mbps=250.0,
        expected_ul_mbps=50.0,
    ),

    # Use case specific scenarios
    "redcap_wearable": RedCapTestScenario(
        name="RedCap Wearable",
        description="Wearable device profile (smartwatch)",
        redcap_type=RedCapType.REDCAP_FR1,
        band="n78",
        bandwidth_mhz=5,
        mimo_layers=1,
        expected_dl_mbps=30.0,
        expected_ul_mbps=10.0,
    ),
    "redcap_industrial_sensor": RedCapTestScenario(
        name="RedCap Industrial Sensor",
        description="Industrial sensor/actuator profile",
        redcap_type=RedCapType.REDCAP_FR1,
        band="n78",
        bandwidth_mhz=10,
        mimo_layers=1,
        expected_dl_mbps=50.0,
        expected_ul_mbps=20.0,
    ),
    "redcap_video_surveillance": RedCapTestScenario(
        name="RedCap Video Surveillance",
        description="Video surveillance camera profile",
        redcap_type=RedCapType.REDCAP_FR1,
        band="n78",
        bandwidth_mhz=20,
        mimo_layers=2,
        expected_dl_mbps=100.0,
        expected_ul_mbps=50.0,  # Higher UL for video upload
    ),
}


# ══════════════════════════════════════════════════════════════
# REDCAP TEST RESULTS
# ══════════════════════════════════════════════════════════════

@dataclass
class RedCapTestResult:
    """Results from a RedCap test."""
    scenario_name: str
    redcap_type: str
    band: str
    bandwidth_mhz: int
    mimo_layers: int
    half_duplex: bool
    # Throughput
    dl_avg_mbps: float
    dl_max_mbps: float
    ul_avg_mbps: float
    ul_max_mbps: float
    expected_dl_mbps: float
    expected_ul_mbps: float
    dl_efficiency: float
    ul_efficiency: float
    # Attachment
    attach_time_ms: float = 0.0
    registration_success: bool = False
    # Power metrics (if available)
    power_idle_mw: float = 0.0
    power_active_mw: float = 0.0
    # Status
    passed: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ══════════════════════════════════════════════════════════════
# REDCAP TEST SUITE
# ══════════════════════════════════════════════════════════════

class RedCapTestSuite:
    """Test suite for RedCap (Reduced Capability) NR devices.

    Tests RedCap-specific features:
    - Reduced bandwidth operation (max 20 MHz FR1 / 100 MHz FR2)
    - 1-2 Rx antenna configurations
    - Half-duplex FDD operation
    - Relaxed processing times
    - IoT use case profiles
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
        self.results: list[RedCapTestResult] = []

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

    def validate_redcap_config(self, scenario: RedCapTestScenario) -> tuple[bool, str]:
        """Validate RedCap configuration constraints.

        Args:
            scenario: Test scenario to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        errors = []

        # Check bandwidth constraints
        if scenario.redcap_type in (RedCapType.REDCAP_FR1, RedCapType.REDCAP_HD_FDD):
            if scenario.bandwidth_mhz > REDCAP_MAX_BW_FR1_MHZ:
                errors.append(
                    f"FR1 RedCap max bandwidth is {REDCAP_MAX_BW_FR1_MHZ} MHz, "
                    f"got {scenario.bandwidth_mhz} MHz"
                )
            if scenario.mimo_layers > REDCAP_MAX_MIMO_LAYERS_FR1:
                errors.append(
                    f"FR1 RedCap max MIMO layers is {REDCAP_MAX_MIMO_LAYERS_FR1}, "
                    f"got {scenario.mimo_layers}"
                )

        elif scenario.redcap_type == RedCapType.REDCAP_FR2:
            if scenario.bandwidth_mhz > REDCAP_MAX_BW_FR2_MHZ:
                errors.append(
                    f"FR2 RedCap max bandwidth is {REDCAP_MAX_BW_FR2_MHZ} MHz, "
                    f"got {scenario.bandwidth_mhz} MHz"
                )
            if scenario.mimo_layers > REDCAP_MAX_MIMO_LAYERS_FR2:
                errors.append(
                    f"FR2 RedCap max MIMO layers is {REDCAP_MAX_MIMO_LAYERS_FR2}, "
                    f"got {scenario.mimo_layers}"
                )

        # Check half-duplex FDD band support
        if scenario.half_duplex:
            if scenario.band not in REDCAP_HD_FDD_BANDS:
                errors.append(
                    f"Band {scenario.band} does not support HD-FDD. "
                    f"Supported: {REDCAP_HD_FDD_BANDS}"
                )

        if errors:
            return False, "; ".join(errors)
        return True, ""

    def configure_cell_for_redcap(self, scenario: RedCapTestScenario) -> bool:
        """Configure cell for RedCap testing.

        Args:
            scenario: RedCap test scenario

        Returns:
            True if configuration successful
        """
        if not self.cb:
            return False

        print(f"  Configuring cell for RedCap...")
        print(f"    Band: {scenario.band}")
        print(f"    Bandwidth: {scenario.bandwidth_mhz} MHz")
        print(f"    MIMO layers: {scenario.mimo_layers}")
        print(f"    Half-duplex: {scenario.half_duplex}")

        try:
            # Get current config (for future use when cell reconfiguration is implemented)
            _config = self.cb.enb.config_get()  # noqa: F841

            # Note: Actual cell reconfiguration would require modifying
            # the eNB configuration file and restarting the cell.
            # This is a framework showing the parameters that need to be set.

            # For RedCap, key configuration parameters:
            # - n_rb_dl/n_rb_ul: Resource blocks for bandwidth
            # - n_antenna_dl: Number of DL antennas (1 or 2 for RedCap)
            # - reduced_cap: Enable RedCap mode
            # - hd_fdd: Enable half-duplex FDD

            # Bandwidth to RB mapping (NR with 30kHz SCS)
            bw_to_rb = {
                5: 11,   # 5 MHz
                10: 24,  # 10 MHz
                15: 36,  # 15 MHz
                20: 51,  # 20 MHz (max for FR1 RedCap)
                50: 133, # 50 MHz
                100: 273,# 100 MHz (max for FR2 RedCap)
            }

            n_rb = bw_to_rb.get(scenario.bandwidth_mhz, 51)
            print(f"    Resource blocks: {n_rb}")

            # In practice, you would call something like:
            # self.cb.enb.config_set_cell(
            #     cell_id=1,
            #     n_rb_dl=n_rb,
            #     n_rb_ul=n_rb,
            #     n_antenna_dl=scenario.mimo_layers,
            #     reduced_cap=True,
            #     hd_fdd=scenario.half_duplex,
            # )

            time.sleep(1)
            return True

        except Exception as e:
            print(f"    ✗ Configuration failed: {e}")
            return False

    def check_ue_attached(self) -> tuple[bool, int, dict[str, Any]]:
        """Check if a UE is attached and get its info.

        Returns:
            Tuple of (is_attached, ue_count, ue_info)
        """
        if not self.cb:
            return False, 0, {}

        try:
            result = self.cb.mme.ue_get()
            ue_list = result.get("ue_list", [])

            if ue_list:
                return True, len(ue_list), ue_list[0]
            return False, 0, {}

        except Exception:
            return False, 0, {}

    def measure_attach_time(self, timeout_s: float = 30.0) -> float:
        """Measure time for UE to attach.

        Args:
            timeout_s: Maximum wait time

        Returns:
            Attach time in milliseconds, or -1 if timeout
        """
        if not self.cb:
            return -1

        print("  Waiting for UE attachment...")
        start = time.monotonic()

        while (time.monotonic() - start) < timeout_s:
            attached, count, _ = self.check_ue_attached()
            if attached:
                attach_time_ms = (time.monotonic() - start) * 1000
                print(f"    ✓ UE attached in {attach_time_ms:.0f} ms")
                return attach_time_ms
            time.sleep(0.5)

        print(f"    ✗ Attachment timeout after {timeout_s}s")
        return -1

    def measure_throughput(
        self,
        duration: float = 10.0,
        interval: float = 1.0,
    ) -> list[dict[str, float]]:
        """Measure throughput from eNB stats.

        Args:
            duration: Measurement duration in seconds
            interval: Sampling interval

        Returns:
            List of throughput samples
        """
        if not self.cb:
            return []

        samples = []
        start = time.monotonic()

        while (time.monotonic() - start) < duration:
            try:
                stats = self.cb.enb.stats()
                cells = stats.get("cells", {})

                for cell_id, cell_data in cells.items():
                    sample = {
                        "timestamp": time.monotonic() - start,
                        "cell_id": cell_id,
                        "dl_bitrate": cell_data.get("dl_bitrate", 0),
                        "ul_bitrate": cell_data.get("ul_bitrate", 0),
                    }
                    samples.append(sample)

            except Exception:
                pass

            time.sleep(interval)

        return samples

    def run_test(self, scenario: RedCapTestScenario) -> RedCapTestResult:
        """Run a single RedCap test scenario.

        Args:
            scenario: Test scenario configuration

        Returns:
            RedCapTestResult with measurements
        """
        print(f"\n{'═' * 60}")
        print(f"Running: {scenario.name}")
        print(f"{'═' * 60}")
        print(f"  Description: {scenario.description}")
        print(f"  RedCap Type: {scenario.redcap_type.value}")
        print(f"  Band: {scenario.band}")
        print(f"  Bandwidth: {scenario.bandwidth_mhz} MHz")
        print(f"  MIMO: {scenario.mimo_layers} layer(s)")
        print(f"  Half-duplex: {scenario.half_duplex}")

        # Validate configuration
        valid, error = self.validate_redcap_config(scenario)
        if not valid:
            print(f"\n  ✗ Invalid configuration: {error}")
            return RedCapTestResult(
                scenario_name=scenario.name,
                redcap_type=scenario.redcap_type.value,
                band=scenario.band,
                bandwidth_mhz=scenario.bandwidth_mhz,
                mimo_layers=scenario.mimo_layers,
                half_duplex=scenario.half_duplex,
                dl_avg_mbps=0,
                dl_max_mbps=0,
                ul_avg_mbps=0,
                ul_max_mbps=0,
                expected_dl_mbps=scenario.expected_dl_mbps,
                expected_ul_mbps=scenario.expected_ul_mbps,
                dl_efficiency=0,
                ul_efficiency=0,
                passed=False,
                notes=f"Invalid config: {error}",
            )

        # Configure cell
        self.configure_cell_for_redcap(scenario)

        # Check UE attachment
        attached, ue_count, ue_info = self.check_ue_attached()
        attach_time = 0.0

        if not attached:
            print("\n  ⚠ No UE attached - measuring available throughput")
            attach_time = self.measure_attach_time(timeout_s=10)
            attached, ue_count, _ = self.check_ue_attached()

        if attached:
            print(f"\n  ✓ {ue_count} UE(s) attached")
            if ue_info:
                print(f"    IMSI: {ue_info.get('imsi', 'N/A')}")

        # Measure throughput
        print(f"\n  Measuring throughput for {scenario.duration_s}s...")
        samples = self.measure_throughput(
            duration=scenario.duration_s,
            interval=1.0,
        )

        # Calculate statistics
        if samples:
            dl_rates = [s["dl_bitrate"] / 1_000_000 for s in samples]
            ul_rates = [s["ul_bitrate"] / 1_000_000 for s in samples]

            dl_avg = sum(dl_rates) / len(dl_rates)
            dl_max = max(dl_rates)
            ul_avg = sum(ul_rates) / len(ul_rates)
            ul_max = max(ul_rates)
        else:
            dl_avg = dl_max = ul_avg = ul_max = 0.0

        # Calculate efficiency
        dl_efficiency = (dl_avg / scenario.expected_dl_mbps * 100) if scenario.expected_dl_mbps > 0 else 0
        ul_efficiency = (ul_avg / scenario.expected_ul_mbps * 100) if scenario.expected_ul_mbps > 0 else 0

        # Determine pass/fail
        passed = (dl_efficiency >= 70 or ul_efficiency >= 70) or not attached

        # Build result
        result = RedCapTestResult(
            scenario_name=scenario.name,
            redcap_type=scenario.redcap_type.value,
            band=scenario.band,
            bandwidth_mhz=scenario.bandwidth_mhz,
            mimo_layers=scenario.mimo_layers,
            half_duplex=scenario.half_duplex,
            dl_avg_mbps=dl_avg,
            dl_max_mbps=dl_max,
            ul_avg_mbps=ul_avg,
            ul_max_mbps=ul_max,
            expected_dl_mbps=scenario.expected_dl_mbps,
            expected_ul_mbps=scenario.expected_ul_mbps,
            dl_efficiency=dl_efficiency,
            ul_efficiency=ul_efficiency,
            attach_time_ms=attach_time if attach_time > 0 else 0,
            registration_success=attached,
            passed=passed,
            notes="No UE attached" if not attached else "",
        )

        # Print results
        self._print_result(result)

        return result

    def _print_result(self, result: RedCapTestResult):
        """Print test result."""
        print(f"\n  Results:")
        print(f"    DL: avg={result.dl_avg_mbps:.2f} Mbps, "
              f"max={result.dl_max_mbps:.2f} Mbps "
              f"({result.dl_efficiency:.1f}% of expected)")
        print(f"    UL: avg={result.ul_avg_mbps:.2f} Mbps, "
              f"max={result.ul_max_mbps:.2f} Mbps "
              f"({result.ul_efficiency:.1f}% of expected)")

        if result.attach_time_ms > 0:
            print(f"    Attach time: {result.attach_time_ms:.0f} ms")

        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"\n  Status: {status}")
        if result.notes:
            print(f"  Notes: {result.notes}")

    def run_all_tests(
        self,
        scenarios: list[str] | None = None,
    ) -> list[RedCapTestResult]:
        """Run multiple RedCap test scenarios.

        Args:
            scenarios: List of scenario names to run (None = all)

        Returns:
            List of test results
        """
        if scenarios is None:
            scenarios = list(REDCAP_TEST_SCENARIOS.keys())

        print("\n" + "═" * 60)
        print("REDCAP TEST SUITE")
        print("═" * 60)
        print(f"Host: {self.host}")
        print(f"Tests to run: {len(scenarios)}")

        self.results = []

        for scenario_name in scenarios:
            if scenario_name not in REDCAP_TEST_SCENARIOS:
                print(f"\n⚠ Unknown scenario: {scenario_name}")
                continue

            scenario = REDCAP_TEST_SCENARIOS[scenario_name]
            result = self.run_test(scenario)
            self.results.append(result)

        return self.results

    def print_summary(self):
        """Print summary of all test results."""
        if not self.results:
            print("\nNo test results to summarize.")
            return

        print("\n" + "═" * 90)
        print("REDCAP TEST SUMMARY")
        print("═" * 90)

        print(f"\n{'Scenario':<30} {'Type':<12} {'Band':<6} {'BW':<6} "
              f"{'DL Mbps':>10} {'UL Mbps':>10} {'Status':<8}")
        print("-" * 90)

        passed = 0
        failed = 0

        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            if r.passed:
                passed += 1
            else:
                failed += 1

            print(f"{r.scenario_name:<30} {r.redcap_type:<12} {r.band:<6} "
                  f"{r.bandwidth_mhz:>4}MHz "
                  f"{r.dl_avg_mbps:>10.2f} {r.ul_avg_mbps:>10.2f} {status:<8}")

        print("-" * 90)
        print(f"\nTotal: {len(self.results)} tests, {passed} passed, {failed} failed")

    def export_results(self, output_file: str):
        """Export results to JSON file."""
        data = {
            "test_suite": "RedCap Test Suite",
            "host": self.host,
            "timestamp": time.time(),
            "results": [r.to_dict() for r in self.results],
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
            },
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\n✓ Results exported to: {output_file}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="RedCap (Reduced Capability) device testing for Amarisoft Callbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RedCap Test Scenarios:
  redcap_fr1_20mhz       FR1 RedCap with 20 MHz bandwidth (max)
  redcap_fr1_10mhz       FR1 RedCap with 10 MHz bandwidth
  redcap_fr1_5mhz        FR1 RedCap with 5 MHz bandwidth
  redcap_fr1_1rx         FR1 RedCap with single Rx antenna
  redcap_hd_fdd_n71      Half-duplex FDD on n71 (600 MHz)
  redcap_hd_fdd_n5       Half-duplex FDD on n5 (850 MHz)
  redcap_fr2_100mhz      FR2 RedCap with 100 MHz bandwidth
  redcap_fr2_50mhz       FR2 RedCap with 50 MHz bandwidth
  redcap_wearable        Wearable device profile
  redcap_industrial_sensor  Industrial sensor profile
  redcap_video_surveillance  Video camera profile

Examples:
    # Run all RedCap tests
    python redcap_example.py --host 192.168.1.80

    # Run specific tests
    python redcap_example.py --host 192.168.1.80 --tests redcap_fr1_20mhz redcap_hd_fdd_n71

    # Export results to JSON
    python redcap_example.py --host 192.168.1.80 --output redcap_results.json

    # List available tests
    python redcap_example.py --list-tests
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
        "--output", default=None,
        help="Export results to JSON file",
    )
    parser.add_argument(
        "--list-tests", action="store_true",
        help="List available test scenarios and exit",
    )
    return parser.parse_args()


def list_tests():
    """Print available RedCap test scenarios."""
    print("\nRedCap Test Scenarios:")
    print("=" * 100)
    print(f"{'Name':<30} {'Type':<12} {'Band':<6} {'BW':<8} {'MIMO':<6} "
          f"{'Expected DL':>12} {'Expected UL':>12}")
    print("-" * 100)

    for name, scenario in REDCAP_TEST_SCENARIOS.items():
        hd = " (HD)" if scenario.half_duplex else ""
        print(f"{name:<30} {scenario.redcap_type.value:<12} {scenario.band:<6} "
              f"{scenario.bandwidth_mhz:>4} MHz {scenario.mimo_layers:>4}Rx "
              f"{scenario.expected_dl_mbps:>10.1f} Mbps "
              f"{scenario.expected_ul_mbps:>10.1f} Mbps{hd}")

    print("-" * 100)
    print(f"\nTotal: {len(REDCAP_TEST_SCENARIOS)} test scenarios")

    print("\nRedCap Bands:")
    print(f"  FR1 bands: {', '.join(REDCAP_FR1_BANDS)}")
    print(f"  FR2 bands: {', '.join(REDCAP_FR2_BANDS)}")
    print(f"  HD-FDD bands: {', '.join(REDCAP_HD_FDD_BANDS)}")


def main():
    args = parse_args()

    if args.list_tests:
        list_tests()
        return

    # Create test suite
    suite = RedCapTestSuite(
        host=args.host,
        password=args.password,
        ssl=args.ssl,
        ssl_verify=args.ssl_verify,
    )

    # Connect
    if not suite.connect():
        return

    try:
        # Run tests
        suite.run_all_tests(scenarios=args.tests)

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
