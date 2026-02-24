#!/usr/bin/env python3
"""Bearer management example for the Amarisoft Callbox.

Demonstrates:
- Listing current bearers and sessions
- Activating a dedicated bearer for a UE
- Modifying bearer QoS parameters
- Deactivating a bearer
"""

import argparse
import time
from pprint import pprint

from client.websocket import (
    Callbox,
    AmariError,
    CommandError,
    InvalidParameterError,
    CapabilityChecker,
    get_default_capabilities,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Bearer management examples")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    return parser.parse_args()


def validate_qci(qci, checker=None):
    """Validate QCI and return info about the QCI class."""
    if checker is None:
        checker = CapabilityChecker(get_default_capabilities())

    try:
        checker.validate_qci(qci)
        info = checker.get_qci_info(qci)
        return True, info
    except InvalidParameterError as e:
        return False, str(e)


def main():
    args = parse_args()

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl,
                     ssl_verify=args.ssl_verify) as cb:

            # --- Current sessions and bearers ---
            print("=" * 60)
            print("MME — Current Sessions")
            print("=" * 60)
            sessions = cb.mme.session_get()
            pprint(sessions)

            print("\n" + "=" * 60)
            print("MME — Current Bearers")
            print("=" * 60)
            bearers = cb.mme.bearer_get()
            pprint(bearers)

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

                # Create checker for QCI validation
                checker = CapabilityChecker(get_default_capabilities())

                # QCI 1 is for GBR conversational voice
                qci = 1
                valid, info = validate_qci(qci, checker)
                if valid:
                    print(f"QCI {qci}: {info.get('name', 'Valid')} ({info.get('type', 'unknown')})")
                    try:
                        result = cb.enb.ue_activate_dedicated_bearer(
                            enb_ue_id=enb_ue_id, qci=qci,
                        )
                        pprint(result)
                    except CommandError as e:
                        print(f"Activation error: {e}")
                else:
                    print(f"Invalid QCI {qci}: {info}")

                time.sleep(2)

                # Show updated bearer list
                print("\nBearers after activation:")
                pprint(cb.mme.bearer_get())

            # --- Modify bearer QoS ---
            print("\n" + "=" * 60)
            print("MME — Modify bearer QoS")
            print("=" * 60)

            # Find an existing erab_id to modify
            current_bearers = cb.mme.bearer_get()
            bearer_list = current_bearers.get("bearer_list", [])
            if bearer_list:
                erab_id = bearer_list[0].get("erab_id")
                if erab_id is not None:
                    print(f"Modifying bearer erab_id={erab_id} to QCI=9")
                    try:
                        result = cb.mme.ue_modify_bearer(
                            imsi=imsi, erab_id=erab_id, qci=9,
                        )
                        pprint(result)
                    except CommandError as e:
                        print(f"Modify error: {e}")
            else:
                print("No bearers found to modify.")

            # --- Deactivate a dedicated bearer ---
            # Only deactivate non-default bearers (erab_id > 5 typically)
            print("\n" + "=" * 60)
            print("MME — Deactivate dedicated bearer")
            print("=" * 60)
            current_bearers = cb.mme.bearer_get()
            bearer_list = current_bearers.get("bearer_list", [])
            dedicated = [b for b in bearer_list
                         if b.get("erab_id", 0) > 5]
            if dedicated:
                erab_id = dedicated[0]["erab_id"]
                print(f"Deactivating bearer erab_id={erab_id}")
                try:
                    result = cb.mme.ue_deactivate_bearer(
                        erab_id=erab_id, imsi=imsi,
                    )
                    pprint(result)
                except CommandError as e:
                    print(f"Deactivation error: {e}")
            else:
                print("No dedicated bearers to deactivate.")

            # --- Final state ---
            print("\n" + "=" * 60)
            print("Final Bearer State")
            print("=" * 60)
            pprint(cb.mme.bearer_get())

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
