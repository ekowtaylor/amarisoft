#!/usr/bin/env python3
"""UE Management via HTTP REST API.

Demonstrates UE management operations using the REST API.

Requirements:
    pip install requests

Usage:
    python ue_management.py
"""

import requests

# Configuration
BASE_URL = "http://192.168.1.80:9010"


def list_ues_enb():
    """List UEs connected to the eNB/gNB."""
    print("=" * 60)
    print("UEs Connected to eNB/gNB")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/enb/ue")

    if response.status_code == 200:
        data = response.json()
        ue_list = data.get("ue_list", [])
        print(f"Total UEs: {len(ue_list)}")
        for ue in ue_list:
            print(f"  eNB UE ID: {ue.get('enb_ue_id', 'N/A')}")
            print(f"    IMSI: {ue.get('imsi', 'N/A')}")
            print(f"    Cell ID: {ue.get('cell_id', 'N/A')}")
            print(f"    RRC State: {ue.get('rrc_state', 'N/A')}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
    print()


def list_ues_mme():
    """List UEs registered with the MME/AMF."""
    print("=" * 60)
    print("UEs Registered with MME/AMF")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/mme/ue")

    if response.status_code == 200:
        data = response.json()
        ue_list = data.get("ue_list", [])
        print(f"Total UEs: {len(ue_list)}")
        for ue in ue_list:
            print(f"  MME UE ID: {ue.get('mme_ue_id', 'N/A')}")
            print(f"    IMSI: {ue.get('imsi', 'N/A')}")
            print(f"    State: {ue.get('state', 'N/A')}")
            print(f"    PDN Connections: {len(ue.get('pdn_list', []))}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
    print()


def get_ue_by_imsi(imsi: str):
    """Get UE details by IMSI.

    Args:
        imsi: The IMSI of the UE to look up.
    """
    print("=" * 60)
    print(f"UE Details for IMSI: {imsi}")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/mme/ue/imsi/{imsi}")

    if response.status_code == 200:
        data = response.json()
        print(f"  MME UE ID: {data.get('mme_ue_id', 'N/A')}")
        print(f"  State: {data.get('state', 'N/A')}")
        print(f"  eNB UE ID: {data.get('enb_ue_id', 'N/A')}")
        print(f"  PDN Connections:")
        for pdn in data.get("pdn_list", []):
            print(f"    - APN: {pdn.get('apn', 'N/A')}, IP: {pdn.get('ip', 'N/A')}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
    print()


def release_ue(mme_ue_id: int, cause: str | None = None):
    """Release/detach a UE from the network.

    Args:
        mme_ue_id: The MME UE ID to release.
        cause: Optional release cause.
    """
    print("=" * 60)
    print(f"Releasing UE: MME UE ID {mme_ue_id}")
    print("=" * 60)

    payload = {}
    if cause:
        payload["cause"] = cause

    response = requests.post(
        f"{BASE_URL}/mme/ue/{mme_ue_id}/release",
        json=payload if payload else None,
    )

    if response.status_code == 200:
        print("✓ UE released successfully")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.json()}")
    print()


def rrc_release(enb_ue_id: int, cause: str | None = None):
    """Release RRC connection for a UE.

    Args:
        enb_ue_id: The eNB UE ID to release.
        cause: Optional release cause.
    """
    print("=" * 60)
    print(f"RRC Release for eNB UE ID {enb_ue_id}")
    print("=" * 60)

    payload = {}
    if cause:
        payload["cause"] = cause

    response = requests.post(
        f"{BASE_URL}/enb/ue/{enb_ue_id}/rrc-release",
        json=payload if payload else None,
    )

    if response.status_code == 200:
        print("✓ RRC connection released")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.json()}")
    print()


def create_pdn_connection(mme_ue_id: int, apn: str, pdn_type: str = "ipv4"):
    """Create a PDN connection for a UE.

    Args:
        mme_ue_id: The MME UE ID.
        apn: The Access Point Name.
        pdn_type: The PDN type (ipv4, ipv6, or ipv4v6).
    """
    print("=" * 60)
    print(f"Creating PDN Connection")
    print(f"  UE: {mme_ue_id}, APN: {apn}, Type: {pdn_type}")
    print("=" * 60)

    response = requests.post(
        f"{BASE_URL}/mme/ue/{mme_ue_id}/pdn",
        json={"apn": apn, "pdn_type": pdn_type},
    )

    if response.status_code == 200:
        print("✓ PDN connection created")
        print(f"  Response: {response.json()}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.json()}")
    print()


def send_paging(imsi: str):
    """Send paging to a UE.

    Args:
        imsi: The IMSI of the UE to page.
    """
    print("=" * 60)
    print(f"Paging UE: {imsi}")
    print("=" * 60)

    response = requests.post(f"{BASE_URL}/mme/paging?imsi={imsi}")

    if response.status_code == 200:
        print("✓ Paging sent")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.json()}")
    print()


def main():
    """Run UE management examples."""
    print("\n" + "=" * 60)
    print("  AMARISOFT REST API - UE Management Examples")
    print("=" * 60)
    print(f"  Target: {BASE_URL}")
    print()

    try:
        # List UEs from different perspectives
        list_ues_enb()
        list_ues_mme()

        # Example: Get UE by IMSI (uncomment to use)
        # get_ue_by_imsi("001010123456789")

        # Example: Release UE (uncomment to use)
        # release_ue(mme_ue_id=1)

        # Example: RRC Release (uncomment to use)
        # rrc_release(enb_ue_id=1)

        # Example: Create PDN connection (uncomment to use)
        # create_pdn_connection(mme_ue_id=1, apn="internet")

        # Example: Send paging (uncomment to use)
        # send_paging("001010123456789")

    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to {BASE_URL}")
        print("Make sure the REST API service is running on the callbox.")


if __name__ == "__main__":
    main()
