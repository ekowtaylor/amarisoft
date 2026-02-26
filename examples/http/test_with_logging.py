#!/usr/bin/env python3
"""End-to-end test with automatic log collection example via HTTP.

Demonstrates:
- Using TestSession for automatic log capture during test runs
- Step-based test organization with timing
- Automatic diagnostics export (logs, stats, config)
- Validation integration with logging
- Error handling and failure analysis

Output Structure:
    ./logs/<test_name>_<timestamp>/
    ├── session_info.json    # Test metadata, steps, timing
    ├── logs_enb.txt         # eNB logs (text format)
    ├── logs_mme.txt         # MME logs (text format)
    ├── logs_ims.txt         # IMS logs (text format)
    ├── logs_all.txt         # All logs combined (chronological)
    ├── logs_all.json        # All logs in JSON format
    ├── config_initial.json  # Configuration at test start
    ├── stats_initial.json   # Statistics at test start
    ├── stats_final.json     # Statistics at test end
    └── summary.txt          # Human-readable summary

Requirements:
    pip install requests

Usage:
    python test_with_logging.py
    python test_with_logging.py --url http://192.168.1.80:9010
    python test_with_logging.py --offline  # Run without device
"""

import argparse
import logging
import time

from client.http import Callbox, ConnectionError, HTTPClientError
from client.http.capabilities import (
    CapabilityChecker,
    DeviceCapabilities,
    ValidationContext,
)
from client.http.logging import enable_file_logging, LogCollector, TestSession


def parse_args():
    parser = argparse.ArgumentParser(
        description="End-to-end test with log collection via HTTP"
    )
    parser.add_argument(
        "--url",
        default="http://192.168.1.80:9010",
        help="REST API service URL",
    )
    parser.add_argument(
        "--output-dir",
        default="./logs",
        help="Directory for test logs (default: ./logs)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run offline simulation (no device connection)",
    )
    return parser.parse_args()


def run_offline_simulation():
    """Simulate a test session without a device connection."""
    print("=" * 60)
    print("OFFLINE TEST SESSION SIMULATION")
    print("=" * 60)
    print("\nThis demonstrates the test structure without a device.")
    print("In a real test, logs would be collected via HTTP.\n")

    # Simulate test steps
    print("Step 1: Would check service health")
    print("  ✓ Health check simulated")

    print("\nStep 2: Would get version info")
    print("  ✓ Version: 2024-12-01 (simulated)")

    print("\nStep 3: Would configure RF parameters")
    print("  ✓ RF configuration simulated")

    print("\nStep 4: Would check cell status")
    print("  ✓ Cells: 2 active (simulated)")

    print("\nStep 5: Would monitor throughput")
    for i in range(3):
        print(f"  [{i+1}s] DL=150.0 Mbps, UL=50.0 Mbps (simulated)")
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("OFFLINE SIMULATION COMPLETE")
    print("=" * 60)
    print("\nTo run a real test with log collection:")
    print(f"  python {__file__} --url http://192.168.1.80:9010")


def run_test_session(args):
    """Run a full test session with log collection via HTTP."""

    # Enable Python logging to file
    enable_file_logging(f"{args.output_dir}/amarisoft_http.log")

    # Configure console logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print("=" * 60)
    print("STARTING HTTP TEST SESSION WITH LOG COLLECTION")
    print("=" * 60)
    print(f"Target: {args.url}")
    print(f"Output: {args.output_dir}")
    print()

    try:
        with Callbox(args.url, timeout=args.timeout) as cb:
            # Create a test session with automatic log collection
            with TestSession(
                cb,
                name="http_connectivity_test",
                output_dir=args.output_dir,
                collect_interval=1.0,  # Poll logs every second
                auto_export=True,
                collect_on_error=True,
            ) as session:

                # --- Step 1: Health Check ---
                with session.add_step("Health Check"):
                    print("\nChecking service health...")
                    health = cb.health_check()
                    status = health.get("status", "unknown")
                    print(f"  Status: {status}")

                    if status != "healthy":
                        raise RuntimeError(f"Service unhealthy: {status}")
                    print("  ✓ Service is healthy")

                # --- Step 2: Service Info ---
                with session.add_step("Get Service Info"):
                    print("\nGetting service information...")
                    try:
                        help_info = cb.enb.help()
                        cmds = help_info.get("commands", help_info.get("messages", []))
                        print(f"  eNB available commands: {len(cmds)}")
                    except Exception as e:
                        print(f"  Could not get eNB help: {e}")

                # --- Step 3: Discover Capabilities ---
                with session.add_step("Discover Capabilities"):
                    print("\nDiscovering device capabilities...")
                    caps = DeviceCapabilities.from_callbox(cb)
                    print(f"  Version: {caps.version}")
                    print(f"  Max Cells: {caps.max_cells}")
                    print(f"  Max UEs: {caps.max_ues}")
                    print(f"  Supported Bands: {caps.band_numbers}")

                # --- Step 4: Check Cell Status ---
                with session.add_step("Check Cell Status"):
                    print("\nChecking cell status...")
                    try:
                        cells = cb.enb.cells_get()
                        cell_list = cells.get("cells", cells.get("cell_list", []))
                        print(f"  Active cells: {len(cell_list)}")

                        for cell in cell_list[:5]:
                            cell_id = cell.get("cell_id", "?")
                            band = cell.get("band", "?")
                            print(f"    Cell {cell_id}: Band {band}")
                    except Exception as e:
                        print(f"  Could not get cells: {e}")

                # --- Step 5: Check UE Connectivity ---
                with session.add_step("Check UE Connectivity"):
                    print("\nChecking UE connectivity...")

                    try:
                        enb_ues = cb.enb.ue_get()
                        ue_list = enb_ues.get("ue_list", [])
                        print(f"  UEs at eNB: {len(ue_list)}")
                    except Exception as e:
                        print(f"  Could not get eNB UEs: {e}")

                    try:
                        mme_ues = cb.mme.ue_get()
                        ue_list = mme_ues.get("ue_list", [])
                        print(f"  UEs at MME: {len(ue_list)}")
                    except Exception as e:
                        print(f"  Could not get MME UEs: {e}")

                # --- Step 6: Collect Statistics ---
                with session.add_step("Collect Statistics"):
                    print("\nCollecting statistics...")
                    try:
                        stats = cb.enb.stats(rf=True)

                        cells = stats.get("cells", [])
                        print(f"  Cells reporting: {len(cells)}")

                        for cell in cells[:3]:
                            dl = cell.get("dl_bitrate", 0) / 1e6
                            ul = cell.get("ul_bitrate", 0) / 1e6
                            print(
                                f"    Cell {cell.get('cell_id', '?')}: "
                                f"DL={dl:.1f}Mbps, UL={ul:.1f}Mbps"
                            )
                    except Exception as e:
                        print(f"  Could not get stats: {e}")

                # --- Step 7: Brief Throughput Monitoring ---
                with session.add_step("Monitor Throughput (5s)"):
                    print("\nMonitoring throughput for 5 seconds...")

                    for i in range(5):
                        try:
                            stats = cb.enb.stats()
                            cells = stats.get("cells", [])
                            for cell in cells[:2]:
                                dl = cell.get("dl_bitrate", 0) / 1e6
                                ul = cell.get("ul_bitrate", 0) / 1e6
                                print(
                                    f"  [{i+1}s] Cell {cell.get('cell_id', '?')}: "
                                    f"DL={dl:.1f}Mbps, UL={ul:.1f}Mbps"
                                )
                        except Exception as e:
                            print(f"  [{i+1}s] Error: {e}")
                        time.sleep(1)

                # --- Print Log Summary ---
                print("\n" + "-" * 60)
                print("LOG SUMMARY")
                print("-" * 60)

                errors = session.get_errors()
                warnings = session.get_warnings()

                print(f"  Total logs collected: {len(session.logs)}")
                print(f"  Errors: {len(errors)}")
                print(f"  Warnings: {len(warnings)}")

                if errors:
                    print("\n  Recent errors:")
                    for err in errors[-5:]:
                        msg = (
                            err.message[:60] + "..."
                            if len(err.message) > 60
                            else err.message
                        )
                        print(f"    [{err.service}] {msg}")

            # Session ended - diagnostics exported automatically
            print("\n" + "=" * 60)
            print("TEST SESSION COMPLETE")
            print("=" * 60)
            print(f"\nDiagnostics exported to: {args.output_dir}/")

    except HTTPClientError as e:
        print(f"\n✗ HTTP Client Error: {e}")
        print("\nDiagnostics have been exported for analysis.")
        raise


def example_custom_log_collection(args):
    """Example of custom log collection without TestSession."""
    print("\n" + "=" * 60)
    print("CUSTOM LOG COLLECTION EXAMPLE")
    print("=" * 60)

    with Callbox(args.url, timeout=args.timeout) as cb:
        # Create a log collector
        collector = LogCollector(cb)

        # Collect logs once
        print("\nCollecting logs once...")
        entries = collector.collect_once()
        print(f"  Collected {len(entries)} log entries")

        # Start continuous collection with callback
        print("\nStarting continuous collection (3 seconds)...")

        def on_log(entry):
            msg = (
                entry.message[:50] + "..." if len(entry.message) > 50 else entry.message
            )
            print(f"  [{entry.service}:{entry.layer}] {msg}")

        collector.start_continuous(interval=0.5, callback=on_log)
        time.sleep(3)
        collector.stop_continuous()

        # Filter logs
        print("\nFiltering logs by layer...")
        phy_logs = collector.filter_logs(layer="PHY")
        rrc_logs = collector.filter_logs(layer="RRC")
        nas_logs = collector.filter_logs(layer="NAS")

        print(f"  PHY logs: {len(phy_logs)}")
        print(f"  RRC logs: {len(rrc_logs)}")
        print(f"  NAS logs: {len(nas_logs)}")

        # Get errors
        errors = collector.filter_logs(level="ERROR")
        if errors:
            print(f"\n  Found {len(errors)} errors:")
            for err in errors[:3]:
                print(f"    {err}")


def main():
    args = parse_args()

    if args.offline:
        run_offline_simulation()
        return

    try:
        run_test_session(args)
    except ConnectionError as e:
        print(f"\n✗ Connection error: {e}")
        print(f"\nMake sure the REST API service is running at {args.url}")
        print("\nRun with --offline to see a simulation without device connection.")
    except Exception as e:
        print(f"\nTest session failed: {e}")
        print("\nRun with --offline to see a simulation without device connection.")


if __name__ == "__main__":
    main()
