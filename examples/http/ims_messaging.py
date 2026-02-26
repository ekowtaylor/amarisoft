#!/usr/bin/env python3
"""IMS user management, SMS, MMS, and call control example (HTTP).

Demonstrates:
- Querying IMS users and license info
- Sending SMS and flushing the SMS queue
- Querying active dialogs
"""

import argparse
from pprint import pprint

from client.http import APIError, Callbox


def parse_args():
    parser = argparse.ArgumentParser(description="IMS messaging examples (HTTP)")
    parser.add_argument("--url", default="http://127.0.0.1:9010", help="REST API URL")
    parser.add_argument("--api-key", default=None, help="API key for authentication")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        with Callbox(args.url, api_key=args.api_key) as cb:
            # --- IMS info (license may not be supported on all versions) ---
            print("=" * 60)
            print("IMS — Service Information")
            print("=" * 60)
            try:
                lic = cb.ims.license()
                pprint(lic)
            except APIError as e:
                print(f"IMS license() not available: {e}")
                try:
                    help_info = cb.ims.help()
                    print(
                        f"IMS available commands: {len(help_info.get('messages', []))}"
                    )
                except APIError:
                    print("IMS service unavailable")

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
                        sms_result = cb.ims.send_sms(
                            impu=impu, text="Hello from HTTP API!"
                        )
                        pprint(sms_result)
                    except APIError as e:
                        print(f"send_sms error: {e}")

                    # Flush SMS queue
                    print("\n" + "=" * 60)
                    print("IMS — Flush SMS Queue")
                    print("=" * 60)
                    flush = cb.ims.sms_flush()
                    pprint(flush)
            else:
                print("\nNo IMS users found — skipping SMS demo.")

    except APIError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
