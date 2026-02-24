#!/usr/bin/env python3
"""UE attach / detach lifecycle example for the Amarisoft Callbox (HTTP).

Demonstrates:
- Detaching a UE from the core network (MME)
- Re-attaching by power-cycling the UE simulator
- Monitoring UE state transitions across services
"""

import argparse
import time
from pprint import pprint

from client.http import Callbox, APIError


def parse_args():
    parser = argparse.ArgumentParser(description="UE attach/detach lifecycle (HTTP)")
    parser.add_argument("--url", default="http://127.0.0.1:9010", help="REST API URL")
    parser.add_argument("--api-key", default=None, help="API key for authentication")
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
        with Callbox(args.url, api_key=args.api_key) as cb:

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
            except APIError as e:
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

    except APIError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
