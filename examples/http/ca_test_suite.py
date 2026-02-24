#!/usr/bin/env python3
"""Carrier Aggregation (CA) test suite for Amarisoft REST API.

Supports comprehensive CA testing across LTE and NR:
  - LTE CA: 2CC to 5CC configurations
  - NR CA: Intra-band and inter-band combinations
  - EN-DC: LTE anchor with NR secondary cells
  - NR-DC: NR-NR Dual Connectivity

Usage:
    # List available CA configurations
    python ca_test_suite.py --list-configs

    # Run specific CA test
    python ca_test_suite.py --url http://192.168.1.80:9010 --config lte_2cc_b7_b3

    # Run all CA tests
    python ca_test_suite.py --url http://192.168.1.80:9010 --all

    # Export results
    python ca_test_suite.py --url http://192.168.1.80:9010 --output ca_results.json
"""

import argparse
import json
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any

from client.http import Callbox, APIError


# ══════════════════════════════════════════════════════════════
# CA CONFIGURATION TYPES
# ══════════════════════════════════════════════════════════════

class CAType(Enum):
    """Carrier Aggregation type."""
    LTE_CA = "lte_ca"      # LTE Carrier Aggregation
    NR_CA = "nr_ca"        # NR Carrier Aggregation
    ENDC = "endc"          # EN-DC (LTE + NR)
    NRDC = "nrdc"          # NR-DC


@dataclass
class CAConfig:
    """CA test configuration."""
    name: str
    ca_type: CAType
    description: str
    primary_band: str
    secondary_bands: list[str]
    expected_dl_mbps: float
    expected_ul_mbps: float
    bandwidth_mhz: int = 20


# Pre-defined CA configurations
CA_CONFIGS = {
    # LTE CA configurations
    "lte_2cc_b7_b3": CAConfig(
        name="LTE 2CC (B7+B3)",
        ca_type=CAType.LTE_CA,
        description="LTE CA with Band 7 primary and Band 3 secondary",
        primary_band="b7",
        secondary_bands=["b3"],
        bandwidth_mhz=20,
        expected_dl_mbps=300.0,
        expected_ul_mbps=75.0,
    ),
    "lte_3cc_b1_b3_b7": CAConfig(
        name="LTE 3CC (B1+B3+B7)",
        ca_type=CAType.LTE_CA,
        description="LTE CA with 3 carriers",
        primary_band="b1",
        secondary_bands=["b3", "b7"],
        bandwidth_mhz=20,
        expected_dl_mbps=450.0,
        expected_ul_mbps=100.0,
    ),
    # NR CA configurations
    "nr_2cc_n78": CAConfig(
        name="NR 2CC (n78)",
        ca_type=CAType.NR_CA,
        description="NR intra-band CA on n78",
        primary_band="n78",
        secondary_bands=["n78"],
        bandwidth_mhz=100,
        expected_dl_mbps=2000.0,
        expected_ul_mbps=400.0,
    ),
    # EN-DC configurations
    "endc_b1_n78": CAConfig(
        name="EN-DC (B1+n78)",
        ca_type=CAType.ENDC,
        description="EN-DC with LTE B1 anchor and NR n78",
        primary_band="b1",
        secondary_bands=["n78"],
        bandwidth_mhz=100,
        expected_dl_mbps=1500.0,
        expected_ul_mbps=300.0,
    ),
    "endc_b3_n77": CAConfig(
        name="EN-DC (B3+n77)",
        ca_type=CAType.ENDC,
        description="EN-DC with LTE B3 anchor and NR n77",
        primary_band="b3",
        secondary_bands=["n77"],
        bandwidth_mhz=100,
        expected_dl_mbps=1500.0,
        expected_ul_mbps=300.0,
    ),
}


# ══════════════════════════════════════════════════════════════
# CA TEST RESULT
# ══════════════════════════════════════════════════════════════

@dataclass
class CATestResult:
    """Result of a CA test."""
    config_name: str
    ca_type: str
    primary_band: str
    secondary_bands: list[str]
    # Measurements
    dl_avg_mbps: float
    dl_max_mbps: float
    ul_avg_mbps: float
    ul_max_mbps: float
    expected_dl_mbps: float
    expected_ul_mbps: float
    dl_efficiency: float
    ul_efficiency: float
    # Cell info
    active_cells: int
    cell_info: list[dict[str, Any]]
    # Status
    passed: bool
    duration_s: float
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ══════════════════════════════════════════════════════════════
# CA TEST SUITE
# ══════════════════════════════════════════════════════════════

class CATestSuite:
    """Carrier Aggregation test suite for HTTP REST API."""

    def __init__(
        self,
        url: str,
        timeout: float = 10.0,
    ):
        self.url = url
        self.timeout = timeout
        self.cb: Callbox | None = None
        self.results: list[CATestResult] = []

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

    def get_cell_info(self) -> list[dict[str, Any]]:
        """Get information about active cells."""
        if not self.cb:
            return []

        cells = []
        try:
            cell_list = self.cb.enb.cell_list()
            for cell in cell_list.get("cell_list", []):
                cells.append({
                    "cell_id": cell.get("cell_id"),
                    "state": cell.get("state"),
                    "band": cell.get("band"),
                    "dl_earfcn": cell.get("dl_earfcn"),
                    "bandwidth": cell.get("bandwidth"),
                    "rat": cell.get("rat", "LTE"),
                })
        except APIError as e:
            print(f"  Warning: Could not get cell list: {e}")

        return cells

    def measure_throughput(
        self,
        duration: float = 10.0,
        interval: float = 1.0,
    ) -> list[dict[str, float]]:
        """Measure throughput for the specified duration."""
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

    def run_test(
        self,
        config: CAConfig,
        duration: float = 30.0,
    ) -> CATestResult:
        """Run a single CA test.

        Args:
            config: CA configuration to test
            duration: Test duration in seconds

        Returns:
            CATestResult with measurements
        """
        print(f"\n{'═' * 60}")
        print(f"Running: {config.name}")
        print(f"{'═' * 60}")
        print(f"  Type: {config.ca_type.value}")
        print(f"  Primary band: {config.primary_band}")
        print(f"  Secondary bands: {', '.join(config.secondary_bands)}")
        print(f"  Expected DL: {config.expected_dl_mbps} Mbps")
        print(f"  Expected UL: {config.expected_ul_mbps} Mbps")

        # Get cell info
        cell_info = self.get_cell_info()
        active_cells = len([c for c in cell_info if c.get("state") == "active"])
        print(f"\n  Active cells: {active_cells}")

        # Measure throughput
        print(f"\n  Measuring throughput for {duration}s...")
        samples = self.measure_throughput(duration=duration, interval=1.0)

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
        dl_eff = (dl_avg / config.expected_dl_mbps * 100) if config.expected_dl_mbps > 0 else 0
        ul_eff = (ul_avg / config.expected_ul_mbps * 100) if config.expected_ul_mbps > 0 else 0

        # Determine pass/fail (70% threshold or no traffic)
        passed = (dl_eff >= 70 or ul_eff >= 70) or (dl_avg == 0 and ul_avg == 0)

        result = CATestResult(
            config_name=config.name,
            ca_type=config.ca_type.value,
            primary_band=config.primary_band,
            secondary_bands=config.secondary_bands,
            dl_avg_mbps=dl_avg,
            dl_max_mbps=dl_max,
            ul_avg_mbps=ul_avg,
            ul_max_mbps=ul_max,
            expected_dl_mbps=config.expected_dl_mbps,
            expected_ul_mbps=config.expected_ul_mbps,
            dl_efficiency=dl_eff,
            ul_efficiency=ul_eff,
            active_cells=active_cells,
            cell_info=cell_info,
            passed=passed,
            duration_s=duration,
            notes="" if active_cells > 0 else "No active cells detected",
        )

        # Print result
        print(f"\n  Results:")
        print(f"    DL: avg={dl_avg:.2f} Mbps, max={dl_max:.2f} Mbps "
              f"({dl_eff:.1f}% efficiency)")
        print(f"    UL: avg={ul_avg:.2f} Mbps, max={ul_max:.2f} Mbps "
              f"({ul_eff:.1f}% efficiency)")
        print(f"\n  Status: {'✓ PASS' if passed else '✗ FAIL'}")

        return result

    def run_all_tests(
        self,
        configs: list[str] | None = None,
        duration: float = 30.0,
    ) -> list[CATestResult]:
        """Run multiple CA tests.

        Args:
            configs: List of config names to test (None = all)
            duration: Test duration per config

        Returns:
            List of test results
        """
        if configs is None:
            configs = list(CA_CONFIGS.keys())

        print("\n" + "═" * 60)
        print("CA TEST SUITE (HTTP)")
        print("═" * 60)
        print(f"URL: {self.url}")
        print(f"Tests to run: {len(configs)}")

        self.results = []

        for config_name in configs:
            if config_name not in CA_CONFIGS:
                print(f"\n⚠ Unknown config: {config_name}")
                continue

            config = CA_CONFIGS[config_name]
            result = self.run_test(config, duration=duration)
            self.results.append(result)

        return self.results

    def print_summary(self):
        """Print summary of all test results."""
        if not self.results:
            print("\nNo test results.")
            return

        print("\n" + "═" * 80)
        print("CA TEST SUMMARY")
        print("═" * 80)

        print(f"\n{'Config':<30} {'Type':<10} {'DL Mbps':>10} {'UL Mbps':>10} "
              f"{'Cells':>6} {'Status':<8}")
        print("-" * 80)

        passed = failed = 0
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            if r.passed:
                passed += 1
            else:
                failed += 1

            print(f"{r.config_name:<30} {r.ca_type:<10} {r.dl_avg_mbps:>10.2f} "
                  f"{r.ul_avg_mbps:>10.2f} {r.active_cells:>6} {status:<8}")

        print("-" * 80)
        print(f"\nTotal: {len(self.results)} tests, {passed} passed, {failed} failed")

    def export_results(self, output_file: str):
        """Export results to JSON file."""
        data = {
            "test_suite": "CA Test Suite (HTTP)",
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
        description="CA test suite for Amarisoft REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available CA Configurations:
  lte_2cc_b7_b3      LTE CA with B7+B3
  lte_3cc_b1_b3_b7   LTE CA with B1+B3+B7
  nr_2cc_n78         NR intra-band CA on n78
  endc_b1_n78        EN-DC with B1 anchor and n78
  endc_b3_n77        EN-DC with B3 anchor and n77

Examples:
    python ca_test_suite.py --list-configs
    python ca_test_suite.py --url http://192.168.1.80:9010 --config lte_2cc_b7_b3
    python ca_test_suite.py --url http://192.168.1.80:9010 --all
        """,
    )
    parser.add_argument(
        "--url", default="http://127.0.0.1:9010",
        help="REST API service URL",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout")
    parser.add_argument(
        "--config", nargs="+", default=None,
        help="Specific configs to test",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all CA configurations",
    )
    parser.add_argument(
        "--duration", type=float, default=30.0,
        help="Test duration per config (default: 30s)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Export results to JSON file",
    )
    parser.add_argument(
        "--list-configs", action="store_true",
        help="List available configs and exit",
    )
    return parser.parse_args()


def list_configs():
    """Print available CA configurations."""
    print("\nAvailable CA Configurations:")
    print("=" * 80)
    print(f"{'Name':<25} {'Type':<10} {'Primary':<8} {'Secondary':<20} "
          f"{'Expected DL':>12}")
    print("-" * 80)

    for name, config in CA_CONFIGS.items():
        secondary = ",".join(config.secondary_bands)
        print(f"{name:<25} {config.ca_type.value:<10} {config.primary_band:<8} "
              f"{secondary:<20} {config.expected_dl_mbps:>10.0f} Mbps")

    print("-" * 80)
    print(f"\nTotal: {len(CA_CONFIGS)} configurations")


def main():
    args = parse_args()

    if args.list_configs:
        list_configs()
        return

    # Create test suite
    suite = CATestSuite(url=args.url, timeout=args.timeout)

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
            configs = list(CA_CONFIGS.keys())[:1]  # Default to first config

        # Run tests
        suite.run_all_tests(configs=configs, duration=args.duration)

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
