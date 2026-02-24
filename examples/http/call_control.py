#!/usr/bin/env python3
"""Voice call control example for the Amarisoft Callbox (HTTP).

Demonstrates:
- Initiating a mobile-terminated (MT) call via IMS
- Monitoring call dialogs
- Answering and terminating calls via dialog_set
"""

import argparse
import time
from pprint import pprint

from client.http import Callbox, APIError


def parse_args():
    parser = argparse.ArgumentParser(description="IMS call control examples (HTTP)")
    parser.add_argument("--url", default="http://127.0.0.1:9010", help="REST API URL")
    parser.add_argument("--api-key", default=None, help="API key for authentication")
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

    print("=" * 60)
    print("Pre-flight checks for VoLTE call")
    print("=" * 60)

    try:
        with Callbox(args.url, api_key=args.api_key) as cb:

            # Check health
            health = cb.health_check()
            if health.get("status") == "healthy":
                print("  ✓ REST API service is healthy")
            else:
                print("  ⚠ REST API service status:", health)

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
            except APIError as e:
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
            except APIError as e:
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
            except APIError as e:
                print(f"stop error: {e}")

            time.sleep(1)

            # --- Verify call is gone ---
            print("\n" + "=" * 60)
            print("Dialogs after termination")
            print("=" * 60)
            pprint(cb.ims.dialog_get())

    except APIError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
