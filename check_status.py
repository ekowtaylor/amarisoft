#!/usr/bin/env python3
"""Script to check Amarisoft Callbox status and SDR card information.

This script connects to an Amarisoft Callbox using HTTPOverSSHClient to:
1. Check REST API health and service status
2. Enumerate SDR cards and their details
3. Report on overall system status

Usage:
    python check_status.py
"""

import sys

sys.path.insert(0, ".")

from client.http_ssh import HTTPOverSSHClient

# Configuration - Update these values for your Amarisoft box
SSH_HOST = "2620:10d:c052:12a:aaa1:59ff:fe88:d39"
SSH_USERNAME = "root"
SSH_PASSWORD = "toor"
REMOTE_API_PORT = 9010


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def main() -> int:
    print("=" * 60)
    print("  AMARISOFT CALLBOX STATUS CHECK")
    print("=" * 60)
    print(f"\nTarget: {SSH_USERNAME}@{SSH_HOST}")
    print(f"REST API Port: {REMOTE_API_PORT}")

    # Create the HTTP over SSH client
    client = HTTPOverSSHClient(
        ssh_host=SSH_HOST,
        ssh_username=SSH_USERNAME,
        ssh_password=SSH_PASSWORD,
        remote_port=REMOTE_API_PORT,
    )

    # Step 1: Check SSH connectivity
    print("\n[1] Checking SSH connectivity...")
    if client.is_listening():
        print("    ✓ SSH service is reachable")
    else:
        print("    ✗ SSH service is NOT reachable")
        print(f"    Make sure {SSH_HOST}:22 is accessible")
        return 1

    # Connect to establish SSH tunnel
    print("\n[2] Establishing SSH tunnel...")
    try:
        client.connect()
        print(f"    ✓ SSH tunnel established")
        print(
            f"    Tunnel: localhost:{client.local_port} -> {SSH_HOST}:{REMOTE_API_PORT}"
        )
    except Exception as e:
        print(f"    ✗ Failed to establish tunnel: {e}")
        return 1

    # Step 3: Check REST API health
    print("\n[3] Checking REST API health...")
    health_data = None
    try:
        health_data = client.health_check()
        status = health_data.get("status", "unknown")
        version = health_data.get("version", "unknown")
        print(f"    ✓ REST API is responding")
        print(f"      Status: {status}")
        print(f"      Version: {version}")

        callbox = health_data.get("callbox", {})
        connected = callbox.get("connected_services", 0)
        total = callbox.get("total_services", 0)
        print(f"      Services: {connected}/{total} connected")
    except Exception as e:
        print(f"    ✗ Health check failed: {e}")

    # Step 4: Get service details
    print("\n[4] Checking service status...")
    services_data = None
    try:
        services_data = client.get("/services")
        print("    ✓ Retrieved service status")

        services = services_data.get("services", {})
        for svc_name, svc_info in services.items():
            connected = svc_info.get("connected", False)
            port = svc_info.get("port", "N/A")
            status_icon = "✓" if connected else "✗"
            print(f"      {svc_name.upper():4}: {status_icon} (port {port})")
    except Exception as e:
        print(f"    ✗ Failed to get services: {e}")

    # Step 5: Get version information
    print("\n[5] Checking version information...")
    try:
        version_data = client.get("/version")
        api_version = version_data.get("api_version", "unknown")
        print(f"    API Version: {api_version}")

        svc_versions = version_data.get("services", {})
        for svc_name, svc_info in svc_versions.items():
            version = svc_info.get("version", "N/A")
            connected = svc_info.get("connected", False)
            if connected and version:
                print(f"      {svc_name.upper()}: {version}")
    except Exception as e:
        print(f"    ✗ Failed to get versions: {e}")

    # Step 6: Try to connect all services
    print("\n[6] Attempting to connect to all services...")
    try:
        connect_result = client.post("/services/connect")
        print("    ✓ Connection request sent")

        services = connect_result.get("services", {})
        for svc_name, svc_info in services.items():
            connected = svc_info.get("connected", False)
            error = svc_info.get("error")
            status_icon = "✓" if connected else "✗"
            error_msg = f" ({error})" if error else ""
            print(f"      {svc_name.upper():4}: {status_icon}{error_msg}")
    except Exception as e:
        print(f"    ✗ Failed to connect services: {e}")

    # Step 7: Get ENB license info (contains hardware info)
    print("\n[7] Checking eNB license info...")
    license_info = None
    try:
        license_info = client.get("/enb/license")
        print("    ✓ Retrieved license info")

        if license_info:
            user = license_info.get("user", "unknown")
            valid_until = license_info.get("valid_until", "unknown")
            products = license_info.get("products", [])
            print(f"      User: {user}")
            print(f"      Valid Until: {valid_until}")
            if products:
                print(
                    f"      Products: {', '.join(products) if isinstance(products, list) else products}"
                )
    except Exception as e:
        print(f"    ⚠ Could not get license info: {e}")

    # Step 8: Get ENB stats with RF info (includes SDR-related data)
    print("\n[8] Checking eNB/gNB stats (with RF info)...")
    rf_info = None
    try:
        enb_stats = client.get("/enb/stats", params={"rf": "true"})
        print("    ✓ Retrieved eNB stats")

        cells = enb_stats.get("cells", {})
        if cells:
            print(f"      Active cells: {len(cells)}")
            for cell_id, cell_info in cells.items():
                dl_bitrate = cell_info.get("dl_bitrate", 0)
                ul_bitrate = cell_info.get("ul_bitrate", 0)
                print(
                    f"        Cell {cell_id}: DL={dl_bitrate/1e6:.2f} Mbps, UL={ul_bitrate/1e6:.2f} Mbps"
                )
        else:
            print("      No active cells")

        # Check for RF info
        rf_info = enb_stats.get("rf")
        if rf_info:
            print(
                f"      RF Info available: {list(rf_info.keys()) if isinstance(rf_info, dict) else 'yes'}"
            )
    except Exception as e:
        print(f"    ⚠ Could not get eNB stats: {e}")

    # Step 9: Get cell configuration (may include SDR/RF config)
    print("\n[9] Checking cell configuration...")
    try:
        cells_data = client.get("/enb/cells")
        cell_list = cells_data.get("cell_list", [])
        print(f"    ✓ Found {len(cell_list)} configured cell(s)")

        for cell in cell_list[:5]:
            cell_id = cell.get("cell_id", "N/A")
            rat = cell.get("rat", "unknown")
            band = cell.get("rf_port", cell.get("band", "N/A"))
            bw = cell.get("bandwidth", cell.get("n_rb_dl", "N/A"))
            print(f"      - Cell {cell_id}: {rat}, Band {band}, BW {bw}")

        if len(cell_list) > 5:
            print(f"      ... and {len(cell_list) - 5} more")
    except Exception as e:
        print(f"    ⚠ Could not get cells: {e}")

    # Step 10: Get UE list from eNB
    print("\n[10] Checking connected UEs (eNB)...")
    try:
        ue_data = client.get("/enb/ue")
        ue_list = ue_data.get("ue_list", [])
        print(f"    ✓ Found {len(ue_list)} UE(s) connected to eNB")

        for ue in ue_list[:5]:  # Show first 5 UEs
            imsi = ue.get("imsi", "unknown")
            cell_id = ue.get("cell_id", "N/A")
            print(f"      - IMSI: {imsi}, Cell: {cell_id}")

        if len(ue_list) > 5:
            print(f"      ... and {len(ue_list) - 5} more")
    except Exception as e:
        print(f"    ⚠ Could not get UE list: {e}")

    # Step 11: Get UE list from MME
    print("\n[11] Checking attached UEs (MME)...")
    try:
        mme_ue_data = client.get("/mme/ue")
        mme_ue_list = mme_ue_data.get("ue_list", [])
        print(f"    ✓ Found {len(mme_ue_list)} UE(s) attached to MME")

        for ue in mme_ue_list[:5]:  # Show first 5 UEs
            imsi = ue.get("imsi", "unknown")
            ip = ue.get("ip_addr", "N/A")
            print(f"      - IMSI: {imsi}, IP: {ip}")

        if len(mme_ue_list) > 5:
            print(f"      ... and {len(mme_ue_list) - 5} more")
    except Exception as e:
        print(f"    ⚠ Could not get MME UE list: {e}")

    # Print summary
    print_section("SUMMARY")

    ssh_ok = client.is_tunnel_active()
    api_ok = health_data is not None
    api_healthy = health_data and health_data.get("status") == "healthy"

    connected_services = 0
    total_services = 0
    if services_data:
        for svc_info in services_data.get("services", {}).values():
            total_services += 1
            if svc_info.get("connected"):
                connected_services += 1

    print(f"  SSH Tunnel:        {'✓ Active' if ssh_ok else '✗ Inactive'}")
    print(f"  REST API:          {'✓ Responding' if api_ok else '✗ Not responding'}")
    print(
        f"  API Health:        {'✓ Healthy' if api_healthy else '⚠ Unhealthy' if api_ok else '─ N/A'}"
    )
    print(f"  Services:          {connected_services}/{total_services} connected")

    # Cleanup
    print("\n[12] Closing tunnel...")
    client.close()
    print("    ✓ Tunnel closed")

    print("\n" + "=" * 60)
    print("  Status check completed!")
    print("=" * 60)

    return 0 if (ssh_ok and api_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
