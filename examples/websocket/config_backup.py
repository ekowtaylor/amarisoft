#!/usr/bin/env python3
"""Configuration backup and restore example for the Amarisoft Callbox.

Demonstrates:
- Retrieving configuration from all services via config_get()
- Saving configurations to JSON files
- Restoring a configuration via config_set()
"""

import argparse
import json
import os
from datetime import datetime
from pprint import pprint

from client.websocket import Callbox, AmariError, CommandError


def parse_args():
    parser = argparse.ArgumentParser(description="Backup/restore Callbox configs")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    sub = parser.add_subparsers(dest="action", help="Action to perform")

    sub.add_parser("backup", help="Save current config to files")
    restore_p = sub.add_parser("restore", help="Restore config from a backup file")
    restore_p.add_argument(
        "file", help="Path to a backup JSON file to restore",
    )
    restore_p.add_argument(
        "--service", required=True,
        choices=["enb", "mme", "ims", "ue"],
        help="Service to restore the config to",
    )

    return parser.parse_args()


SERVICES = ["enb", "mme", "ims", "ue"]


def backup(cb, output_dir="."):
    """Retrieve and save configuration from all services."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for name in SERVICES:
        api = getattr(cb, name)
        print(f"Backing up {name} configuration ...")
        try:
            config = api.config_get()
        except CommandError as e:
            print(f"  Skipped {name}: {e}")
            continue

        filename = f"config_{name}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w") as f:
            json.dump(config, f, indent=2)
        print(f"  Saved to {filepath}")


def restore(cb, service, filepath):
    """Restore a configuration from a JSON backup file."""
    api = getattr(cb, service)

    print(f"Loading config from {filepath} ...")
    with open(filepath) as f:
        config = json.load(f)

    # The backup includes metadata fields from config_get; strip them
    # and pass only the config body to config_set.
    # config_get typically returns {"message": "config_get", "config": ...}
    config_body = config.get("config", config)

    print(f"Restoring config to {service} ...")
    pprint(config_body)

    try:
        result = api.config_set(config=config_body)
        print("\nRestore result:")
        pprint(result)
    except CommandError as e:
        print(f"\nRestore error: {e}")


def main():
    args = parse_args()

    if not args.action:
        print("Usage: config_backup.py [backup|restore]")
        print("  backup  — save all service configs to JSON files")
        print("  restore — push a JSON config back to a service")
        return

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl,
                     ssl_verify=args.ssl_verify) as cb:
            if args.action == "backup":
                backup(cb)
            elif args.action == "restore":
                restore(cb, args.service, args.file)
    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
