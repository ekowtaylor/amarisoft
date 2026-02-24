#!/usr/bin/env python3
"""Throughput monitoring example for the Amarisoft Callbox.

Demonstrates:
- Polling eNB stats to extract DL/UL throughput per UE
- Optionally pinning MCS for fixed-rate measurements
- Periodic sampling over a configurable duration
- Computing average throughput across samples
"""

import argparse
import time

from client.websocket import (
    Callbox,
    AmariError,
    CommandError,
    InvalidParameterError,
    CapabilityChecker,
    RATType,
    get_default_capabilities,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Monitor DL/UL throughput")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    parser.add_argument(
        "--duration", type=float, default=10.0,
        help="Monitoring duration in seconds (default: 10)",
    )
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="Polling interval in seconds (default: 1)",
    )
    parser.add_argument(
        "--cell-id", type=int, default=None,
        help="Pin MCS on this cell before measuring",
    )
    parser.add_argument(
        "--dl-mcs", type=int, default=None,
        help="Fix downlink MCS (requires --cell-id)",
    )
    parser.add_argument(
        "--ul-mcs", type=int, default=None,
        help="Fix uplink MCS (requires --cell-id)",
    )
    return parser.parse_args()


def extract_throughput(stats_resp):
    """Extract per-cell DL/UL bitrate from a stats response."""
    cells = stats_resp.get("cells", [])
    results = []
    for cell in cells:
        results.append({
            "cell_id": cell.get("cell_id"),
            "dl_bitrate": cell.get("dl_bitrate", 0),
            "ul_bitrate": cell.get("ul_bitrate", 0),
            "dl_tx": cell.get("dl_tx", 0),
            "ul_tx": cell.get("ul_tx", 0),
        })
    return results


def format_bps(bps):
    """Format bits-per-second as human-readable string."""
    if bps >= 1_000_000_000:
        return f"{bps / 1_000_000_000:.2f} Gbps"
    if bps >= 1_000_000:
        return f"{bps / 1_000_000:.2f} Mbps"
    if bps >= 1_000:
        return f"{bps / 1_000:.2f} kbps"
    return f"{bps:.0f} bps"


def main():
    args = parse_args()

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl,
                     ssl_verify=args.ssl_verify) as cb:

            # --- Optionally pin MCS with validation ---
            if args.cell_id is not None:
                # Get checker for validation
                checker = CapabilityChecker(get_default_capabilities())

                if args.dl_mcs is not None:
                    print(f"Validating and setting DL MCS={args.dl_mcs} on cell {args.cell_id}")
                    try:
                        # Validate MCS is in valid LTE range (0-28)
                        checker.validate_mcs(args.dl_mcs, rat=RATType.LTE)
                        cb.enb.set_dl_config(args.cell_id, pdsch_mcs=args.dl_mcs)
                        print(f"  ✓ DL MCS set to {args.dl_mcs}")
                    except InvalidParameterError as e:
                        print(f"  ✗ Invalid MCS: {e}")
                    except CommandError as e:
                        print(f"  Warning: {e}")

                if args.ul_mcs is not None:
                    print(f"Validating and setting UL MCS={args.ul_mcs} on cell {args.cell_id}")
                    try:
                        # Validate MCS is in valid LTE range (0-28)
                        checker.validate_mcs(args.ul_mcs, rat=RATType.LTE)
                        cb.enb.set_ul_config(args.cell_id, pusch_mcs=args.ul_mcs)
                        print(f"  ✓ UL MCS set to {args.ul_mcs}")
                    except InvalidParameterError as e:
                        print(f"  ✗ Invalid MCS: {e}")
                    except CommandError as e:
                        print(f"  Warning: {e}")

            # --- Polling loop ---
            print(f"\nPolling throughput every {args.interval}s "
                  f"for {args.duration}s ...\n")
            print(f"{'Time':>6s}  {'Cell':>4s}  {'DL Bitrate':>14s}  "
                  f"{'UL Bitrate':>14s}")
            print("-" * 50)

            all_samples = []
            start = time.monotonic()

            while (time.monotonic() - start) < args.duration:
                stats = cb.enb.stats()
                elapsed = time.monotonic() - start
                cells = extract_throughput(stats)

                for cell in cells:
                    dl = cell["dl_bitrate"]
                    ul = cell["ul_bitrate"]
                    print(f"{elapsed:6.1f}s  {cell['cell_id']:>4}  "
                          f"{format_bps(dl):>14s}  {format_bps(ul):>14s}")
                    all_samples.append(cell)

                time.sleep(args.interval)

            # --- Summary ---
            if all_samples:
                print("\n" + "=" * 50)
                print("Summary")
                print("=" * 50)

                # Group by cell_id
                cell_ids = sorted(set(s["cell_id"] for s in all_samples))
                for cid in cell_ids:
                    cell_samples = [s for s in all_samples if s["cell_id"] == cid]
                    n = len(cell_samples)
                    avg_dl = sum(s["dl_bitrate"] for s in cell_samples) / n
                    avg_ul = sum(s["ul_bitrate"] for s in cell_samples) / n
                    max_dl = max(s["dl_bitrate"] for s in cell_samples)
                    max_ul = max(s["ul_bitrate"] for s in cell_samples)
                    print(f"\nCell {cid} ({n} samples):")
                    print(f"  DL avg: {format_bps(avg_dl)}  max: {format_bps(max_dl)}")
                    print(f"  UL avg: {format_bps(avg_ul)}  max: {format_bps(max_ul)}")
            else:
                print("\nNo samples collected.")

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
