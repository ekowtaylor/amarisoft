#!/usr/bin/env python3
"""UE attach and data test example for the Amarisoft Callbox.

Demonstrates:
- Powering on UE and waiting for attachment
- Verifying UE is connected (RRC, EMM, PDN states)
- Monitoring throughput during data transfer
- Running ping tests via SSH
- Collecting UE statistics and signal quality
"""

import argparse
import time

from amarisoft import (
    Callbox,
    AmariError,
    CommandError,
    AmariConnectionError,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Attach UE and perform data test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic attach and monitor
  python ue_data_test.py --host 192.168.1.80

  # With SSH for ping test
  python ue_data_test.py --host 192.168.1.80 --ssh-password toor --ping-target 8.8.8.8

  # Monitor throughput for 30 seconds
  python ue_data_test.py --host 192.168.1.80 --duration 30
        """,
    )
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="WebSocket auth password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates",
    )
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
    parser.add_argument(
        "--ssh-user", default="root",
        help="SSH username for ping tests (default: root)",
    )
    parser.add_argument(
        "--ssh-password", default=None,
        help="SSH password (enables ping test if provided)",
    )
    parser.add_argument(
        "--ping-target", default="8.8.8.8",
        help="Target IP for ping test (default: 8.8.8.8)",
    )
    parser.add_argument(
        "--ping-count", type=int, default=5,
        help="Number of ping packets (default: 5)",
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
            for ue in ue_list:
                fiveg_state = ue.get("5g_mm_state", "")
                if fiveg_state in ("registered", "connected"):
                    if ue_id is None or ue.get("ue_id") == ue_id:
                        print(f"  ✓ UE attached (5G): IMSI={ue.get('imsi')}, "
                              f"5G-MM={fiveg_state}")
                        return ue

        except CommandError as e:
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
    except CommandError:
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
    except CommandError:
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
    except CommandError:
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

        except CommandError as e:
            print(f"  Stats error: {e}")

        time.sleep(interval)

    return samples


def run_ping_test(cb, ssh_user, ssh_password, target, count):
    """Run ping test via SSH.

    Args:
        cb: Callbox instance
        ssh_user: SSH username
        ssh_password: SSH password
        target: Target IP to ping
        count: Number of ping packets

    Returns:
        dict with ping results
    """
    print(f"\nRunning ping test to {target}...")

    try:
        from amarisoft import SSHClient

        ssh = SSHClient(
            host=cb._enb_client.host if cb._enb_client else "127.0.0.1",
            username=ssh_user,
            password=ssh_password,
        )
        ssh.connect()

        result = ssh.ping(target, count=count)
        ssh.close()

        return result

    except ImportError:
        print("  SSH client not available")
        return None
    except Exception as e:
        print(f"  Ping failed: {e}")
        return None


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
    print("UE Attach and Data Test")
    print("=" * 60)
    print(f"Host: {args.host}")

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl,
                     ssl_verify=args.ssl_verify) as cb:

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
            except CommandError:
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
            # Step 4: Get detailed UE info
            # ─────────────────────────────────────────────
            print("\n" + "=" * 60)
            print("Step 4: UE Connection Details")
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
            # Step 5: Run ping test (if SSH enabled)
            # ─────────────────────────────────────────────
            if args.ssh_password:
                print("\n" + "=" * 60)
                print("Step 5: Ping Test")
                print("=" * 60)

                ping_result = run_ping_test(
                    cb, args.ssh_user, args.ssh_password,
                    args.ping_target, args.ping_count
                )

                if ping_result:
                    print(f"\nPing to {args.ping_target}:")
                    print(f"  Packets: {ping_result.get('transmitted', 0)} sent, "
                          f"{ping_result.get('received', 0)} received")
                    print(f"  Loss: {ping_result.get('loss_percent', 100):.1f}%")
                    if ping_result.get("avg_ms"):
                        print(f"  RTT: min={ping_result.get('min_ms', 0):.1f}ms, "
                              f"avg={ping_result.get('avg_ms', 0):.1f}ms, "
                              f"max={ping_result.get('max_ms', 0):.1f}ms")

            # ─────────────────────────────────────────────
            # Step 6: Monitor throughput
            # ─────────────────────────────────────────────
            print("\n" + "=" * 60)
            print(f"Step 6: Throughput Monitoring ({args.duration}s)")
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

    except AmariConnectionError as e:
        print(f"\nConnection error: {e}")
        print("Verify the Callbox is reachable and services are running.")
    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
