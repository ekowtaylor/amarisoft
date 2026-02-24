#!/usr/bin/env python3
"""Voice call control example for the Amarisoft Callbox.

Demonstrates:
- Initiating a mobile-terminated (MT) call via IMS
- Monitoring call dialogs
- Answering and terminating calls via dialog_set
- Registering for call events
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
    parser = argparse.ArgumentParser(description="IMS call control examples")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    parser.add_argument(
        "--impu", default=None,
        help="IMPU to call (e.g. sip:0001@ims.mnc001.mcc001.3gppnetwork.org)",
    )
    return parser.parse_args()


def find_registered_impu(cb):
    """Return the first registered IMPU, or None."""
    users = cb.ims.users_get(registered_only=True)
    user_list = users.get("user_list", [])
    if user_list:
        return user_list[0].get("impu")
    return None


def main():
    args = parse_args()

    # Pre-validate IMS service and VoLTE feature requirement
    checker = CapabilityChecker(get_default_capabilities())
    print("=" * 60)
    print("Pre-flight checks for VoLTE call")
    print("=" * 60)

    try:
        checker.validate_service_available("ims")
        print("  ✓ IMS service expected to be available")
    except InvalidParameterError as e:
        print(f"  ⚠ Warning: {e}")
        print("    IMS may not be connected on this device")

    try:
        checker.validate_feature("volte")
        print("  ✓ VoLTE feature expected to be enabled")
    except InvalidParameterError as e:
        print(f"  ⚠ Warning: {e}")
        print("    VoLTE calls may not be supported")

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl,
                     ssl_verify=args.ssl_verify) as cb:

            # Verify IMS is actually connected
            if not cb.status.get("ims", False):
                print("\n⚠ Warning: IMS service not connected!")
                print("  VoLTE calls require IMS. Check your configuration.")
                print("  Note: IMS may be on port 9003 instead of default 9002")
                print("  Try: Callbox(host, ims_port=9003)")

            # Register for call/dialog events so we receive updates
            print("\nRegistering for dialog events ...")
            try:
                cb.ims.register_events("dialog")
            except CommandError as e:
                print(f"register_events warning: {e}")

            # Determine target IMPU
            impu = args.impu or find_registered_impu(cb)
            if not impu:
                print("No registered IMS user found. Use --impu to specify one.")
                return

            print(f"Target IMPU: {impu}")

            # --- Initiate MT call ---
            print("\n" + "=" * 60)
            print("Initiating MT call")
            print("=" * 60)
            try:
                result = cb.ims.mt_call(impu)
                pprint(result)
            except CommandError as e:
                print(f"mt_call error: {e}")
                return

            # Wait for the call to set up
            time.sleep(3)

            # --- Check dialog state ---
            print("\n" + "=" * 60)
            print("Current dialogs")
            print("=" * 60)
            dialogs = cb.ims.dialog_get()
            pprint(dialogs)

            dialog_list = dialogs.get("dialog_list", [])
            if not dialog_list:
                print("No active dialogs found.")
                return

            session_id = dialog_list[0].get("session_id")
            if not session_id:
                print("Could not find session_id in dialog.")
                return

            print(f"\nActive session: {session_id}")

            # --- Answer the call ---
            print("\n" + "=" * 60)
            print(f"Answering call {session_id}")
            print("=" * 60)
            try:
                answer = cb.ims.dialog_set(session_id, action="answer")
                pprint(answer)
            except CommandError as e:
                print(f"answer error: {e}")

            # Let the call run briefly
            time.sleep(3)

            # --- Check dialog state during call ---
            print("\n" + "=" * 60)
            print("Dialog state during call")
            print("=" * 60)
            pprint(cb.ims.dialog_get(session_id=session_id))

            # --- Terminate the call ---
            print("\n" + "=" * 60)
            print(f"Terminating call {session_id}")
            print("=" * 60)
            try:
                stop = cb.ims.dialog_set(session_id, action="stop")
                pprint(stop)
            except CommandError as e:
                print(f"stop error: {e}")

            time.sleep(1)

            # --- Verify call is gone ---
            print("\n" + "=" * 60)
            print("Dialogs after termination")
            print("=" * 60)
            pprint(cb.ims.dialog_get())

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
