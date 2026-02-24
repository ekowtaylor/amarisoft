#!/usr/bin/env python3
"""UE attach / detach lifecycle example for the Amarisoft Callbox.

Demonstrates:
- Detaching a UE from the core network (MME)
- Re-attaching by power-cycling the UE simulator
- Monitoring UE state transitions across services
"""

import argparse
import time
from pprint import pprint

from client.websocket import Callbox, AmariError, CommandError


def parse_args():
    parser = argparse.ArgumentParser(description="UE attach/detach lifecycle")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    parser.add_argument(
        "--imsi", default=None,
        help="IMSI of the UE to detach (auto-detected if omitted)",
    )
    return parser.parse_args()


def show_ue_summary(cb, label):
    """Print a brief summary of UE state from both eNB and MME."""
    print(f"\n--- {label} ---")
    enb_ues = cb.enb.ue_get()
    mme_ues = cb.mme.ue_get()
    enb_count = len(enb_ues.get("ue_list", []))
    mme_count = len(mme_ues.get("ue_list", []))
    print(f"  eNB UEs: {enb_count}   MME UEs: {mme_count}")
    return enb_ues, mme_ues


def main():
    args = parse_args()

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl,
                     ssl_verify=args.ssl_verify) as cb:

            # --- Initial state ---
            print("=" * 60)
            print("Initial UE State")
            print("=" * 60)
            enb_ues, mme_ues = show_ue_summary(cb, "Before detach")

            # Find an IMSI to work with
            imsi = args.imsi
            if not imsi:
                ue_list = mme_ues.get("ue_list", [])
                if ue_list:
                    imsi = ue_list[0].get("imsi")
                else:
                    print("No UEs attached. Nothing to detach.")
                    return

            print(f"\nTarget IMSI: {imsi}")

            # --- Detach from MME ---
            print("\n" + "=" * 60)
            print(f"Detaching UE {imsi}")
            print("=" * 60)
            try:
                result = cb.mme.ue_detach(imsi=imsi)
                pprint(result)
            except CommandError as e:
                print(f"ue_detach error: {e}")
                return

            time.sleep(2)
            show_ue_summary(cb, "After detach")

            # --- Power cycle via UE Simulator to re-attach ---
            print("\n" + "=" * 60)
            print("Power cycling UE Simulator to trigger re-attach")
            print("=" * 60)

            # Find the matching ue_id in the UE simulator
            ue_sim = cb.ue.ue_get()
            ue_list = ue_sim.get("ue_list", [])
            target_ue_id = None
            for ue in ue_list:
                if ue.get("imsi") == imsi:
                    target_ue_id = ue.get("ue_id")
                    break

            if target_ue_id is not None:
                print(f"  Power off UE {target_ue_id} ...")
                cb.ue.power_off(ue_id=target_ue_id)
                time.sleep(2)

                print(f"  Power on UE {target_ue_id} ...")
                cb.ue.power_on(ue_id=target_ue_id)
            else:
                # Fallback: power cycle all UEs
                print("  Could not find matching ue_id; cycling all UEs ...")
                cb.ue.power_off()
                time.sleep(2)
                cb.ue.power_on()

            # Wait for re-attach
            print("  Waiting for UE to re-attach ...")
            time.sleep(5)

            # --- Final state ---
            print("\n" + "=" * 60)
            print("Final UE State")
            print("=" * 60)
            show_ue_summary(cb, "After re-attach")

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
