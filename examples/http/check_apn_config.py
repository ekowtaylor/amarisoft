#!/usr/bin/env python3
"""Check APN Configuration via Amarisoft REST API.

This script demonstrates how to check the currently configured APNs
(Access Point Names) on an Amarisoft Callbox using the HTTP REST API.

APNs are configured in the MME (Mobility Management Entity) and define:
- IP address pools for UE connections
- DNS servers
- QoS parameters (QCI, priority)
- PDN type (IPv4, IPv6, or IPv4v6)

Usage:
    python check_apn_config.py [--url URL]

Examples:
    python check_apn_config.py
    python check_apn_config.py --url http://192.168.1.100:9010
"""

from __future__ import annotations

import argparse
from typing import Any

from client.http import APIError, Callbox


def check_apn_via_http(url: str) -> dict[str, Any]:
    """Check APN-related info via HTTP REST API.

    Args:
        url: REST API service URL.

    Returns:
        UE and config information from MME.
    """
    print(f"\n{'='*60}")
    print("CHECKING APN CONFIGURATION VIA HTTP API")
    print(f"{'='*60}")
    print(f"URL: {url}")

    result = {
        "ues": {},
        "config": {},
        "erabs": {},
    }

    with Callbox(url) as cb:
        # Check service status
        print(f"\nService Status: {cb.status}")

        # Get UE info (session_get/bearer_get not supported)
        if cb.status.get("mme"):
            try:
                result["ues"] = cb.mme.ue_get()
            except APIError as e:
                print(f"  UE query error: {e}")

            try:
                result["config"] = cb.mme.config_get()
            except APIError as e:
                print(f"  Config query error: {e}")

        # Get E-RABs from eNB
        if cb.status.get("enb"):
            try:
                result["erabs"] = cb.enb.erab_get()
            except APIError as e:
                print(f"  E-RAB query error: {e}")
        else:
            print("eNB not connected")

    return result


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
        qci = session.get("qci", "N/A")

        print(f"\n  IMSI: {imsi}")
        print(f"  APN:  {apn}")
        print(f"  IP:   {ip}")
        print(f"  QCI:  {qci}")


def display_bearers(bearers: dict[str, Any]) -> None:
    """Display active bearers.

    Args:
        bearers: Bearer data from MME.
    """
    bearer_list = bearers.get("bearer_list", [])

    if not bearer_list:
        print("\nNo active bearers.")
        return

    print(f"\n{'='*60}")
    print("ACTIVE BEARERS")
    print(f"{'='*60}")

    for bearer in bearer_list:
        bearer_id = bearer.get("bearer_id", bearer.get("eps_bearer_id", "N/A"))
        qci = bearer.get("qci", "N/A")
        bearer_type = bearer.get("type", "N/A")

        print(f"\n  Bearer ID: {bearer_id}")
        print(f"  QCI:       {qci}")
        print(f"  Type:      {bearer_type}")


def display_erabs(erabs: dict[str, Any]) -> None:
    """Display E-RAB information.

    Args:
        erabs: E-RAB data from eNB.
    """
    erab_list = erabs.get("erab_list", [])

    if not erab_list:
        print("\nNo active E-RABs.")
        return

    print(f"\n{'='*60}")
    print("ACTIVE E-RABs")
    print(f"{'='*60}")

    for erab in erab_list:
        erab_id = erab.get("erab_id", "N/A")
        qci = erab.get("qci", "N/A")
        enb_ue_id = erab.get("enb_ue_id", "N/A")

        print(f"\n  E-RAB ID:   {erab_id}")
        print(f"  eNB UE ID:  {enb_ue_id}")
        print(f"  QCI:        {qci}")


def display_ue_apn_info(ues: dict[str, Any]) -> None:
    """Display UE information including APNs.

    Args:
        ues: UE data from MME.
    """
    ue_list = ues.get("ue_list", [])

    if not ue_list:
        print("\nNo connected UEs.")
        return

    print(f"\n{'='*60}")
    print("CONNECTED UEs")
    print(f"{'='*60}")

    for ue in ue_list:
        imsi = ue.get("imsi", "N/A")
        emm_state = ue.get("emm_state", "N/A")
        ip_addr = ue.get("ip_addr", "N/A")

        print(f"\n  IMSI:      {imsi}")
        print(f"  EMM State: {emm_state}")
        print(f"  IP:        {ip_addr}")

        # PDN connections
        pdn_list = ue.get("pdn_list", [])
        if pdn_list:
            print(f"  PDN Connections:")
            for pdn in pdn_list:
                apn = pdn.get("apn", "N/A")
                pdn_ip = pdn.get("ip_addr", "N/A")
                print(f"    - APN: {apn}, IP: {pdn_ip}")


def display_config_apns(config: dict[str, Any]) -> None:
    """Display APN configuration from MME config.

    Args:
        config: Config data from MME.
    """
    # The config structure varies by Amarisoft version
    # Look for pdn_list or apn configurations
    pdn_list = config.get("pdn_list", [])

    if not pdn_list:
        print("\nNo APN configuration found in config response.")
        print("(Note: Full pdn_list may require SSH access to config file)")
        return

    print(f"\n{'='*60}")
    print("CONFIGURED APNs (from MME config)")
    print(f"{'='*60}")

    for i, pdn in enumerate(pdn_list, 1):
        name = pdn.get("access_point_name", pdn.get("apn", "unknown"))
        pdn_type = pdn.get("pdn_type", "N/A")
        first_ip = pdn.get("first_ip_addr", "N/A")
        last_ip = pdn.get("last_ip_addr", "N/A")
        dns = pdn.get("dns_addr", "N/A")
        qci = pdn.get("qci", "N/A")

        print(f"\n{i}. APN: {name}")
        print(f"   PDN Type:  {pdn_type}")
        print(f"   IP Range:  {first_ip} - {last_ip}")
        print(f"   DNS:       {dns}")
        print(f"   QCI:       {qci}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check APN configuration via Amarisoft REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Common APNs:
  default   - Generic fallback APN
  internet  - Data/internet traffic
  ims       - VoLTE/IMS services
  sos       - Emergency services

Note: For full APN configuration details (pdn_list), SSH access
to the callbox may be needed to read the MME config file directly.
        """,
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:9010",
        help="REST API service URL (default: http://127.0.0.1:9010)",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout")

    args = parser.parse_args()

    print("=" * 60)
    print("AMARISOFT APN CONFIGURATION CHECK (HTTP)")
    print("=" * 60)
    print(f"Target: {args.url}")

    try:
        # Check via HTTP API
        data = check_apn_via_http(args.url)

        # Display results
        display_ue_apn_info(data["ues"])
        display_erabs(data["erabs"])
        display_config_apns(data["config"])

        print(f"\n{'='*60}")
        print("CHECK COMPLETE")
        print(f"{'='*60}")

    except APIError as e:
        print(f"\nAPI Error: {e}")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify REST API service is running")
        print("  2. Check service URL is correct")
        print("  3. Verify network connectivity")


if __name__ == "__main__":
    main()
