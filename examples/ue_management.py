#!/usr/bin/env python3
"""UE querying and control example for the Amarisoft Callbox.

Demonstrates:
- Querying UEs from both eNB and MME perspectives
- E-RAB and session/bearer information
- Connected eNB/gNB listing from MME
- RRC connection release
"""

import argparse
from pprint import pprint

from amarisoft import Callbox, AmariError, CommandError


def parse_args():
    parser = argparse.ArgumentParser(description="UE management examples")
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
            # --- UEs from eNB perspective ---
            print("=" * 60)
            print("eNB — Connected UEs")
            print("=" * 60)
            enb_ues = cb.enb.ue_get()
            pprint(enb_ues)

            # --- UEs from MME perspective ---
            print("\n" + "=" * 60)
            print("MME — Registered UEs")
            print("=" * 60)
            mme_ues = cb.mme.ue_get()
            pprint(mme_ues)

            # --- E-RAB information ---
            print("\n" + "=" * 60)
            print("eNB — E-RAB Information")
            print("=" * 60)
            erabs = cb.enb.erab_get()
            pprint(erabs)

            # --- Sessions from MME ---
            print("\n" + "=" * 60)
            print("MME — PDN/PDU Sessions")
            print("=" * 60)
            sessions = cb.mme.session_get()
            pprint(sessions)

            # --- Bearers from MME ---
            print("\n" + "=" * 60)
            print("MME — Bearer Information")
            print("=" * 60)
            bearers = cb.mme.bearer_get()
            pprint(bearers)

            # --- Connected eNBs/gNBs ---
            print("\n" + "=" * 60)
            print("MME — Connected eNBs")
            print("=" * 60)
            try:
                enbs = cb.mme.enb_get()
                pprint(enbs)
            except CommandError as e:
                print(f"enb_get error: {e}")

            print("\n" + "=" * 60)
            print("MME — Connected gNBs")
            print("=" * 60)
            try:
                gnbs = cb.mme.gnb_get()
                pprint(gnbs)
            except CommandError as e:
                print(f"gnb_get error: {e}")

            # --- RRC connection release ---
            # Only release if a UE is connected (use with caution)
            ue_list = enb_ues.get("ue_list", [])
            if ue_list:
                enb_ue_id = ue_list[0].get("enb_ue_id")
                if enb_ue_id is not None:
                    print(f"\n" + "=" * 60)
                    print(f"eNB — RRC release for enb_ue_id={enb_ue_id}")
                    print("=" * 60)
                    try:
                        result = cb.enb.rrc_cnx_release(enb_ue_id)
                        pprint(result)
                    except CommandError as e:
                        print(f"rrc_cnx_release error: {e}")
            else:
                print("\nNo UEs connected — skipping RRC release demo.")

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
