#!/usr/bin/env python3
"""SMS and MMS messaging example for the Amarisoft Callbox.

Demonstrates:
- Sending a text SMS
- Sending a binary SMS (hex payload)
- Sending an MMS with a file attachment
- Flushing the SMS queue
- Querying the MMS server address
"""

import argparse
from pprint import pprint

from client.websocket import Callbox, AmariError, CommandError


def parse_args():
    parser = argparse.ArgumentParser(description="SMS and MMS examples")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    parser.add_argument(
        "--impu", default=None,
        help="Target IMPU for SMS/MMS (auto-detected if omitted)",
    )
    parser.add_argument(
        "--mms-file", default=None,
        help="Path to a file to send as MMS (jpg, png, gif, txt)",
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

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl,
                     ssl_verify=args.ssl_verify) as cb:

            # Determine target IMPU
            impu = args.impu or find_registered_impu(cb)
            if not impu:
                print("No registered IMS user found. Use --impu to specify one.")
                return

            print(f"Target IMPU: {impu}\n")

            # --- Send text SMS ---
            print("=" * 60)
            print("Send Text SMS")
            print("=" * 60)
            try:
                result = cb.ims.send_sms(impu=impu, text="Hello from the API!")
                pprint(result)
            except CommandError as e:
                print(f"send_sms error: {e}")

            # --- Send binary SMS ---
            print("\n" + "=" * 60)
            print("Send Binary SMS (hex payload)")
            print("=" * 60)
            try:
                result = cb.ims.send_sms(
                    impu=impu,
                    binary_hex="48656C6C6F",  # "Hello" in ASCII hex
                )
                pprint(result)
            except CommandError as e:
                print(f"binary send_sms error: {e}")

            # --- Send MMS ---
            if args.mms_file:
                print("\n" + "=" * 60)
                print(f"Send MMS ({args.mms_file})")
                print("=" * 60)

                # Query MMS server address first
                try:
                    mms_srv = cb.ims.mms_server()
                    print("MMS server:")
                    pprint(mms_srv)
                except CommandError as e:
                    print(f"mms_server error: {e}")

                try:
                    result = cb.ims.send_mms(impu=impu, filename=args.mms_file)
                    pprint(result)
                except CommandError as e:
                    print(f"send_mms error: {e}")
            else:
                print("\n(Skipping MMS — use --mms-file to send an MMS)")

            # --- Flush SMS queue ---
            print("\n" + "=" * 60)
            print("Flush SMS Queue")
            print("=" * 60)
            try:
                result = cb.ims.sms_flush()
                pprint(result)
            except CommandError as e:
                print(f"sms_flush error: {e}")

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
