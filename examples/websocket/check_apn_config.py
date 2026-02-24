#!/usr/bin/env python3
"""Check APN Configuration on Amarisoft Callbox.

This script demonstrates how to check the currently configured APNs
(Access Point Names) on an Amarisoft Callbox using both SSH and WebSocket APIs.

APNs are configured in the MME (Mobility Management Entity) and define:
- IP address pools for UE connections
- DNS servers
- QoS parameters (QCI, priority)
- PDN type (IPv4, IPv6, or IPv4v6)

Usage:
    python check_apn_config.py [--host HOST] [--password PASSWORD]

Examples:
    python check_apn_config.py
    python check_apn_config.py --host 192.168.1.100
    python check_apn_config.py --host 192.168.1.80 --password mypassword

Manual SSH Check:
    ssh root@<CALLBOX_IP>  # Password: toor
    grep -A 50 "pdn_list" /root/mme/config/mme.cfg
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

# Add parent directory to path for development
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from client.websocket import Callbox, SSHClient


def parse_pdn_list(config_text: str) -> list[dict[str, Any]]:
    """Parse pdn_list from MME config text.

    Args:
        config_text: Raw config file content.

    Returns:
        List of parsed APN configurations.
    """
    apns = []

    # Find pdn_list section
    pdn_match = re.search(r"pdn_list:\s*\[", config_text)
    if not pdn_match:
        return apns

    # Extract the pdn_list array content
    start = pdn_match.end()
    bracket_count = 1
    end = start

    for i, char in enumerate(config_text[start:], start):
        if char == "[":
            bracket_count += 1
        elif char == "]":
            bracket_count -= 1
            if bracket_count == 0:
                end = i
                break

    pdn_content = config_text[start:end]

    # Parse individual APN entries
    # Split by closing brace followed by comma or end
    entries = re.split(r"\},?\s*(?=\{|$)", pdn_content)

    for entry in entries:
        entry = entry.strip()
        if not entry or entry == "{":
            continue

        apn = {}

        # Extract key fields
        patterns = {
            "access_point_name": r'access_point_name:\s*"([^"]+)"',
            "pdn_type": r'pdn_type:\s*"([^"]+)"',
            "first_ip_addr": r'first_ip_addr:\s*"([^"]+)"',
            "last_ip_addr": r'last_ip_addr:\s*"([^"]+)"',
            "dns_addr": r'dns_addr:\s*"([^"]+)"',
            "ip_addr_shift": r"ip_addr_shift:\s*(\d+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, entry)
            if match:
                apn[key] = match.group(1)

        # Extract QCI if present
        qci_match = re.search(r"qci:\s*(\d+)", entry)
        if qci_match:
            apn["qci"] = int(qci_match.group(1))

        if apn:
            apns.append(apn)

    return apns


def check_apn_via_ssh(host: str, password: str = "toor") -> list[dict[str, Any]]:
    """Check APN configuration via SSH.

    Args:
        host: Callbox IP address.
        password: SSH password (default: toor).

    Returns:
        List of parsed APN configurations.
    """
    print(f"\n{'='*60}")
    print("CHECKING APN CONFIGURATION VIA SSH")
    print(f"{'='*60}")
    print(f"Host: {host}")

    with SSHClient(host, password=password) as ssh:
        print(f"Connected to: {ssh.get_hostname()}")

        # Read MME config file
        config = ssh._run_command("cat /root/mme/config/mme.cfg 2>/dev/null")

        if not config:
            print("Warning: Could not read MME config file")
            return []

        # Parse APNs
        apns = parse_pdn_list(config)

        return apns


def check_apn_via_websocket(host: str) -> dict[str, Any]:
    """Check APN-related info via WebSocket API.

    Note: The WebSocket API doesn't directly expose pdn_list,
    but we can get session/bearer info for connected UEs.

    Args:
        host: Callbox IP address.

    Returns:
        Session information from MME.
    """
    print(f"\n{'='*60}")
    print("CHECKING ACTIVE SESSIONS VIA WEBSOCKET")
    print(f"{'='*60}")

    with Callbox(host) as cb:
        # Get active sessions (shows APNs in use by connected UEs)
        if cb.status.get("mme"):
            sessions = cb.mme.session_get()
            return sessions
        else:
            print("MME not connected")
            return {}


def display_apn_config(apns: list[dict[str, Any]]) -> None:
    """Display APN configuration in a formatted table.

    Args:
        apns: List of APN configurations.
    """
    if not apns:
        print("\nNo APNs found in configuration.")
        return

    print(f"\n{'='*60}")
    print("CONFIGURED APNs")
    print(f"{'='*60}")

    for i, apn in enumerate(apns, 1):
        name = apn.get("access_point_name", "unknown")
        pdn_type = apn.get("pdn_type", "N/A")
        first_ip = apn.get("first_ip_addr", "N/A")
        last_ip = apn.get("last_ip_addr", "N/A")
        dns = apn.get("dns_addr", "N/A")
        qci = apn.get("qci", "N/A")

        print(f"\n{i}. APN: {name}")
        print(f"   PDN Type:  {pdn_type}")
        print(f"   IP Range:  {first_ip} - {last_ip}")
        print(f"   DNS:       {dns}")
        print(f"   QCI:       {qci}")


def display_active_sessions(sessions: dict[str, Any]) -> None:
    """Display active PDN sessions.

    Args:
        sessions: Session data from MME.
    """
    session_list = sessions.get("session_list", sessions.get("pdn_list", []))

    if not session_list:
        print("\nNo active PDN sessions.")
        return

    print(f"\n{'='*60}")
    print("ACTIVE PDN SESSIONS")
    print(f"{'='*60}")

    for session in session_list:
        imsi = session.get("imsi", "N/A")
        apn = session.get("apn", session.get("access_point_name", "N/A"))
        ip = session.get("ip_addr", session.get("pdn_addr", "N/A"))

        print(f"\n  IMSI: {imsi}")
        print(f"  APN:  {apn}")
        print(f"  IP:   {ip}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check APN configuration on Amarisoft Callbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Common APNs:
  default   - Generic fallback APN
  internet  - Data/internet traffic
  ims       - VoLTE/IMS services
  sos       - Emergency services

Manual SSH Check:
  ssh root@<CALLBOX_IP>  # Password: toor
  grep -A 50 "pdn_list" /root/mme/config/mme.cfg
        """,
    )
    parser.add_argument(
        "--host",
        default="192.168.1.80",
        help="Callbox IP address (default: 192.168.1.80)",
    )
    parser.add_argument(
        "--password",
        default="toor",
        help="SSH password (default: toor)",
    )
    parser.add_argument(
        "--ssh-only",
        action="store_true",
        help="Only check via SSH (skip WebSocket)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show raw pdn_list from config file",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("AMARISOFT APN CONFIGURATION CHECK")
    print("=" * 60)
    print(f"Target: {args.host}")

    try:
        # Check via SSH (primary method for config)
        apns = check_apn_via_ssh(args.host, args.password)
        display_apn_config(apns)

        # Show raw config if requested
        if args.raw:
            print(f"\n{'='*60}")
            print("RAW PDN_LIST FROM CONFIG")
            print(f"{'='*60}")
            with SSHClient(args.host, password=args.password) as ssh:
                raw = ssh._run_command(
                    "grep -A 50 pdn_list /root/mme/config/mme.cfg 2>/dev/null"
                )
                print(raw)

        # Check active sessions via WebSocket
        if not args.ssh_only:
            try:
                sessions = check_apn_via_websocket(args.host)
                display_active_sessions(sessions)
            except Exception as e:
                print(f"\nWebSocket check skipped: {e}")

        print(f"\n{'='*60}")
        print("CHECK COMPLETE")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify callbox is reachable: ping", args.host)
        print("  2. Check SSH access: ssh root@" + args.host)
        print("  3. Default password is 'toor'")
        sys.exit(1)


if __name__ == "__main__":
    main()
