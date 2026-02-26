#!/usr/bin/env python3
"""Comprehensive Amarisoft Callbox Status Script.

This script connects to an Amarisoft Callbox using HTTPOverSSHClient to:
1. Check overall system health and service status
2. Display cell configuration details
3. Show attached/connected UE information
4. Print network interface status

Usage:
    python callbox_status.py [--verbose]

Requirements:
    - sshpass must be installed for password authentication
    - Network access to the Amarisoft callbox
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any

sys.path.insert(0, ".")

from client.http_ssh import HTTPOverSSHClient, SSHConnectionError


# ═══════════════════════════════════════════════════════════════════════════
# Configuration - Update these values for your Amarisoft box
# ═══════════════════════════════════════════════════════════════════════════
SSH_HOST = "2620:10d:c052:12a:aaa1:59ff:fe88:d39"
SSH_USERNAME = "root"
SSH_PASSWORD = "toor"
REMOTE_API_PORT = 9010

# ProxyJump through devserver (set to None if direct connection is possible)
SSH_PROXY_HOST = "devvm14066.vll0.facebook.com"


def print_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")


def print_section(title: str) -> None:
    """Print a subsection header."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def format_bytes(bytes_val: int) -> str:
    """Format bytes into human readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"


def format_bitrate(bps: float) -> str:
    """Format bitrate into human readable format."""
    if bps < 1000:
        return f"{bps:.0f} bps"
    elif bps < 1_000_000:
        return f"{bps/1000:.2f} Kbps"
    elif bps < 1_000_000_000:
        return f"{bps/1_000_000:.2f} Mbps"
    else:
        return f"{bps/1_000_000_000:.2f} Gbps"


def check_network_info(client: HTTPOverSSHClient) -> dict[str, Any] | None:
    """Get network identity information (MCC, MNC, etc.)."""
    print_section("Network Identity")
    try:
        # Get eNB config for network info (cells contain PLMN)
        enb_config = client.get("/enb/config")
        
        # Get PLMN from first cell
        cells = enb_config.get("cells", {})
        if isinstance(cells, dict):
            cells = list(cells.values())
        
        plmn_list = []
        tac = "N/A"
        ecgi = {}
        if cells and isinstance(cells[0], dict):
            plmn_list = cells[0].get("plmn_list", [])
            tac = cells[0].get("tac", "N/A")
            ecgi = cells[0].get("ecgi", {})
        
        print(f"  PLMN Configuration:")
        if plmn_list:
            for i, plmn_entry in enumerate(plmn_list[:5]):
                # PLMN can be in format '00101' (MCC=001, MNC=01) or dict
                plmn_str = plmn_entry.get("plmn", "") if isinstance(plmn_entry, dict) else str(plmn_entry)
                if plmn_str and len(plmn_str) >= 5:
                    mcc = plmn_str[:3]
                    mnc = plmn_str[3:]
                else:
                    mcc = plmn_entry.get("mcc", "N/A") if isinstance(plmn_entry, dict) else "N/A"
                    mnc = plmn_entry.get("mnc", "N/A") if isinstance(plmn_entry, dict) else "N/A"
                print(f"    PLMN {i+1}: MCC={mcc}, MNC={mnc}")
        else:
            print("    No PLMN configured")
        
        # ECGI (E-UTRAN Cell Global Identifier)
        if ecgi:
            ecgi_plmn = ecgi.get("plmn", "")
            eci = ecgi.get("eci", "N/A")
            if ecgi_plmn and len(ecgi_plmn) >= 5:
                ecgi_mcc = ecgi_plmn[:3]
                ecgi_mnc = ecgi_plmn[3:]
                print(f"\n  E-UTRAN Cell Global ID (ECGI):")
                print(f"    MCC:  {ecgi_mcc}")
                print(f"    MNC:  {ecgi_mnc}")
                print(f"    ECI:  {eci}")
        
        # TAC
        print(f"\n  Tracking Area:")
        print(f"    TAC: {tac}")
        
        # Global eNB ID
        global_enb_id = enb_config.get("global_enb_id", {})
        if global_enb_id:
            enb_id = global_enb_id.get("enb_id", "N/A")
            enb_plmn = global_enb_id.get("plmn", "")
            if enb_plmn and len(enb_plmn) >= 5:
                enb_mcc = enb_plmn[:3]
                enb_mnc = enb_plmn[3:]
            else:
                enb_mcc = global_enb_id.get("mcc", "N/A")
                enb_mnc = global_enb_id.get("mnc", "N/A")
            print(f"\n  Global eNB Identity:")
            print(f"    eNB ID:  {enb_id}")
            print(f"    MCC:     {enb_mcc}")
            print(f"    MNC:     {enb_mnc}")
        
        # License info
        license_user = enb_config.get("license_user", "N/A")
        license_id = enb_config.get("license_id", "N/A")
        version = enb_config.get("version", "N/A")
        name = enb_config.get("name", "N/A")
        
        print(f"\n  System Info:")
        print(f"    Name:         {name}")
        print(f"    Version:      {version}")
        print(f"    License User: {license_user}")
        print(f"    License ID:   {license_id}")
        
        return {"enb_config": enb_config}
    except Exception as e:
        print(f"  ✗ Failed to get network info: {e}")
        return None


def check_carrier_info(client: HTTPOverSSHClient) -> dict[str, Any] | None:
    """Get carrier/frequency information."""
    print_section("Carrier Configuration")
    try:
        enb_config = client.get("/enb/config")
        cells = enb_config.get("cells", [])

        # Handle both list and dict formats
        if isinstance(cells, dict):
            cells = list(cells.values())

        if not cells:
            print("  No carrier configuration found")
            return None

        for i, cell in enumerate(list(cells)[:10]):
            if not isinstance(cell, dict):
                continue

            cell_id = cell.get("cell_id", i)
            rat = cell.get("rat", "LTE")

            print(f"\n  Cell {cell_id} ({rat}):")

            # Frequency info
            if rat == "NR" or rat == "nr":
                dl_arfcn = cell.get("dl_nr_arfcn", "N/A")
                ul_arfcn = cell.get("ul_nr_arfcn", dl_arfcn)
                band = cell.get("band", "N/A")
                scs = cell.get("subcarrier_spacing", 30)
                print(f"    DL NR-ARFCN:  {dl_arfcn}")
                print(f"    UL NR-ARFCN:  {ul_arfcn}")
                print(f"    Band:         n{band}")
                print(f"    SCS:          {scs} kHz")
            else:
                dl_earfcn = cell.get("dl_earfcn", "N/A")
                ul_earfcn = cell.get("ul_earfcn", "N/A")
                band = cell.get("band", "N/A")
                print(f"    DL EARFCN:    {dl_earfcn}")
                print(f"    UL EARFCN:    {ul_earfcn}")
                print(f"    Band:         {band}")

            # Bandwidth
            n_rb_dl = cell.get("n_rb_dl", "N/A")
            n_rb_ul = cell.get("n_rb_ul", n_rb_dl)
            bandwidth = cell.get("bandwidth", "N/A")

            # Convert RBs to MHz if not provided
            if bandwidth == "N/A" and isinstance(n_rb_dl, int):
                rb_to_mhz = {6: 1.4, 15: 3, 25: 5, 50: 10, 75: 15, 100: 20}
                bandwidth = rb_to_mhz.get(n_rb_dl, f"{n_rb_dl} RBs")

            print(
                f"    Bandwidth:    {bandwidth} MHz"
                if isinstance(bandwidth, (int, float))
                else f"    Bandwidth:    {bandwidth}"
            )
            print(f"    RBs (DL/UL):  {n_rb_dl}/{n_rb_ul}")

            # TX power
            tx_gain = cell.get("tx_gain", cell.get("rf_port_tx_gain", "N/A"))
            print(f"    TX Gain:      {tx_gain} dB")

            # MIMO
            n_antenna_dl = cell.get("n_antenna_dl", 1)
            n_antenna_ul = cell.get("n_antenna_ul", 1)
            tm = cell.get("transmission_mode", "N/A")
            print(f"    Antennas:     {n_antenna_dl}T{n_antenna_ul}R")
            if tm != "N/A":
                print(f"    TM:           {tm}")

        return enb_config
    except Exception as e:
        print(f"  ✗ Failed to get carrier info: {e}")
        return None


def check_health(client: HTTPOverSSHClient) -> dict[str, Any] | None:
    """Check REST API health status."""
    print_section("Health Status")
    try:
        health = client.health_check()
        status = health.get("status", "unknown")
        version = health.get("version", "unknown")
        timestamp = health.get("timestamp", "unknown")

        status_icon = "✓" if status == "healthy" else "⚠"
        print(f"  Status:    {status_icon} {status.upper()}")
        print(f"  Version:   {version}")
        print(f"  Timestamp: {timestamp}")

        callbox = health.get("callbox", {})
        connected = callbox.get("connected_services", 0)
        total = callbox.get("total_services", 0)
        print(f"  Services:  {connected}/{total} connected")

        return health
    except Exception as e:
        print(f"  ✗ Failed to get health status: {e}")
        return None


def check_services(client: HTTPOverSSHClient) -> dict[str, Any] | None:
    """Check all service status."""
    print_section("Service Status")
    try:
        services_data = client.get("/services")
        services = services_data.get("services", {})

        for svc_name, svc_info in services.items():
            connected = svc_info.get("connected", False)
            port = svc_info.get("port", "N/A")
            name = svc_info.get("name", svc_name)
            error = svc_info.get("error")

            status_icon = "✓" if connected else "✗"
            error_msg = f" ({error})" if error and not connected else ""
            print(f"  {name:15} Port {port:5} {status_icon}{error_msg}")

        return services_data
    except Exception as e:
        print(f"  ✗ Failed to get services: {e}")
        return None


def check_enb_stats(
    client: HTTPOverSSHClient, verbose: bool = False
) -> dict[str, Any] | None:
    """Get eNB/gNB statistics."""
    print_section("eNB/gNB Statistics")
    try:
        stats = client.get("/enb/stats", params={"rf": "true"})

        # CPU info
        cpu = stats.get("cpu", {})
        if cpu:
            print(f"  CPU Usage: {json.dumps(cpu)}")

        # Cell statistics
        cells = stats.get("cells", {})
        if cells:
            print(f"\n  Active Cells: {len(cells)}")
            for cell_id, cell_info in cells.items():
                dl_bitrate = cell_info.get("dl_bitrate", 0)
                ul_bitrate = cell_info.get("ul_bitrate", 0)
                ue_count = cell_info.get(
                    "ue_count_avg", cell_info.get("ue_count_max", "N/A")
                )
                dl_use = cell_info.get("dl_use_avg", 0) * 100
                ul_use = cell_info.get("ul_use_avg", 0) * 100

                print(f"\n    Cell {cell_id}:")
                print(f"      DL Bitrate:  {format_bitrate(dl_bitrate)}")
                print(f"      UL Bitrate:  {format_bitrate(ul_bitrate)}")
                print(f"      DL Usage:    {dl_use:.1f}%")
                print(f"      UL Usage:    {ul_use:.1f}%")
                print(f"      UE Count:    {ue_count}")

                if verbose:
                    counters = cell_info.get("counters", {})
                    messages = counters.get("messages", {})
                    if messages:
                        print(f"      RRC Messages: {len(messages)} types")
        else:
            print("  No active cells")

        # RF port info
        rf_ports = stats.get("rf_ports", {})
        if rf_ports:
            print(f"\n  RF Ports: {len(rf_ports)}")
            for port_id, port_info in rf_ports.items():
                rxtx = port_info.get("rxtx_delay", {})
                if rxtx:
                    avg_delay = rxtx.get("avg", "N/A")
                    print(f"    Port {port_id}: RX/TX delay avg = {avg_delay} ms")

        return stats
    except Exception as e:
        print(f"  ✗ Failed to get eNB stats: {e}")
        return None


def check_cell_config(
    client: HTTPOverSSHClient, verbose: bool = False
) -> dict[str, Any] | None:
    """Get cell configuration."""
    print_section("Cell Configuration")
    try:
        cells_data = client.get("/enb/cells")
        cell_list = cells_data.get("cell_list", [])

        if not cell_list:
            # Try to get from config
            config = client.get("/enb/config")
            cells = config.get("cells", [])

            # Handle both list and dict formats
            if isinstance(cells, dict):
                cells = list(cells.values())

            if cells:
                print(f"  Configured Cells: {len(cells)}")
                for i, cell in enumerate(list(cells)[:10]):
                    if isinstance(cell, dict):
                        cell_id = cell.get("cell_id", i)
                        rat = cell.get("rat", "LTE")
                        band = cell.get("rf_port", cell.get("band", "N/A"))
                        n_rb = cell.get("n_rb_dl", cell.get("bandwidth", "N/A"))
                        pci = cell.get("n_id_cell", cell.get("pci", "N/A"))
                        print(f"\n    Cell {cell_id}:")
                        print(f"      RAT:       {rat}")
                        print(f"      Band/Port: {band}")
                        print(f"      RBs (DL):  {n_rb}")
                        print(f"      PCI:       {pci}")
            else:
                print("  No cell configuration found")
            return config

        print(f"  Configured Cells: {len(cell_list)}")
        for cell in list(cell_list)[:10]:
            if isinstance(cell, dict):
                cell_id = cell.get("cell_id", "N/A")
                rat = cell.get("rat", "unknown")
                dl_freq = cell.get("dl_earfcn", cell.get("dl_nr_arfcn", "N/A"))
                bandwidth = cell.get("bandwidth", cell.get("n_rb_dl", "N/A"))

                print(f"\n    Cell {cell_id}:")
                print(f"      RAT:       {rat}")
                print(f"      DL Freq:   {dl_freq}")
                print(f"      Bandwidth: {bandwidth}")

        if len(cell_list) > 10:
            print(f"\n    ... and {len(cell_list) - 10} more cells")

        return cells_data
    except Exception as e:
        print(f"  ✗ Failed to get cell config: {e}")
        return None


def check_enb_ues(
    client: HTTPOverSSHClient, verbose: bool = False
) -> dict[str, Any] | None:
    """Get UEs connected to eNB."""
    print_section("Connected UEs (eNB/gNB)")
    try:
        ue_data = client.get("/enb/ue")
        ue_list = ue_data.get("ue_list", [])

        print(f"  Total UEs: {len(ue_list)}")

        for ue in ue_list[:10]:
            enb_ue_id = ue.get("enb_ue_id", "N/A")
            mme_ue_id = ue.get("mme_ue_id", "N/A")
            rnti = ue.get("rnti", "N/A")
            cells = ue.get("cells", [])
            cell_ids = [c.get("cell_id", "?") for c in cells]

            print(f"\n    UE {enb_ue_id}:")
            print(f"      MME UE ID: {mme_ue_id}")
            print(f"      RNTI:      {rnti}")
            print(f"      Cells:     {cell_ids}")

        if len(ue_list) > 10:
            print(f"\n    ... and {len(ue_list) - 10} more UEs")

        return ue_data
    except Exception as e:
        print(f"  ✗ Failed to get eNB UEs: {e}")
        return None


def check_mme_ues(
    client: HTTPOverSSHClient, verbose: bool = False
) -> dict[str, Any] | None:
    """Get UEs attached to MME."""
    print_section("Attached UEs (MME/AMF)")
    try:
        ue_data = client.get("/mme/ue")
        ue_list = ue_data.get("ue_list", [])

        # Count registered vs non-registered
        registered = sum(1 for ue in ue_list if ue.get("registered", False))
        print(f"  Total UEs: {len(ue_list)} ({registered} registered)")

        for ue in ue_list[:10]:
            imsi = ue.get("imsi", "N/A")
            registered = ue.get("registered", False)
            m_tmsi = ue.get("m_tmsi", "N/A")
            imeisv = ue.get("imeisv", "N/A")
            bearers = ue.get("bearers", [])

            reg_status = "✓ Registered" if registered else "○ Not registered"
            print(f"\n    IMSI: {imsi}")
            print(f"      Status:  {reg_status}")
            print(f"      M-TMSI:  {m_tmsi}")
            print(f"      IMEISV:  {imeisv}")

            if bearers:
                print(f"      Bearers: {len(bearers)}")
                for bearer in bearers[:3]:
                    erab_id = bearer.get("erab_id", "N/A")
                    apn = bearer.get("apn", "N/A")
                    ip = bearer.get("ip", "N/A")
                    dl_bytes = bearer.get("dl_total_bytes", 0)
                    ul_bytes = bearer.get("ul_total_bytes", 0)

                    print(f"        Bearer {erab_id}: APN={apn}, IP={ip}")
                    print(
                        f"          DL: {format_bytes(dl_bytes)}, UL: {format_bytes(ul_bytes)}"
                    )

                if len(bearers) > 3:
                    print(f"        ... and {len(bearers) - 3} more bearers")

        if len(ue_list) > 10:
            print(f"\n    ... and {len(ue_list) - 10} more UEs")

        return ue_data
    except Exception as e:
        print(f"  ✗ Failed to get MME UEs: {e}")
        return None


def check_apns(client: HTTPOverSSHClient) -> dict[str, Any] | None:
    """Get APN information with detailed bearer stats."""
    print_section("APN Configuration")
    try:
        apn_data = client.get("/mme/apn")
        apn_list = apn_data.get("apn_list", [])

        print(f"  Active APNs: {apn_data.get('total_apns', len(apn_list))}")
        print(f"  UEs with bearers: {apn_data.get('ue_count', 'N/A')}")

        # Get detailed bearer info from UE list
        ue_data = client.get("/mme/ue")
        ue_list = ue_data.get("ue_list", [])
        
        # Aggregate bearer details per APN
        apn_details: dict[str, dict] = {}
        for ue in ue_list:
            for bearer in ue.get("bearers", []):
                apn_name = bearer.get("apn", "unknown")
                if apn_name not in apn_details:
                    apn_details[apn_name] = {
                        "bearers": [],
                        "total_dl_bytes": 0,
                        "total_ul_bytes": 0,
                    }
                apn_details[apn_name]["bearers"].append(bearer)
                apn_details[apn_name]["total_dl_bytes"] += bearer.get("dl_total_bytes", 0)
                apn_details[apn_name]["total_ul_bytes"] += bearer.get("ul_total_bytes", 0)

        for apn in apn_list:
            name = apn.get("apn", "N/A")
            ue_count = apn.get("ue_count", 0)
            bearer_count = apn.get("bearer_count", 0)
            
            print(f"\n    APN: {name}")
            print(f"      UE Count:     {ue_count}")
            print(f"      Bearer Count: {bearer_count}")
            
            # Show detailed info if available
            if name in apn_details:
                details = apn_details[name]
                print(f"      Total DL:     {format_bytes(details['total_dl_bytes'])}")
                print(f"      Total UL:     {format_bytes(details['total_ul_bytes'])}")
                
                # Show IP addresses assigned
                ips = []
                ipv6s = []
                for b in details["bearers"]:
                    if b.get("ip"):
                        ips.append(b["ip"])
                    if b.get("ipv6"):
                        ipv6s.append(b["ipv6"])
                
                if ips:
                    print(f"      IPv4 Addrs:   {', '.join(ips)}")
                if ipv6s:
                    print(f"      IPv6 Addrs:   {', '.join(ipv6s)}")

        return apn_data
    except Exception as e:
        print(f"  ✗ Failed to get APN info: {e}")
        return None


def check_interfaces(client: HTTPOverSSHClient) -> None:
    """Check network interface status."""
    print_section("Interface Status")

    interfaces = [
        ("S1", "/enb/interface/s1"),
        ("NG", "/enb/interface/ng"),
        ("X2", "/enb/interface/x2"),
        ("Xn", "/enb/interface/xn"),
    ]

    for name, endpoint in interfaces:
        try:
            data = client.get(endpoint)
            # Check if interface has any connections
            if isinstance(data, dict):
                has_data = any(
                    k not in ["message", "message_id", "time", "utc"]
                    for k in data.keys()
                )
                if has_data:
                    print(f"  {name:4} ✓ Active")
                else:
                    print(f"  {name:4} ○ No connections")
        except Exception:
            print(f"  {name:4} ✗ Error")


def print_summary(
    health: dict | None,
    services: dict | None,
    enb_ues: dict | None,
    mme_ues: dict | None,
) -> None:
    """Print summary of callbox status."""
    print_header("SUMMARY")

    # Health status
    if health:
        status = health.get("status", "unknown")
        status_icon = "✓" if status == "healthy" else "⚠"
        print(f"  System Health:  {status_icon} {status.upper()}")
    else:
        print("  System Health:  ✗ Unable to determine")

    # Service status
    if services:
        svc_data = services.get("services", {})
        connected = sum(1 for s in svc_data.values() if s.get("connected"))
        total = len(svc_data)
        print(f"  Services:       {connected}/{total} connected")

    # UE counts
    if enb_ues:
        enb_count = len(enb_ues.get("ue_list", []))
        print(f"  Connected UEs:  {enb_count}")

    if mme_ues:
        mme_list = mme_ues.get("ue_list", [])
        registered = sum(1 for ue in mme_list if ue.get("registered"))
        print(f"  Registered UEs: {registered}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check Amarisoft Callbox status via HTTP over SSH"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show verbose output"
    )
    parser.add_argument(
        "--host", default=SSH_HOST, help=f"SSH host (default: {SSH_HOST})"
    )
    parser.add_argument(
        "--user", default=SSH_USERNAME, help=f"SSH username (default: {SSH_USERNAME})"
    )
    parser.add_argument("--password", default=SSH_PASSWORD, help="SSH password")
    parser.add_argument(
        "--port",
        type=int,
        default=REMOTE_API_PORT,
        help=f"Remote API port (default: {REMOTE_API_PORT})",
    )

    args = parser.parse_args()

    print_header("AMARISOFT CALLBOX STATUS")
    print(f"  Target:    {args.user}@{args.host}")
    print(f"  API Port:  {args.port}")
    print(f"  Time:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Create client
    client = HTTPOverSSHClient(
        ssh_host=args.host,
        ssh_username=args.user,
        ssh_password=args.password,
        remote_port=args.port,
    )

    # Check SSH connectivity
    print_section("SSH Connectivity")
    if client.is_listening():
        print("  ✓ SSH service is reachable")
    else:
        print("  ✗ SSH service is NOT reachable")
        print(f"  Make sure {args.host}:22 is accessible")
        return 1

    # Establish tunnel
    print("\n  Establishing SSH tunnel...")
    try:
        client.connect()
        print(
            f"  ✓ Tunnel established: localhost:{client.local_port} -> {args.host}:{args.port}"
        )
    except SSHConnectionError as e:
        print(f"  ✗ Failed to establish tunnel: {e}")
        return 1

    try:
        # Run all checks
        health = check_health(client)
        services = check_services(client)
        check_network_info(client)
        check_carrier_info(client)
        check_enb_stats(client, args.verbose)
        check_cell_config(client, args.verbose)
        enb_ues = check_enb_ues(client, args.verbose)
        mme_ues = check_mme_ues(client, args.verbose)
        check_apns(client)
        check_interfaces(client)

        # Print summary
        print_summary(health, services, enb_ues, mme_ues)

    finally:
        # Cleanup
        print(f"\n{'─' * 60}")
        print("  Closing SSH tunnel...")
        client.close()
        print("  ✓ Done")

    print(f"\n{'═' * 70}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
