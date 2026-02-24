#!/usr/bin/env python3
"""Basic HTTP REST API Examples.

Demonstrates basic usage of the Amarisoft REST API service.

Requirements:
    pip install requests

Usage:
    python basic_usage.py
"""

import requests

# Configuration
BASE_URL = "http://192.168.1.80:9010"


def check_health():
    """Check if the REST API service is healthy."""
    print("=" * 60)
    print("Health Check")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/health")
    data = response.json()

    print(f"Status: {data['status']}")
    print(f"Version: {data['version']}")
    print(f"Connected Services: {data['callbox']['connected_services']}/{data['callbox']['total_services']}")
    print()


def get_version():
    """Get version information for all services."""
    print("=" * 60)
    print("Version Information")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/version")
    data = response.json()

    print(f"API Version: {data['api_version']}")
    for name, info in data.get("services", {}).items():
        status = "✓" if info["connected"] else "✗"
        version = info["version"] or "N/A"
        print(f"  {status} {name}: {version}")
    print()


def connect_all_services():
    """Connect to all backend services."""
    print("=" * 60)
    print("Connecting to All Services")
    print("=" * 60)

    response = requests.post(f"{BASE_URL}/services/connect")
    data = response.json()

    print(f"Action: {data['action']}")
    print(f"Healthy: {data['healthy']}")
    for name, svc in data.get("services", {}).items():
        status = "✓" if svc["connected"] else "✗"
        print(f"  {status} {name}")
    print()


def get_enb_stats():
    """Get eNB/gNB statistics."""
    print("=" * 60)
    print("eNB/gNB Statistics")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/enb/stats")

    if response.status_code == 200:
        data = response.json()
        cells = data.get("cells", {})
        print(f"Active Cells: {len(cells)}")
        for cell_id, cell_data in cells.items():
            rat = cell_data.get("rat", "unknown").upper()
            dl = cell_data.get("dl_bitrate", 0) / 1e6
            ul = cell_data.get("ul_bitrate", 0) / 1e6
            print(f"  Cell {cell_id}: {rat}, DL={dl:.1f} Mbps, UL={ul:.1f} Mbps")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
    print()


def list_connected_ues():
    """List UEs connected via MME."""
    print("=" * 60)
    print("Connected UEs (MME)")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/mme/ue")

    if response.status_code == 200:
        data = response.json()
        ue_list = data.get("ue_list", [])
        print(f"Total UEs: {len(ue_list)}")
        for ue in ue_list:
            imsi = ue.get("imsi", "N/A")
            state = ue.get("state", "unknown")
            print(f"  IMSI: {imsi}, State: {state}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  AMARISOFT REST API - Basic Usage Examples")
    print("=" * 60)
    print(f"  Target: {BASE_URL}")
    print()

    try:
        check_health()
        get_version()
        connect_all_services()
        get_enb_stats()
        list_connected_ues()

    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to {BASE_URL}")
        print("Make sure the REST API service is running on the callbox.")


if __name__ == "__main__":
    main()
