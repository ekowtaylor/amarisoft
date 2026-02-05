#!/usr/bin/env python3
"""Event listener example for the Amarisoft Callbox.

Demonstrates:
- Registering for constellation/channel data
- Listening for unsolicited events with a callback
- Unregistering from channels
"""

import argparse
from pprint import pprint

from amarisoft import Callbox, AmariError, CommandError


def parse_args():
    parser = argparse.ArgumentParser(description="Listen for Callbox events")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    parser.add_argument(
        "--duration", type=float, default=10.0,
        help="Seconds to listen for events (default: 10)",
    )
    parser.add_argument(
        "--channel", default="pusch",
        help="Channel to register for (default: pusch)",
    )
    return parser.parse_args()


def on_event(message):
    """Callback invoked for each unsolicited message.

    Return True to stop listening early, or None/False to continue.
    """
    msg_type = message.get("message", "unknown")
    print(f"\n--- Event received: {msg_type} ---")
    pprint(message)
    # Return False to keep listening; return True to stop early.
    return False


def main():
    args = parse_args()

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl,
                     ssl_verify=args.ssl_verify) as cb:
            # Register for channel constellation data
            print(f"Registering for channel: {args.channel}")
            try:
                reg = cb.enb.register_channel(args.channel)
                pprint(reg)
            except CommandError as e:
                print(f"register_channel error: {e}")
                return

            # Listen for unsolicited events
            print(f"\nListening for events for {args.duration}s ...")
            print("(Press Ctrl+C to stop early)\n")

            try:
                cb.enb._client.listen(on_event, duration=args.duration)
            except KeyboardInterrupt:
                print("\nInterrupted by user.")

            # Unregister from the channel
            print(f"\nUnregistering from channel: {args.channel}")
            try:
                unreg = cb.enb.unregister_channel(args.channel)
                pprint(unreg)
            except CommandError as e:
                print(f"unregister_channel error: {e}")

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
