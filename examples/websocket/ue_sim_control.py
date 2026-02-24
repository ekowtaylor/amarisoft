#!/usr/bin/env python3
"""UE Simulator power cycling and bearer activation example.

Demonstrates:
- Powering UEs off and on
- Querying simulated UE state
- Activating a dedicated bearer on a simulated UE
"""

import argparse
import time
from pprint import pprint

from client.websocket import Callbox, AmariError, CommandError


def parse_args():
    parser = argparse.ArgumentParser(description="UE Simulator control examples")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl,
                     ssl_verify=args.ssl_verify) as cb:
            # --- Query simulated UEs ---
            print("=" * 60)
            print("UE Simulator — Current UE State")
            print("=" * 60)
            ue_info = cb.ue.ue_get()
            pprint(ue_info)

            # --- Power off all simulated UEs ---
            print("\n" + "=" * 60)
            print("UE Simulator — Power Off All UEs")
            print("=" * 60)
            result = cb.ue.power_off()
            pprint(result)

            # Brief pause to allow state change
            time.sleep(2)

            # --- Check state after power off ---
            print("\n" + "=" * 60)
            print("UE Simulator — State After Power Off")
            print("=" * 60)
            ue_info = cb.ue.ue_get()
            pprint(ue_info)

            # --- Power on all simulated UEs ---
            print("\n" + "=" * 60)
            print("UE Simulator — Power On All UEs")
            print("=" * 60)
            result = cb.ue.power_on()
            pprint(result)

            # Wait for UEs to attach
            time.sleep(5)

            # --- Check state after power on ---
            print("\n" + "=" * 60)
            print("UE Simulator — State After Power On")
            print("=" * 60)
            ue_info = cb.ue.ue_get()
            pprint(ue_info)

            # --- Power cycle a specific UE ---
            ue_list = ue_info.get("ue_list", [])
            if ue_list:
                ue_id = ue_list[0].get("ue_id", 0)
                print(f"\n" + "=" * 60)
                print(f"UE Simulator — Power cycle UE {ue_id}")
                print("=" * 60)
                cb.ue.power_off(ue_id=ue_id)
                time.sleep(2)
                cb.ue.power_on(ue_id=ue_id)
                print(f"UE {ue_id} power cycled.")

            # --- Activate dedicated bearer ---
            print("\n" + "=" * 60)
            print("UE Simulator — Activate Dedicated Bearer")
            print("=" * 60)
            if ue_list:
                ue_id = ue_list[0].get("ue_id", 0)
                try:
                    bearer = cb.ue.ue_activate_dedicated_bearer(
                        ue_id=ue_id,
                        def_bearer_id=5,
                        qci=1,
                    )
                    pprint(bearer)
                except CommandError as e:
                    print(f"Dedicated bearer activation error: {e}")
            else:
                print("No simulated UEs available — skipping bearer activation.")

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
