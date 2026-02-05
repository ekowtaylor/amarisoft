#!/usr/bin/env python3
"""IMS user management, SMS, MMS, and call control example.

Demonstrates:
- Querying IMS users and license info
- Sending SMS and flushing the SMS queue
- Querying active dialogs
- Registering for IMS events
"""

import argparse
from pprint import pprint

from amarisoft import Callbox, AmariError, CommandError


def parse_args():
    parser = argparse.ArgumentParser(description="IMS messaging examples")
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
            # --- IMS license info ---
            print("=" * 60)
            print("IMS — License Information")
            print("=" * 60)
            lic = cb.ims.license()
            pprint(lic)

            # --- IMS users ---
            print("\n" + "=" * 60)
            print("IMS — All Users")
            print("=" * 60)
            users = cb.ims.users_get()
            pprint(users)

            print("\n" + "=" * 60)
            print("IMS — Registered Users Only")
            print("=" * 60)
            registered = cb.ims.users_get(registered_only=True)
            pprint(registered)

            # --- Active dialogs ---
            print("\n" + "=" * 60)
            print("IMS — Active Dialogs")
            print("=" * 60)
            dialogs = cb.ims.dialog_get()
            pprint(dialogs)

            # --- Send SMS ---
            # Requires at least one registered user
            user_list = users.get("user_list") or registered.get("user_list") or []
            if user_list:
                impu = user_list[0].get("impu", "")
                if impu:
                    print(f"\n" + "=" * 60)
                    print(f"IMS — Send SMS to {impu}")
                    print("=" * 60)
                    try:
                        sms_result = cb.ims.send_sms(impu=impu, text="Hello from API!")
                        pprint(sms_result)
                    except CommandError as e:
                        print(f"send_sms error: {e}")

                    # Flush SMS queue
                    print("\n" + "=" * 60)
                    print("IMS — Flush SMS Queue")
                    print("=" * 60)
                    flush = cb.ims.sms_flush()
                    pprint(flush)
            else:
                print("\nNo IMS users found — skipping SMS demo.")

            # --- Register for events ---
            print("\n" + "=" * 60)
            print("IMS — Register for Events")
            print("=" * 60)
            try:
                events = cb.ims.register_events("sms", "call")
                pprint(events)
            except CommandError as e:
                print(f"register_events error: {e}")

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
