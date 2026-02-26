#!/usr/bin/env python3
"""End-to-end test with automatic log collection example.

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
"""

import argparse
import logging
import time

from client.websocket import (
    AmariError,
    Callbox,
    CapabilityChecker,
    enable_file_logging,
    get_default_capabilities,
    InvalidParameterError,
    RATType,
    # Logging
    TestSession,
    # Capabilities
    ValidationContext,
)


def parse_args():
    parser = argparse.ArgumentParser(description="End-to-end test with log collection")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify",
        action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    parser.add_argument(
        "--ims-port",
        type=int,
        default=9002,
        help="IMS port (use 9003 for CBM-2024121101)",
    )
    parser.add_argument(
        "--output-dir",
        default="./logs",
        help="Directory for test logs (default: ./logs)",
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
    print("\nThis demonstrates the TestSession structure without a device.")
    print("In a real test, logs would be collected from the Callbox.\n")

    # Simulate validation checks
    caps = get_default_capabilities()
    checker = CapabilityChecker(caps)

    print("Step 1: Validate RF Configuration")
    try:
        checker.validate_rf_gain(tx_gain=60, rx_gain=10, mode="wired")
        print("  ✓ RF gain validated for wired testing")
    except InvalidParameterError as e:
        print(f"  ✗ {e}")

    print("\nStep 2: Validate Cell Configuration")
    try:
        checker.validate_cell_config(bandwidth_mhz=20, mimo_layers=2)
        print("  ✓ Cell config validated: 20MHz, 2x2 MIMO")
    except InvalidParameterError as e:
        print(f"  ✗ {e}")

    print("\nStep 3: Validate MCS Settings")
    for mcs in [15, 28]:
        try:
            checker.validate_mcs(mcs, rat=RATType.LTE)
            print(f"  ✓ MCS={mcs} is valid for LTE")
        except InvalidParameterError as e:
            print(f"  ✗ MCS={mcs}: {e}")

    print("\n" + "=" * 60)
    print("OFFLINE SIMULATION COMPLETE")
    print("=" * 60)
    print("\nTo run a real test with log collection:")
    print(f"  python {__file__} --host 192.168.1.80 --ims-port 9003")


def run_test_session(args):
    """Run a full test session with log collection."""

    # Enable Python logging to file as well
    enable_file_logging(f"{args.output_dir}/amarisoft_python.log")

    # Configure console logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print("=" * 60)
    print("STARTING TEST SESSION WITH LOG COLLECTION")
    print("=" * 60)

    try:
        with Callbox(
            args.host,
            password=args.password,
            ssl=args.ssl,
            ssl_verify=args.ssl_verify,
            ims_port=args.ims_port,
        ) as cb:
            # Create a test session with automatic log collection
            with TestSession(
                cb,
                name="e2e_connectivity_test",
                output_dir=args.output_dir,
                collect_interval=0.5,  # Poll logs every 0.5s
                auto_export=True,
                collect_on_error=True,
            ) as session:

                # --- Step 1: Verify Services ---
                with session.add_step("Verify Service Connectivity"):
                    print("\nVerifying service connectivity...")
                    status = cb.status
                    print(f"  eNB: {'✓' if status['enb'] else '✗'}")
                    print(f"  MME: {'✓' if status['mme'] else '✗'}")
                    print(f"  IMS: {'✓' if status['ims'] else '✗'}")

                    if not any(status.values()):
                        raise RuntimeError("No services connected!")

                # --- Step 2: Discover Capabilities ---
                with session.add_step("Discover Device Capabilities"):
                    print("\nDiscovering device capabilities...")
                    caps = cb.discover_capabilities()
                    print(f"  Device: {caps.hostname}")
                    print(f"  Version: {caps.amarisoft_version}")
                    print(f"  Max Bandwidth: {caps.max_bandwidth_mhz} MHz")

                # --- Step 3: Configure RF with Validation ---
                with session.add_step("Configure RF Parameters"):
                    print("\nConfiguring RF parameters...")

                    with ValidationContext(cb) as ctx:
                        # Validate before applying
                        ctx.checker.validate_rf_gain(tx_gain=60, mode="wired")

                        # Apply configuration
                        result = cb.enb.rf(tx_gain=60)
                        print(f"  TX gain set: {result.get('tx_gain', 'N/A')}")

                # --- Step 4: Check Cell Status ---
                with session.add_step("Check Cell Status"):
                    print("\nChecking cell status...")
                    # cell_list() not supported - use config_get to find cells
                    config = cb.enb.config_get()
                    cell_list = config.get("cell_list", config.get("cells", []))
                    print(f"  Configured cells: {len(cell_list)}")

                    for cell in cell_list:
                        cell_id = cell.get("cell_id", "?")
                        band = cell.get("band", cell.get("dl_earfcn_band", "?"))
                        print(f"    Cell {cell_id}: Band {band}")

                # --- Step 5: Check UE Connectivity ---
                with session.add_step("Check UE Connectivity"):
                    print("\nChecking UE connectivity...")

                    enb_ues = cb.enb.ue_get()
                    ue_list = enb_ues.get("ue_list", [])
                    print(f"  UEs at eNB: {len(ue_list)}")

                    mme_ues = cb.mme.ue_get()
                    ue_list = mme_ues.get("ue_list", [])
                    print(f"  UEs at MME: {len(ue_list)}")

                # --- Step 6: Collect Statistics ---
                with session.add_step("Collect Statistics"):
                    print("\nCollecting statistics...")
                    stats = cb.enb.stats(rf=True)

                    rf_info = stats.get("rf", {})
                    if rf_info:
                        print(f"  TX gain: {rf_info.get('tx_gain', 'N/A')} dB")
                        print(f"  RX gain: {rf_info.get('rx_gain', 'N/A')} dB")

                # --- Step 7: Brief Throughput Monitoring ---
                with session.add_step("Monitor Throughput (5s)"):
                    print("\nMonitoring throughput for 5 seconds...")

                    for i in range(5):
                        stats = cb.enb.stats()
                        cells = stats.get("cells", [])
                        for cell in cells:
                            dl = cell.get("dl_bitrate", 0)
                            ul = cell.get("ul_bitrate", 0)
                            print(
                                f"  [{i+1}s] Cell {cell.get('cell_id')}: "
                                f"DL={dl/1e6:.2f}Mbps, UL={ul/1e6:.2f}Mbps"
                            )
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
                        print(f"    [{err.service}] {err.message[:60]}...")

            # Session has ended - diagnostics exported automatically
            print("\n" + "=" * 60)
            print("TEST SESSION COMPLETE")
            print("=" * 60)
            print(f"\nDiagnostics exported to: {args.output_dir}/")

    except AmariError as e:
        print(f"\n✗ Test failed with error: {e}")
        print("\nDiagnostics have been exported for analysis.")
        raise


def example_custom_log_collection(args):
    """Example of custom log collection without TestSession."""
    from client.websocket.logging import LogCollector

    print("\n" + "=" * 60)
    print("CUSTOM LOG COLLECTION EXAMPLE")
    print("=" * 60)

    with Callbox(
        args.host,
        password=args.password,
        ssl=args.ssl,
        ssl_verify=args.ssl_verify,
        ims_port=args.ims_port,
    ) as cb:
        # Create a log collector
        collector = LogCollector(cb)

        # Collect logs once
        print("\nCollecting logs once...")
        entries = collector.collect_once()
        print(f"  Collected {len(entries)} log entries")

        # Start continuous collection with callback
        print("\nStarting continuous collection (3 seconds)...")

        def on_log(entry):
            print(f"  [{entry.service}:{entry.layer}] {entry.message[:50]}...")

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
    except Exception as e:
        print(f"\nTest session failed: {e}")
        print("\nRun with --offline to see a simulation without device connection.")


if __name__ == "__main__":
    main()
