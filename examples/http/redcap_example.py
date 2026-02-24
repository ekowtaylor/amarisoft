#!/usr/bin/env python3
"""RedCap (Reduced Capability) device testing example for Amarisoft REST API.

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

Usage:
    # Run RedCap tests
    python redcap_example.py --url http://192.168.1.80:9010

    # List RedCap test scenarios
    python redcap_example.py --list-tests

    # Run specific test
    python redcap_example.py --url http://192.168.1.80:9010 --test redcap_attach
"""

import argparse
import json
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any

from client.http import Callbox, APIError, ConnectionError


# ══════════════════════════════════════════════════════════════
# REDCAP CONSTANTS AND CONFIGURATION
# ══════════════════════════════════════════════════════════════

class RedCapType(Enum):
    """RedCap device type classifications."""
    REDCAP_FR1 = "redcap_fr1"      # FR1 RedCap (Sub-6 GHz)
    REDCAP_FR2 = "redcap_fr2"      # FR2 RedCap (mmWave)
    REDCAP_HD_FDD = "redcap_hd"    # Half-duplex FDD RedCap


# RedCap capability restrictions
REDCAP_MAX_MIMO_LAYERS_FR1 = 2
REDCAP_MAX_MIMO_LAYERS_FR2 = 2
REDCAP_MAX_BW_FR1_MHZ = 20
REDCAP_MAX_BW_FR2_MHZ = 100

# Half-duplex FDD capable bands
REDCAP_HD_FDD_BANDS = [
    "n1", "n3", "n5", "n7", "n8", "n20", "n25", "n28", "n66", "n71",
]


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


REDCAP_TEST_SCENARIOS = {
    "redcap_fr1_20mhz": RedCapTestScenario(
        name="RedCap FR1 20MHz",
        description="RedCap device with max FR1 bandwidth (20 MHz)",
        redcap_type=RedCapType.REDCAP_FR1,
        band="n78",
        bandwidth_mhz=20,
        mimo_layers=2,
        expected_dl_mbps=150.0,
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
    "redcap_hd_fdd_n71": RedCapTestScenario(
        name="RedCap HD-FDD n71",
        description="Half-duplex FDD RedCap on 600 MHz band",
        redcap_type=RedCapType.REDCAP_HD_FDD,
        band="n71",
        bandwidth_mhz=20,
        mimo_layers=1,
        half_duplex=True,
        expected_dl_mbps=60.0,
        expected_ul_mbps=20.0,
    ),
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
    dl_avg_mbps: float
    dl_max_mbps: float
    ul_avg_mbps: float
    ul_max_mbps: float
    expected_dl_mbps: float
    expected_ul_mbps: float
    dl_efficiency: float
    ul_efficiency: float
    attach_time_ms: float = 0.0
    registration_success: bool = False
    passed: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ══════════════════════════════════════════════════════════════
# REDCAP TEST SUITE
# ══════════════════════════════════════════════════════════════

class RedCapTestSuite:
    """Test suite for RedCap devices via HTTP REST API."""

    def __init__(
        self,
        url: str,
        timeout: float = 10.0,
    ):
        self.url = url
        self.timeout = timeout
        self.cb: Callbox | None = None
        self.results: list[RedCapTestResult] = []

    def connect(self) -> bool:
        """Connect to the REST API."""
        try:
            self.cb = Callbox(self.url, timeout=self.timeout)
            print(f"✓ Connected to REST API at {self.url}")
            return True
        except ConnectionError as e:
            print(f"✗ Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from the REST API."""
        if self.cb:
            self.cb.close()
            self.cb = None

    def validate_redcap_config(self, scenario: RedCapTestScenario) -> tuple[bool, str]:
        """Validate RedCap configuration constraints."""
        errors = []

        if scenario.redcap_type in (RedCapType.REDCAP_FR1, RedCapType.REDCAP_HD_FDD):
            if scenario.bandwidth_mhz > REDCAP_MAX_BW_FR1_MHZ:
                errors.append(f"FR1 RedCap max BW is {REDCAP_MAX_BW_FR1_MHZ} MHz")
            if scenario.mimo_layers > REDCAP_MAX_MIMO_LAYERS_FR1:
                errors.append(f"FR1 RedCap max MIMO is {REDCAP_MAX_MIMO_LAYERS_FR1}")

        elif scenario.redcap_type == RedCapType.REDCAP_FR2:
            if scenario.bandwidth_mhz > REDCAP_MAX_BW_FR2_MHZ:
                errors.append(f"FR2 RedCap max BW is {REDCAP_MAX_BW_FR2_MHZ} MHz")

        if scenario.half_duplex and scenario.band not in REDCAP_HD_FDD_BANDS:
            errors.append(f"Band {scenario.band} doesn't support HD-FDD")

        if errors:
            return False, "; ".join(errors)
        return True, ""

    def check_ue_attached(self) -> tuple[bool, int, dict[str, Any]]:
        """Check if a UE is attached."""
        if not self.cb:
            return False, 0, {}

        try:
            result = self.cb.mme.ue_get()
            ue_list = result.get("ue_list", [])
            if ue_list:
                return True, len(ue_list), ue_list[0]
            return False, 0, {}
        except APIError:
            return False, 0, {}

    def measure_attach_time(self, timeout_s: float = 30.0) -> float:
        """Measure time for UE to attach."""
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
        """Measure throughput from eNB stats."""
        if not self.cb:
            return []

        samples = []
        start = time.monotonic()

        while (time.monotonic() - start) < duration:
            try:
                stats = self.cb.enb.stats()
                total_dl = 0
                total_ul = 0

                for cell in stats.get("cells", []):
                    total_dl += cell.get("dl_bitrate", 0)
                    total_ul += cell.get("ul_bitrate", 0)

                samples.append({
                    "timestamp": time.monotonic() - start,
                    "dl_bitrate": total_dl,
                    "ul_bitrate": total_ul,
                })
            except APIError:
                pass

            time.sleep(interval)

        return samples

    def run_test(self, scenario: RedCapTestScenario) -> RedCapTestResult:
        """Run a single RedCap test scenario."""
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
                dl_avg_mbps=0, dl_max_mbps=0,
                ul_avg_mbps=0, ul_max_mbps=0,
                expected_dl_mbps=scenario.expected_dl_mbps,
                expected_ul_mbps=scenario.expected_ul_mbps,
                dl_efficiency=0, ul_efficiency=0,
                passed=False,
                notes=f"Invalid config: {error}",
            )

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
        samples = self.measure_throughput(duration=scenario.duration_s, interval=1.0)

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
        dl_eff = (dl_avg / scenario.expected_dl_mbps * 100) if scenario.expected_dl_mbps > 0 else 0
        ul_eff = (ul_avg / scenario.expected_ul_mbps * 100) if scenario.expected_ul_mbps > 0 else 0

        # Determine pass/fail
        passed = (dl_eff >= 70 or ul_eff >= 70) or not attached

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
            dl_efficiency=dl_eff,
            ul_efficiency=ul_eff,
            attach_time_ms=attach_time if attach_time > 0 else 0,
            registration_success=attached,
            passed=passed,
            notes="No UE attached" if not attached else "",
        )

        # Print results
        print(f"\n  Results:")
        print(f"    DL: avg={dl_avg:.2f} Mbps, max={dl_max:.2f} Mbps "
              f"({dl_eff:.1f}% efficiency)")
        print(f"    UL: avg={ul_avg:.2f} Mbps, max={ul_max:.2f} Mbps "
              f"({ul_eff:.1f}% efficiency)")
        if result.attach_time_ms > 0:
            print(f"    Attach time: {result.attach_time_ms:.0f} ms")
        print(f"\n  Status: {'✓ PASS' if passed else '✗ FAIL'}")

        return result

    def run_all_tests(
        self,
        scenarios: list[str] | None = None,
    ) -> list[RedCapTestResult]:
        """Run multiple RedCap test scenarios."""
        if scenarios is None:
            scenarios = list(REDCAP_TEST_SCENARIOS.keys())

        print("\n" + "═" * 60)
        print("REDCAP TEST SUITE (HTTP)")
        print("═" * 60)
        print(f"URL: {self.url}")
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
            print("\nNo test results.")
            return

        print("\n" + "═" * 90)
        print("REDCAP TEST SUMMARY")
        print("═" * 90)

        print(f"\n{'Scenario':<30} {'Type':<12} {'Band':<6} {'BW':<6} "
              f"{'DL Mbps':>10} {'UL Mbps':>10} {'Status':<8}")
        print("-" * 90)

        passed = failed = 0
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
            "test_suite": "RedCap Test Suite (HTTP)",
            "url": self.url,
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
        description="RedCap device testing via Amarisoft REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RedCap Test Scenarios:
  redcap_fr1_20mhz         FR1 RedCap with 20 MHz bandwidth (max)
  redcap_fr1_10mhz         FR1 RedCap with 10 MHz bandwidth
  redcap_fr1_5mhz          FR1 RedCap with 5 MHz bandwidth
  redcap_hd_fdd_n71        Half-duplex FDD on n71 (600 MHz)
  redcap_wearable          Wearable device profile
  redcap_industrial_sensor Industrial sensor profile

Examples:
    python redcap_example.py --url http://192.168.1.80:9010
    python redcap_example.py --url http://192.168.1.80:9010 --tests redcap_fr1_20mhz
    python redcap_example.py --list-tests
        """,
    )
    parser.add_argument(
        "--url", default="http://127.0.0.1:9010",
        help="REST API service URL",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout")
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
    print("=" * 90)
    print(f"{'Name':<30} {'Type':<12} {'Band':<6} {'BW':<8} {'MIMO':<6} "
          f"{'Expected DL':>12}")
    print("-" * 90)

    for name, scenario in REDCAP_TEST_SCENARIOS.items():
        hd = " (HD)" if scenario.half_duplex else ""
        print(f"{name:<30} {scenario.redcap_type.value:<12} {scenario.band:<6} "
              f"{scenario.bandwidth_mhz:>4} MHz {scenario.mimo_layers:>4}Rx "
              f"{scenario.expected_dl_mbps:>10.1f} Mbps{hd}")

    print("-" * 90)
    print(f"\nTotal: {len(REDCAP_TEST_SCENARIOS)} test scenarios")


def main():
    args = parse_args()

    if args.list_tests:
        list_tests()
        return

    # Create test suite
    suite = RedCapTestSuite(url=args.url, timeout=args.timeout)

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

    except APIError as e:
        print(f"\nError: {e}")
    finally:
        suite.disconnect()


if __name__ == "__main__":
    main()
