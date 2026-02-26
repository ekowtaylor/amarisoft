#!/usr/bin/env python3
"""Test script to verify HTTPOverSSHClient connectivity to Amarisoft box.

Usage:
    python test_connectivity.py

Requirements:
    - sshpass must be installed for password authentication
    - Network access to the Amarisoft callbox
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from client.http_ssh import HTTPOverSSHClient, SSHConnectionError

# Configuration - Update these values for your Amarisoft box
SSH_HOST = "2620:10d:c052:12a:aaa1:59ff:fe88:d39"
SSH_USERNAME = "root"
SSH_PASSWORD = "toor"
SSH_KEY_PATH = None
REMOTE_PORT = 9010


def main() -> int:
    print("=" * 60)
    print("HTTPOverSSHClient Connectivity Test")
    print("=" * 60)

    client = HTTPOverSSHClient(
        ssh_host=SSH_HOST,
        ssh_username=SSH_USERNAME,
        ssh_password=SSH_PASSWORD,
        ssh_key_path=SSH_KEY_PATH,
        remote_port=REMOTE_PORT,
    )

    print(f"\nTarget: {SSH_USERNAME}@{SSH_HOST}")
    print(f"Remote API port: {REMOTE_PORT}")
    print(f"Local tunnel port: {client.local_port}")

    # Step 1: Check if SSH service is reachable
    print("\n[1] Checking SSH service reachability...")
    if client.is_listening():
        print("    ✓ SSH service is reachable")
    else:
        print("    ✗ SSH service is NOT reachable")
        print(f"    Make sure {SSH_HOST}:22 is accessible from this machine")
        return 1

    # Step 2: Establish SSH tunnel
    print("\n[2] Establishing SSH tunnel...")
    try:
        client.connect()
        print("    ✓ SSH tunnel established")
        print(f"    Tunnel: localhost:{client.local_port} -> {SSH_HOST}:{REMOTE_PORT}")
    except SSHConnectionError as e:
        print(f"    ✗ Failed to establish tunnel: {e}")
        return 1
    except Exception as e:
        print(f"    ✗ Unexpected error: {e}")
        return 1

    # Step 3: Check tunnel is active
    print("\n[3] Verifying tunnel is active...")
    if client.is_tunnel_active():
        print("    ✓ Tunnel is active")
    else:
        print("    ✗ Tunnel is NOT active")
        client.close()
        return 1

    # Step 4: Test REST API health check
    print("\n[4] Testing REST API health check...")
    try:
        health = client.health_check()
        status = health.get("status", "unknown")
        version = health.get("version", "unknown")
        print("    ✓ REST API is responding")
        print(f"      Status: {status}")
        print(f"      Version: {version}")

        callbox = health.get("callbox", {})
        connected = callbox.get("connected_services", 0)
        total = callbox.get("total_services", 0)
        print(f"      Services: {connected}/{total} connected")
    except Exception as e:
        print(f"    ✗ Health check failed: {e}")
        print("    The SSH tunnel works, but REST API may not be running")

    # Step 5: Try to get service status
    print("\n[5] Fetching service status...")
    try:
        services = client.get("/services")
        print("    ✓ Got service status")

        for svc_name, svc_info in services.get("services", {}).items():
            connected = svc_info.get("connected", False)
            port = svc_info.get("port", "N/A")
            status_icon = "✓" if connected else "✗"
            print(f"      {svc_name.upper():4}: {status_icon} (port {port})")
    except Exception as e:
        print(f"    ✗ Failed to get services: {e}")

    # Step 6: Test eNB stats endpoint
    print("\n[6] Fetching eNB/gNB stats...")
    try:
        stats = client.get("/enb/stats")
        print("    ✓ Got eNB stats")

        cells = stats.get("cells", {})
        print(f"      Active cells: {len(cells)}")

        for cell_id, cell_info in list(cells.items())[:3]:
            dl_bitrate = cell_info.get("dl_bitrate", 0)
            print(f"      Cell {cell_id}: DL bitrate = {dl_bitrate/1000:.2f} kbps")
    except Exception as e:
        print(f"    ✗ Failed to get eNB stats: {e}")

    # Step 7: Test MME UE list endpoint
    print("\n[7] Fetching MME UE list...")
    try:
        ue_data = client.get("/mme/ue")
        ue_list = ue_data.get("ue_list", [])
        print(f"    ✓ Got UE list: {len(ue_list)} UE(s)")

        for ue in ue_list[:3]:
            imsi = ue.get("imsi", "N/A")
            registered = ue.get("registered", False)
            status = "registered" if registered else "not registered"
            print(f"      IMSI {imsi}: {status}")
    except Exception as e:
        print(f"    ✗ Failed to get UE list: {e}")

    # Cleanup
    print("\n[8] Closing tunnel...")
    client.close()
    print("    ✓ Tunnel closed")

    print("\n" + "=" * 60)
    print("Connectivity test completed successfully!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
