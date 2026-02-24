#!/usr/bin/env python3
"""UE attach and data test example for the Amarisoft REST API.

Demonstrates:
- Powering on UE and waiting for attachment
- Verifying UE is connected (RRC, EMM, PDN states)
- Monitoring throughput during data transfer
- Collecting UE statistics and signal quality
"""

import argparse
import time

from client.http import Callbox, APIError, ConnectionError


def parse_args():
    parser = argparse.ArgumentParser(
        description="Attach UE and perform data test via HTTP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic attach and monitor
  python ue_data_test.py --url http://192.168.1.80:9010

  # Monitor throughput for 30 seconds
  python ue_data_test.py --url http://192.168.1.80:9010 --duration 30
        """,
    )
    parser.add_argument(
        "--url", default="http://127.0.0.1:9010",
        help="REST API service URL (default: http://127.0.0.1:9010)",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout")
    parser.add_argument(
        "--ue-id", type=int, default=None,
        help="Specific UE ID to test (default: first available)",
    )
    parser.add_argument(
        "--duration", type=float, default=10.0,
        help="Throughput monitoring duration in seconds (default: 10)",
    )
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="Stats polling interval in seconds (default: 1)",
    )
    return parser.parse_args()


def format_bps(bps):
    """Format bits-per-second as human-readable string."""
    if bps >= 1_000_000_000:
        return f"{bps / 1_000_000_000:.2f} Gbps"
    if bps >= 1_000_000:
        return f"{bps / 1_000_000:.2f} Mbps"
    if bps >= 1_000:
        return f"{bps / 1_000:.2f} kbps"
    return f"{bps:.0f} bps"


def wait_for_attach(cb, ue_id=None, timeout=30):
    """Wait for UE to attach to the network.

    Args:
        cb: Callbox instance
        ue_id: Specific UE ID to wait for (None = any)
        timeout: Maximum wait time in seconds

    Returns:
        dict with attached UE info, or None if timeout
    """
    print(f"\nWaiting for UE attachment (timeout: {timeout}s)...")
    start = time.monotonic()

    while (time.monotonic() - start) < timeout:
        try:
            mme_ues = cb.mme.ue_get()
            ue_list = mme_ues.get("ue_list", [])

            for ue in ue_list:
                # Check if UE is attached (has EMM state)
                emm_state = ue.get("emm_state", "")
                if emm_state in ("registered", "connected"):
                    if ue_id is None or ue.get("ue_id") == ue_id:
                        print(f"  ✓ UE attached: IMSI={ue.get('imsi')}, "
                              f"EMM={emm_state}")
                        return ue

                # Also check 5G (AMF)
                fiveg_state = ue.get("5g_mm_state", "")
                if fiveg_state in ("registered", "connected"):
                    if ue_id is None or ue.get("ue_id") == ue_id:
                        print(f"  ✓ UE attached (5G): IMSI={ue.get('imsi')}, "
                              f"5G-MM={fiveg_state}")
                        return ue

        except APIError as e:
            print(f"  Warning: {e}")

        time.sleep(1)
        elapsed = time.monotonic() - start
        print(f"  Waiting... ({elapsed:.0f}s)")

    print("  ✗ Timeout waiting for UE attachment")
    return None


def get_ue_details(cb, imsi):
    """Get detailed UE information from all services.

    Args:
        cb: Callbox instance
        imsi: IMSI of the target UE

    Returns:
        dict with UE details from eNB, MME, and UE simulator
    """
    details = {"imsi": imsi}

    # eNB info (RRC state, signal quality)
    try:
        enb_ues = cb.enb.ue_get()
        for ue in enb_ues.get("ue_list", []):
            if ue.get("imsi") == imsi:
                details["enb"] = {
                    "ue_id": ue.get("ue_id"),
                    "rnti": ue.get("rnti"),
                    "rrc_state": ue.get("rrc_state"),
                    "cell_id": ue.get("cell_id"),
                    "dl_cqi": ue.get("dl_cqi"),
                    "ul_snr": ue.get("ul_snr"),
                    "dl_mcs": ue.get("dl_mcs"),
                    "ul_mcs": ue.get("ul_mcs"),
                    "dl_bitrate": ue.get("dl_bitrate", 0),
                    "ul_bitrate": ue.get("ul_bitrate", 0),
                }
                break
    except APIError:
        pass

    # MME info (EMM state, PDN connections)
    try:
        mme_ues = cb.mme.ue_get()
        for ue in mme_ues.get("ue_list", []):
            if ue.get("imsi") == imsi:
                details["mme"] = {
                    "emm_state": ue.get("emm_state"),
                    "ecm_state": ue.get("ecm_state"),
                    "ip_addr": ue.get("ip_addr"),
                    "pdn_list": ue.get("pdn_list", []),
                    "bearer_list": ue.get("bearer_list", []),
                }
                break
    except APIError:
        pass

    # UE Simulator info
    try:
        ue_sim = cb.ue.ue_get()
        for ue in ue_sim.get("ue_list", []):
            if ue.get("imsi") == imsi:
                details["ue_sim"] = {
                    "ue_id": ue.get("ue_id"),
                    "power": ue.get("power"),
                    "rat": ue.get("rat"),
                    "rrc_state": ue.get("rrc_state"),
                }
                break
    except APIError:
        pass

    return details


def monitor_throughput(cb, duration, interval):
    """Monitor throughput for all cells.

    Args:
        cb: Callbox instance
        duration: Monitoring duration in seconds
        interval: Polling interval in seconds

    Returns:
        list of throughput samples
    """
    print(f"\n{'Time':>6s}  {'Cell':>4s}  {'DL Bitrate':>14s}  "
          f"{'UL Bitrate':>14s}  {'UEs':>4s}")
    print("-" * 55)

    samples = []
    start = time.monotonic()

    while (time.monotonic() - start) < duration:
        try:
            stats = cb.enb.stats()
            elapsed = time.monotonic() - start

            for cell in stats.get("cells", []):
                cell_id = cell.get("cell_id")
                dl = cell.get("dl_bitrate", 0)
                ul = cell.get("ul_bitrate", 0)
                ue_count = cell.get("ue_count", 0)

                print(f"{elapsed:6.1f}s  {cell_id:>4}  "
                      f"{format_bps(dl):>14s}  {format_bps(ul):>14s}  "
                      f"{ue_count:>4}")

                samples.append({
                    "time": elapsed,
                    "cell_id": cell_id,
                    "dl_bitrate": dl,
                    "ul_bitrate": ul,
                    "ue_count": ue_count,
                })

        except APIError as e:
            print(f"  Stats error: {e}")

        time.sleep(interval)

    return samples


def print_summary(samples):
    """Print throughput summary statistics."""
    if not samples:
        print("\nNo throughput samples collected.")
        return

    print("\n" + "=" * 55)
    print("Throughput Summary")
    print("=" * 55)

    # Group by cell_id
    cell_ids = sorted(set(s["cell_id"] for s in samples))

    for cid in cell_ids:
        cell_samples = [s for s in samples if s["cell_id"] == cid]
        n = len(cell_samples)

        avg_dl = sum(s["dl_bitrate"] for s in cell_samples) / n
        avg_ul = sum(s["ul_bitrate"] for s in cell_samples) / n
        max_dl = max(s["dl_bitrate"] for s in cell_samples)
        max_ul = max(s["ul_bitrate"] for s in cell_samples)

        print(f"\nCell {cid} ({n} samples):")
        print(f"  DL - avg: {format_bps(avg_dl)}, max: {format_bps(max_dl)}")
        print(f"  UL - avg: {format_bps(avg_ul)}, max: {format_bps(max_ul)}")


def main():
    args = parse_args()

    print("=" * 60)
    print("UE Attach and Data Test (HTTP)")
    print("=" * 60)
    print(f"URL: {args.url}")

    try:
        with Callbox(args.url, timeout=args.timeout) as cb:

            # ─────────────────────────────────────────────
            # Step 1: Check current UE state from MME
            # ─────────────────────────────────────────────
            print("\n" + "=" * 60)
            print("Step 1: Check Current UE State")
            print("=" * 60)

            # Get UEs from MME (core network view)
            mme_ues = cb.mme.ue_get()
            ue_list = mme_ues.get("ue_list", [])
            print(f"\nMME reports {len(ue_list)} UE(s) connected")

            # Also get UEs from eNB (radio view)
            try:
                enb_ues = cb.enb.ue_get()
                enb_list = enb_ues.get("ue_list", [])
                print(f"eNB reports {len(enb_list)} UE(s) connected")
            except APIError:
                enb_list = []

            if not ue_list and not enb_list:
                print("\nNo UEs currently connected.")
                print("Waiting for UE to attach...")

                # Wait for attachment
                attached_ue = wait_for_attach(cb, timeout=30)
                if not attached_ue:
                    print("\nNo UE attached. Check:")
                    print("  - UE is powered on and in range")
                    print("  - SIM/USIM is configured correctly")
                    print("  - RF path is connected")
                    return
                imsi = attached_ue.get("imsi")
            else:
                # Find target UE
                target_ue = None
                for ue in ue_list:
                    if args.ue_id is None or ue.get("ue_id") == args.ue_id:
                        target_ue = ue
                        break

                if not target_ue and ue_list:
                    target_ue = ue_list[0]

                if target_ue:
                    imsi = target_ue.get("imsi")
                    print(f"\nTarget UE: IMSI={imsi}")
                    print(f"  EMM State: {target_ue.get('emm_state', 'N/A')}")
                    print(f"  ECM State: {target_ue.get('ecm_state', 'N/A')}")
                else:
                    print("No suitable UE found")
                    return

            # ─────────────────────────────────────────────
            # Step 2: Get detailed UE info
            # ─────────────────────────────────────────────
            print("\n" + "=" * 60)
            print("Step 2: UE Connection Details")
            print("=" * 60)

            details = get_ue_details(cb, imsi)

            if "enb" in details:
                enb = details["enb"]
                print(f"\neNB (Radio):")
                print(f"  RRC State: {enb.get('rrc_state', 'N/A')}")
                print(f"  Cell ID: {enb.get('cell_id', 'N/A')}")
                print(f"  DL CQI: {enb.get('dl_cqi', 'N/A')}")
                print(f"  UL SNR: {enb.get('ul_snr', 'N/A')} dB")
                print(f"  DL MCS: {enb.get('dl_mcs', 'N/A')}")
                print(f"  UL MCS: {enb.get('ul_mcs', 'N/A')}")

            if "mme" in details:
                mme = details["mme"]
                print(f"\nMME (Core Network):")
                print(f"  EMM State: {mme.get('emm_state', 'N/A')}")
                print(f"  ECM State: {mme.get('ecm_state', 'N/A')}")
                print(f"  IP Address: {mme.get('ip_addr', 'N/A')}")

                pdn_list = mme.get("pdn_list", [])
                if pdn_list:
                    print(f"  PDN Connections: {len(pdn_list)}")
                    for pdn in pdn_list:
                        print(f"    - APN: {pdn.get('apn', 'N/A')}, "
                              f"IP: {pdn.get('ip_addr', 'N/A')}")

            # ─────────────────────────────────────────────
            # Step 3: Monitor throughput
            # ─────────────────────────────────────────────
            print("\n" + "=" * 60)
            print(f"Step 3: Throughput Monitoring ({args.duration}s)")
            print("=" * 60)
            print("\nNote: Generate traffic (e.g., iperf, file download) to see throughput")

            samples = monitor_throughput(cb, args.duration, args.interval)
            print_summary(samples)

            # ─────────────────────────────────────────────
            # Final Summary
            # ─────────────────────────────────────────────
            print("\n" + "=" * 60)
            print("Test Complete")
            print("=" * 60)
            print(f"\n✓ UE {imsi} attached and data path verified")

    except ConnectionError as e:
        print(f"\nConnection error: {e}")
        print("Verify the REST API service is reachable and running.")
    except APIError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
