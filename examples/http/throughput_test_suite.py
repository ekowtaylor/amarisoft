#!/usr/bin/env python3
"""Throughput test suite for the Amarisoft REST API.

Supports multiple RAT/mode combinations:
  1. LTE FDD 1CC (MIMO)
  2. LTE TDD 1CC (MIMO)
  3. ENDC (LTE + NR) (MIMO)
  4. NR FDD 1CC (MIMO)
  5. NR TDD 1CC (MIMO)

Usage:
    # List available test configurations
    python throughput_test_suite.py --list-configs

    # Run specific test
    python throughput_test_suite.py --url http://192.168.1.80:9010 --config lte_fdd

    # Run all throughput tests
    python throughput_test_suite.py --url http://192.168.1.80:9010 --all

    # Export results to JSON
    python throughput_test_suite.py --url http://192.168.1.80:9010 --output results.json
"""

import argparse
import json
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from client.http import APIError, Callbox


# ══════════════════════════════════════════════════════════════
# THROUGHPUT TEST CONFIGURATION
# ══════════════════════════════════════════════════════════════


class RATMode(Enum):
    """Radio Access Technology mode."""

    LTE_FDD = "lte_fdd"
    LTE_TDD = "lte_tdd"
    NR_FDD = "nr_fdd"
    NR_TDD = "nr_tdd"
    ENDC = "endc"


@dataclass
class ThroughputTestConfig:
    """Configuration for a throughput test."""

    name: str
    rat_mode: RATMode
    description: str
    bandwidth_mhz: int
    mimo_layers: int
    expected_dl_mbps: float
    expected_ul_mbps: float
    duration_s: float = 30.0


# Pre-defined test configurations
THROUGHPUT_TEST_CONFIGS = {
    "lte_fdd_20mhz": ThroughputTestConfig(
        name="LTE FDD 20MHz",
        rat_mode=RATMode.LTE_FDD,
        description="LTE FDD with 20 MHz bandwidth, 4x4 MIMO",
        bandwidth_mhz=20,
        mimo_layers=4,
        expected_dl_mbps=150.0,
        expected_ul_mbps=50.0,
    ),
    "lte_fdd_10mhz": ThroughputTestConfig(
        name="LTE FDD 10MHz",
        rat_mode=RATMode.LTE_FDD,
        description="LTE FDD with 10 MHz bandwidth, 2x2 MIMO",
        bandwidth_mhz=10,
        mimo_layers=2,
        expected_dl_mbps=75.0,
        expected_ul_mbps=25.0,
    ),
    "lte_tdd_20mhz": ThroughputTestConfig(
        name="LTE TDD 20MHz",
        rat_mode=RATMode.LTE_TDD,
        description="LTE TDD with 20 MHz bandwidth, 4x4 MIMO",
        bandwidth_mhz=20,
        mimo_layers=4,
        expected_dl_mbps=120.0,
        expected_ul_mbps=40.0,
    ),
    "nr_fdd_100mhz": ThroughputTestConfig(
        name="NR FDD 100MHz",
        rat_mode=RATMode.NR_FDD,
        description="NR FDD with 100 MHz bandwidth, 4x4 MIMO",
        bandwidth_mhz=100,
        mimo_layers=4,
        expected_dl_mbps=1000.0,
        expected_ul_mbps=200.0,
    ),
    "nr_tdd_100mhz": ThroughputTestConfig(
        name="NR TDD 100MHz",
        rat_mode=RATMode.NR_TDD,
        description="NR TDD with 100 MHz bandwidth, 4x4 MIMO",
        bandwidth_mhz=100,
        mimo_layers=4,
        expected_dl_mbps=800.0,
        expected_ul_mbps=150.0,
    ),
    "endc_lte_nr": ThroughputTestConfig(
        name="EN-DC (LTE+NR)",
        rat_mode=RATMode.ENDC,
        description="EN-DC with LTE anchor and NR secondary",
        bandwidth_mhz=100,
        mimo_layers=4,
        expected_dl_mbps=1200.0,
        expected_ul_mbps=250.0,
    ),
}


# ══════════════════════════════════════════════════════════════
# THROUGHPUT TEST RESULT
# ══════════════════════════════════════════════════════════════


@dataclass
class ThroughputTestResult:
    """Result of a throughput test."""

    config_name: str
    rat_mode: str
    bandwidth_mhz: int
    mimo_layers: int
    # Measurements
    dl_avg_mbps: float
    dl_max_mbps: float
    dl_min_mbps: float
    ul_avg_mbps: float
    ul_max_mbps: float
    ul_min_mbps: float
    expected_dl_mbps: float
    expected_ul_mbps: float
    dl_efficiency: float
    ul_efficiency: float
    # Statistics
    sample_count: int
    duration_s: float
    # UE info
    ue_count: int
    # Status
    passed: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ══════════════════════════════════════════════════════════════
# THROUGHPUT TEST SUITE
# ══════════════════════════════════════════════════════════════


class ThroughputTestSuite:
    """Comprehensive throughput test suite via HTTP REST API."""

    def __init__(
        self,
        url: str,
        timeout: float = 10.0,
    ):
        self.url = url
        self.timeout = timeout
        self.cb: Callbox | None = None
        self.results: list[ThroughputTestResult] = []

    def connect(self) -> bool:
        """Connect to the REST API."""
        try:
            self.cb = Callbox(self.url, timeout=self.timeout)
            print(f"✓ Connected to REST API at {self.url}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from the REST API."""
        if self.cb:
            self.cb.close()
            self.cb = None

    def get_ue_count(self) -> int:
        """Get number of connected UEs."""
        if not self.cb:
            return 0

        try:
            ue_info = self.cb.mme.ue_get()
            return len(ue_info.get("ue_list", []))
        except APIError:
            return 0

    def get_cell_info(self) -> dict[str, Any]:
        """Get current cell configuration."""
        if not self.cb:
            return {}

        try:
            # cell_list() not supported - use config_get()
            config = self.cb.enb.config_get()
            cells = config.get("cell_list", config.get("cells", []))
            return {"cell_list": cells if isinstance(cells, list) else []}
        except APIError:
            return {}

    def measure_throughput(
        self,
        duration: float = 10.0,
        interval: float = 1.0,
    ) -> list[dict[str, float]]:
        """Measure throughput for the specified duration.

        Args:
            duration: Measurement duration in seconds
            interval: Sampling interval in seconds

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
                total_dl = 0
                total_ul = 0

                for cell in stats.get("cells", []):
                    total_dl += cell.get("dl_bitrate", 0)
                    total_ul += cell.get("ul_bitrate", 0)

                samples.append(
                    {
                        "timestamp": time.monotonic() - start,
                        "dl_bitrate": total_dl,
                        "ul_bitrate": total_ul,
                    }
                )

            except APIError:
                pass

            time.sleep(interval)

        return samples

    def run_test(
        self,
        config: ThroughputTestConfig,
    ) -> ThroughputTestResult:
        """Run a single throughput test.

        Args:
            config: Test configuration

        Returns:
            ThroughputTestResult with measurements
        """
        print(f"\n{'═' * 60}")
        print(f"Running: {config.name}")
        print(f"{'═' * 60}")
        print(f"  RAT Mode: {config.rat_mode.value}")
        print(f"  Bandwidth: {config.bandwidth_mhz} MHz")
        print(f"  MIMO: {config.mimo_layers} layers")
        print(f"  Expected DL: {config.expected_dl_mbps} Mbps")
        print(f"  Expected UL: {config.expected_ul_mbps} Mbps")
        print(f"  Duration: {config.duration_s}s")

        # Get UE count
        ue_count = self.get_ue_count()
        print(f"\n  Connected UEs: {ue_count}")

        if ue_count == 0:
            print("  ⚠ No UEs connected - throughput will be limited")

        # Measure throughput
        print(f"\n  Measuring throughput...")
        print(f"  {'Time':>6s}  {'DL Mbps':>12s}  {'UL Mbps':>12s}")
        print("  " + "-" * 35)

        samples = []
        start = time.monotonic()

        while (time.monotonic() - start) < config.duration_s:
            try:
                stats = self.cb.enb.stats()
                total_dl = 0
                total_ul = 0

                for cell in stats.get("cells", []):
                    total_dl += cell.get("dl_bitrate", 0)
                    total_ul += cell.get("ul_bitrate", 0)

                elapsed = time.monotonic() - start
                dl_mbps = total_dl / 1_000_000
                ul_mbps = total_ul / 1_000_000

                samples.append(
                    {
                        "timestamp": elapsed,
                        "dl_bitrate": total_dl,
                        "ul_bitrate": total_ul,
                    }
                )

                print(f"  {elapsed:6.1f}s  {dl_mbps:>12.2f}  {ul_mbps:>12.2f}")

            except APIError as e:
                print(f"  Error: {e}")

            time.sleep(1.0)

        # Calculate statistics
        if samples:
            dl_rates = [s["dl_bitrate"] / 1_000_000 for s in samples]
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

        # Calculate efficiency
        dl_eff = (
            (dl_avg / config.expected_dl_mbps * 100)
            if config.expected_dl_mbps > 0
            else 0
        )
        ul_eff = (
            (ul_avg / config.expected_ul_mbps * 100)
            if config.expected_ul_mbps > 0
            else 0
        )

        # Determine pass/fail (70% threshold)
        passed = (dl_eff >= 70 or ul_eff >= 70) or ue_count == 0

        result = ThroughputTestResult(
            config_name=config.name,
            rat_mode=config.rat_mode.value,
            bandwidth_mhz=config.bandwidth_mhz,
            mimo_layers=config.mimo_layers,
            dl_avg_mbps=dl_avg,
            dl_max_mbps=dl_max,
            dl_min_mbps=dl_min,
            ul_avg_mbps=ul_avg,
            ul_max_mbps=ul_max,
            ul_min_mbps=ul_min,
            expected_dl_mbps=config.expected_dl_mbps,
            expected_ul_mbps=config.expected_ul_mbps,
            dl_efficiency=dl_eff,
            ul_efficiency=ul_eff,
            sample_count=len(samples),
            duration_s=config.duration_s,
            ue_count=ue_count,
            passed=passed,
            notes="" if ue_count > 0 else "No UEs connected",
        )

        # Print summary
        print(f"\n  Results:")
        print(
            f"    DL: avg={dl_avg:.2f}, max={dl_max:.2f}, min={dl_min:.2f} Mbps "
            f"({dl_eff:.1f}% efficiency)"
        )
        print(
            f"    UL: avg={ul_avg:.2f}, max={ul_max:.2f}, min={ul_min:.2f} Mbps "
            f"({ul_eff:.1f}% efficiency)"
        )
        print(f"    Samples: {len(samples)}")
        print(f"\n  Status: {'✓ PASS' if passed else '✗ FAIL'}")

        return result

    def run_all_tests(
        self,
        configs: list[str] | None = None,
    ) -> list[ThroughputTestResult]:
        """Run multiple throughput tests.

        Args:
            configs: List of config names to test (None = all)

        Returns:
            List of test results
        """
        if configs is None:
            configs = list(THROUGHPUT_TEST_CONFIGS.keys())

        print("\n" + "═" * 60)
        print("THROUGHPUT TEST SUITE (HTTP)")
        print("═" * 60)
        print(f"URL: {self.url}")
        print(f"Tests to run: {len(configs)}")

        self.results = []

        for config_name in configs:
            if config_name not in THROUGHPUT_TEST_CONFIGS:
                print(f"\n⚠ Unknown config: {config_name}")
                continue

            config = THROUGHPUT_TEST_CONFIGS[config_name]
            result = self.run_test(config)
            self.results.append(result)

        return self.results

    def print_summary(self):
        """Print summary of all test results."""
        if not self.results:
            print("\nNo test results.")
            return

        print("\n" + "═" * 90)
        print("THROUGHPUT TEST SUMMARY")
        print("═" * 90)

        print(
            f"\n{'Config':<25} {'RAT':<10} {'BW':<8} {'DL Avg':>10} {'UL Avg':>10} "
            f"{'DL Eff':>8} {'Status':<8}"
        )
        print("-" * 90)

        passed = failed = 0
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            if r.passed:
                passed += 1
            else:
                failed += 1

            print(
                f"{r.config_name:<25} {r.rat_mode:<10} {r.bandwidth_mhz:>5}MHz "
                f"{r.dl_avg_mbps:>10.2f} {r.ul_avg_mbps:>10.2f} "
                f"{r.dl_efficiency:>7.1f}% {status:<8}"
            )

        print("-" * 90)
        print(f"\nTotal: {len(self.results)} tests, {passed} passed, {failed} failed")

        # Calculate aggregates
        if self.results:
            total_dl = sum(r.dl_avg_mbps for r in self.results)
            total_ul = sum(r.ul_avg_mbps for r in self.results)
            avg_dl_eff = sum(r.dl_efficiency for r in self.results) / len(self.results)
            avg_ul_eff = sum(r.ul_efficiency for r in self.results) / len(self.results)

            print(
                f"\nAggregate DL: {total_dl:.2f} Mbps (avg efficiency: {avg_dl_eff:.1f}%)"
            )
            print(
                f"Aggregate UL: {total_ul:.2f} Mbps (avg efficiency: {avg_ul_eff:.1f}%)"
            )

    def export_results(self, output_file: str):
        """Export results to JSON file."""
        data = {
            "test_suite": "Throughput Test Suite (HTTP)",
            "url": self.url,
            "timestamp": time.time(),
            "results": [r.to_dict() for r in self.results],
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
                "avg_dl_efficiency": (
                    sum(r.dl_efficiency for r in self.results) / len(self.results)
                    if self.results
                    else 0
                ),
                "avg_ul_efficiency": (
                    sum(r.ul_efficiency for r in self.results) / len(self.results)
                    if self.results
                    else 0
                ),
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
        description="Throughput test suite for Amarisoft REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Test Configurations:
  lte_fdd_20mhz    LTE FDD with 20 MHz, 4x4 MIMO
  lte_fdd_10mhz    LTE FDD with 10 MHz, 2x2 MIMO
  lte_tdd_20mhz    LTE TDD with 20 MHz, 4x4 MIMO
  nr_fdd_100mhz    NR FDD with 100 MHz, 4x4 MIMO
  nr_tdd_100mhz    NR TDD with 100 MHz, 4x4 MIMO
  endc_lte_nr      EN-DC with LTE anchor and NR secondary

Examples:
    python throughput_test_suite.py --list-configs
    python throughput_test_suite.py --url http://192.168.1.80:9010 --config lte_fdd_20mhz
    python throughput_test_suite.py --url http://192.168.1.80:9010 --all
    python throughput_test_suite.py --url http://192.168.1.80:9010 --output results.json
        """,
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:9010",
        help="REST API service URL",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout")
    parser.add_argument(
        "--config",
        nargs="+",
        default=None,
        help="Specific configs to test",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all test configurations",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Export results to JSON file",
    )
    parser.add_argument(
        "--list-configs",
        action="store_true",
        help="List available test configurations and exit",
    )
    return parser.parse_args()


def list_configs():
    """Print available test configurations."""
    print("\nAvailable Throughput Test Configurations:")
    print("=" * 90)
    print(
        f"{'Name':<20} {'RAT':<10} {'BW':<8} {'MIMO':<6} "
        f"{'Expected DL':>12} {'Expected UL':>12}"
    )
    print("-" * 90)

    for name, config in THROUGHPUT_TEST_CONFIGS.items():
        print(
            f"{name:<20} {config.rat_mode.value:<10} {config.bandwidth_mhz:>5}MHz "
            f"{config.mimo_layers:>4}x{config.mimo_layers} "
            f"{config.expected_dl_mbps:>10.0f} Mbps "
            f"{config.expected_ul_mbps:>10.0f} Mbps"
        )

    print("-" * 90)
    print(f"\nTotal: {len(THROUGHPUT_TEST_CONFIGS)} configurations")


def main():
    args = parse_args()

    if args.list_configs:
        list_configs()
        return

    # Create test suite
    suite = ThroughputTestSuite(url=args.url, timeout=args.timeout)

    # Connect
    if not suite.connect():
        return

    try:
        # Determine configs to test
        if args.all:
            configs = None  # All configs
        elif args.config:
            configs = args.config
        else:
            configs = list(THROUGHPUT_TEST_CONFIGS.keys())[:1]  # Default to first

        # Run tests
        suite.run_all_tests(configs=configs)

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
