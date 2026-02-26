#!/usr/bin/env python3
"""Basic connection example for the Amarisoft HTTP Client.

Demonstrates:
- Callbox constructor and health checks
- Connection status checking
- Version info from each service
- Context manager usage
- Individual API operations

Requirements:
    pip install requests

Usage:
    python basic_connection.py
    python basic_connection.py --url http://192.168.1.80:9010
"""

import argparse
from pprint import pprint

from client.http import (
    APIError,
    Callbox,
    ConnectionError,
    HTTPClientError,
    TimeoutError,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Connect to an Amarisoft Callbox via HTTP REST API"
    )
    parser.add_argument(
        "--url",
        default="http://192.168.1.80:9010",
        help="REST API service URL",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds",
    )
    return parser.parse_args()


def example_health_check(cb: Callbox):
    """Check if the REST API service is healthy."""
    print("=" * 60)
    print("Example 1: Health Check")
    print("=" * 60)

    health = cb.health_check()

    print(f"\nService Status: {health.get('status', 'unknown')}")
    print(f"API Version: {health.get('version', 'unknown')}")

    callbox_info = health.get("callbox", {})
    print(
        f"Connected Services: {callbox_info.get('connected_services', 0)}/{callbox_info.get('total_services', 0)}"
    )

    services = callbox_info.get("services", {})
    for name, info in services.items():
        status = "✓" if info.get("connected") else "✗"
        print(f"  {status} {name}")


def example_version_info(cb: Callbox):
    """Get information from each service using help()."""
    print("\n" + "=" * 60)
    print("Example 2: Service Information")
    print("=" * 60)

    services = [
        ("eNB/gNB", cb.enb),
        ("MME/AMF", cb.mme),
        ("IMS", cb.ims),
        ("UE Simulator", cb.ue),
    ]

    for name, api in services:
        try:
            help_info = api.help()
            messages = help_info.get("messages", [])
            print(f"\n{name}:")
            print(f"  Available commands: {len(messages)}")
        except APIError as e:
            print(f"\n{name}: Not available ({e})")
        except Exception as e:
            print(f"\n{name}: Error - {e}")


def example_context_manager(url: str, timeout: float):
    """Use the Callbox as a context manager."""
    print("\n" + "=" * 60)
    print("Example 3: Context Manager Usage")
    print("=" * 60)

    with Callbox(url, timeout=timeout) as cb:
        print("\nConnected via context manager.")
        print(f"Base URL: {cb.base_url}")

        # Get help for available commands
        try:
            help_info = cb.enb.help()
            commands = help_info.get("commands", [])
            print(f"\neNB available commands: {len(commands)}")
            for cmd in commands[:5]:
                print(f"  - {cmd}")
            if len(commands) > 5:
                print(f"  ... and {len(commands) - 5} more")
        except Exception as e:
            print(f"\nCould not get help: {e}")

    print("\nContext manager exited - connection closed.")


def example_basic_operations(cb: Callbox):
    """Perform basic operations."""
    print("\n" + "=" * 60)
    print("Example 4: Basic Operations")
    print("=" * 60)

    # Get eNB statistics
    print("\neNB Statistics:")
    try:
        stats = cb.enb.stats()
        cells = stats.get("cells", [])
        print(f"  Active cells: {len(cells)}")
        for cell in cells[:3]:
            cell_id = cell.get("cell_id", "?")
            rat = cell.get("rat", "unknown").upper()
            dl = cell.get("dl_bitrate", 0) / 1e6
            ul = cell.get("ul_bitrate", 0) / 1e6
            print(f"    Cell {cell_id}: {rat}, DL={dl:.1f} Mbps, UL={ul:.1f} Mbps")
    except APIError as e:
        print(f"  Error: {e}")

    # Get MME UE list
    print("\nMME UE List:")
    try:
        ue_info = cb.mme.ue_get()
        ue_list = ue_info.get("ue_list", [])
        print(f"  Connected UEs: {len(ue_list)}")
        for ue in ue_list[:3]:
            imsi = ue.get("imsi", "N/A")
            state = ue.get("state", "unknown")
            print(f"    IMSI: {imsi}, State: {state}")
    except APIError as e:
        print(f"  Error: {e}")

    # Get eNB configuration
    print("\neNB Configuration:")
    try:
        config = cb.enb.config_get()
        print(f"  Config keys: {list(config.keys())[:5]}...")
    except APIError as e:
        print(f"  Error: {e}")


def example_error_handling(cb: Callbox):
    """Demonstrate error handling."""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)

    print("\nTesting error handling with invalid operation:")

    try:
        # Try to access a non-existent endpoint
        cb._client.get("/invalid/endpoint")
        print("  Unexpected success!")
    except APIError as e:
        print(f"  ✓ Caught APIError: {e}")
    except HTTPClientError as e:
        print(f"  ✓ Caught HTTPClientError: {e}")

    print("\nError handling works correctly.")


def main():
    args = parse_args()

    print("\n" + "=" * 60)
    print("  AMARISOFT HTTP CLIENT - Basic Connection Examples")
    print("=" * 60)
    print(f"  Target: {args.url}")
    print()

    try:
        # Create the callbox client
        cb = Callbox(args.url, timeout=args.timeout)

        try:
            example_health_check(cb)
            example_version_info(cb)
            example_context_manager(args.url, args.timeout)
            example_basic_operations(cb)
            example_error_handling(cb)

            print("\n" + "=" * 60)
            print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
            print("=" * 60)

        finally:
            cb.close()

    except ConnectionError as e:
        print(f"\n✗ Connection error: {e}")
        print(f"\nMake sure the REST API service is running at {args.url}")
        print("Deploy the service using: service/deploy.sh")

    except TimeoutError as e:
        print(f"\n✗ Timeout: {e}")

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
