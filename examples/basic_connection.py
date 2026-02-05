#!/usr/bin/env python3
"""Basic connection example for the Amarisoft Callbox.

Demonstrates:
- Callbox constructor and connect_all()
- Connection status checking
- Version info from each service
- Context manager usage
- Individual service connections
"""

import argparse
from pprint import pprint

from amarisoft import (
    Callbox,
    AmariConnectionError,
    AmariTimeoutError,
    AuthenticationError,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Connect to an Amarisoft Callbox")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    return parser.parse_args()


def example_connect_all(host, password, ssl):
    """Connect to all services at once and print status."""
    print("=" * 60)
    print("Example 1: connect_all()")
    print("=" * 60)

    cb = Callbox(host, password=password, ssl=ssl)
    try:
        ready = cb.connect_all()
        print("\nReady messages from each service:")
        pprint(ready)

        print("\nConnection status:")
        pprint(cb.status)

        # Get version from each service
        for name, api in [("eNB", cb.enb), ("MME", cb.mme),
                          ("IMS", cb.ims), ("UE", cb.ue)]:
            version = api.version()
            print(f"\n{name} version:")
            pprint(version)
    finally:
        cb.close()
        print("\nAll connections closed.")


def example_context_manager(host, password, ssl):
    """Use the Callbox as a context manager."""
    print("\n" + "=" * 60)
    print("Example 2: Context manager usage")
    print("=" * 60)

    with Callbox(host, password=password, ssl=ssl) as cb:
        print("\nConnected via context manager.")
        print("Status:", cb.status)

        # Call help() to list available commands on eNB
        print("\neNB available commands:")
        pprint(cb.enb.help())

    print("Context manager exited — connections closed automatically.")


def example_individual_connections(host, password, ssl):
    """Connect to services one at a time."""
    print("\n" + "=" * 60)
    print("Example 3: Individual service connections")
    print("=" * 60)

    cb = Callbox(host, password=password, ssl=ssl)
    try:
        # Connect only to the eNB
        enb_ready = cb.connect_enb()
        print("\neNB ready message:")
        pprint(enb_ready)

        # Connect only to the MME
        mme_ready = cb.connect_mme()
        print("\nMME ready message:")
        pprint(mme_ready)

        print("\nPartial connection status:")
        pprint(cb.status)
    finally:
        cb.close()


def main():
    args = parse_args()

    try:
        example_connect_all(args.host, args.password, args.ssl)
        example_context_manager(args.host, args.password, args.ssl)
        example_individual_connections(args.host, args.password, args.ssl)
    except AuthenticationError as e:
        print(f"\nAuthentication failed: {e}")
        print("Check the --password argument.")
    except AmariConnectionError as e:
        print(f"\nConnection error: {e}")
        print("Verify the Callbox is reachable at the given --host.")
    except AmariTimeoutError as e:
        print(f"\nTimeout: {e}")


if __name__ == "__main__":
    main()
