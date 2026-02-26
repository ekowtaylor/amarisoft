#!/usr/bin/env python3
"""Bearer management example for the Amarisoft Callbox (HTTP).

Demonstrates:
- Listing current bearers and sessions
- Activating a dedicated bearer for a UE
- Modifying bearer QoS parameters
- Deactivating a bearer
"""

import argparse
import time
from pprint import pprint

from client.http import APIError, Callbox, CapabilityChecker, ValidationError


def parse_args():
    parser = argparse.ArgumentParser(description="Bearer management examples (HTTP)")
    parser.add_argument("--url", default="http://127.0.0.1:9010", help="REST API URL")
    parser.add_argument("--api-key", default=None, help="API key for authentication")
    return parser.parse_args()


def validate_qci(qci, checker=None):
    """Validate QCI and return info about the QCI class."""
    # QCI to name mapping
    qci_info = {
        1: {"name": "Conversational Voice", "type": "GBR"},
        2: {"name": "Conversational Video", "type": "GBR"},
        3: {"name": "Real Time Gaming", "type": "GBR"},
        4: {"name": "Non-Conv Video (Buffered)", "type": "GBR"},
        5: {"name": "IMS Signaling", "type": "Non-GBR"},
        6: {"name": "Video/TCP-based", "type": "Non-GBR"},
        7: {"name": "Voice/Video Gaming", "type": "Non-GBR"},
        8: {"name": "Video/TCP-based", "type": "Non-GBR"},
        9: {"name": "Video/TCP-based (Default)", "type": "Non-GBR"},
    }

    if qci in qci_info:
        return True, qci_info[qci]
    elif 1 <= qci <= 9:
        return True, {"name": "Standard QCI", "type": "unknown"}
    elif 65 <= qci <= 67 or 69 <= qci <= 70 or 75 <= qci <= 82:
        return True, {"name": "Extended QCI", "type": "varies"}
    else:
        return False, f"Invalid QCI: {qci}"


def main():
    args = parse_args()

    try:
        with Callbox(args.url, api_key=args.api_key) as cb:

            # --- UE list and E-RABs (session_get/bearer_get not supported) ---
            print("=" * 60)
            print("MME — UE Information")
            print("=" * 60)
            ues = cb.mme.ue_get()
            pprint(ues)

            print("\n" + "=" * 60)
            print("eNB — E-RAB Information")
            print("=" * 60)
            erabs = cb.enb.erab_get()
            pprint(erabs)

            # --- Find a connected UE to work with ---
            mme_ues = cb.mme.ue_get()
            ue_list = mme_ues.get("ue_list", [])
            if not ue_list:
                print("\nNo UEs attached — cannot demonstrate bearer operations.")
                return

            imsi = ue_list[0].get("imsi")
            print(f"\nWorking with UE IMSI: {imsi}")

            # Also get the enb_ue_id for eNB-side operations
            enb_ues = cb.enb.ue_get()
            enb_ue_list = enb_ues.get("ue_list", [])
            enb_ue_id = None
            if enb_ue_list:
                enb_ue_id = enb_ue_list[0].get("enb_ue_id")

            # --- Activate dedicated bearer with QCI validation ---
            if enb_ue_id is not None:
                print("\n" + "=" * 60)
                print(f"eNB — Activate dedicated bearer (enb_ue_id={enb_ue_id})")
                print("=" * 60)

                # QCI 1 is for GBR conversational voice
                qci = 1
                valid, info = validate_qci(qci)
                if valid:
                    print(
                        f"QCI {qci}: {info.get('name', 'Valid')} ({info.get('type', 'unknown')})"
                    )
                    try:
                        result = cb.enb.ue_activate_dedicated_bearer(
                            enb_ue_id=enb_ue_id,
                            qci=qci,
                        )
                        pprint(result)
                    except APIError as e:
                        print(f"Activation error: {e}")
                else:
                    print(f"Invalid QCI {qci}: {info}")

                time.sleep(2)

                # Show updated E-RAB list
                print("\nE-RABs after activation:")
                pprint(cb.enb.erab_get())

            # --- Modify bearer QoS ---
            print("\n" + "=" * 60)
            print("MME — Modify bearer QoS")
            print("=" * 60)

            # Find an existing erab from eNB E-RABs
            current_erabs = cb.enb.erab_get()
            erab_list = current_erabs.get("erab_list", [])
            if erab_list:
                erab_id = erab_list[0].get("erab_id")
                if erab_id is not None:
                    print(f"Modifying bearer erab_id={erab_id} to QCI=9")
                    try:
                        result = cb.mme.ue_modify_bearer(
                            imsi=imsi,
                            erab_id=erab_id,
                            qci=9,
                        )
                        pprint(result)
                    except APIError as e:
                        print(f"Modify error: {e}")
            else:
                print("No E-RABs found to modify.")

            # --- Deactivate a dedicated bearer ---
            # Only deactivate non-default bearers (erab_id > 5 typically)
            print("\n" + "=" * 60)
            print("MME — Deactivate dedicated bearer")
            print("=" * 60)
            current_erabs = cb.enb.erab_get()
            erab_list = current_erabs.get("erab_list", [])
            dedicated = [b for b in erab_list if b.get("erab_id", 0) > 5]
            if dedicated:
                erab_id = dedicated[0]["erab_id"]
                print(f"Deactivating bearer erab_id={erab_id}")
                try:
                    result = cb.mme.ue_deactivate_bearer(
                        erab_id=erab_id,
                        imsi=imsi,
                    )
                    pprint(result)
                except APIError as e:
                    print(f"Deactivation error: {e}")
            else:
                print("No dedicated bearers to deactivate.")

            # --- Final state ---
            print("\n" + "=" * 60)
            print("Final E-RAB State")
            print("=" * 60)
            pprint(cb.enb.erab_get())

    except APIError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
