#!/usr/bin/env python3
"""SSH Diagnostics Example - System administration and monitoring via SSH.

This example demonstrates all the SSH-only commands available for
Amarisoft Callbox system administration, including:
- System information (hostname, OS, CPU, motherboard)
- Resource monitoring (CPU, memory, disk, temperature)
- SDR hardware info (model, serial, FPGA, PCIe)
- Service management (start, stop, restart, status)
- Network configuration and diagnostics
- Configuration file management
- Time and NTP synchronization
- Comprehensive diagnostics

Usage:
    python examples/ssh_diagnostics.py 192.168.1.80

Requirements:
    - sshpass must be installed:
      macOS: brew install hudochenkov/sshpass/sshpass
      Linux: apt install sshpass
"""

import argparse
import sys
from datetime import datetime

sys.path.insert(0, ".")

from client.websocket import SSHClient


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")


def print_subheader(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n─── {title} ───")


def demo_system_info(ssh: SSHClient) -> None:
    """Demonstrate system information commands."""
    print_header("SYSTEM INFORMATION")

    # Basic info
    print(f"Hostname:          {ssh.get_hostname()}")

    os_info = ssh.get_os_info()
    print(f"OS:                {os_info['os_name']} {os_info['os_version']}")
    print(f"Kernel:            {os_info['kernel']}")

    print(f"Motherboard:       {ssh.get_motherboard_info()}")
    print(f"Amarisoft Version: {ssh.get_amarisoft_version()}")

    # CPU info
    cpu_info = ssh.get_cpu_info()
    print(f"CPU:               {cpu_info['model']}")
    print(f"CPU Cores:         {cpu_info['cores']} cores / {cpu_info['threads']} threads")
    print(f"Architecture:      {cpu_info['architecture']}")

    # Uptime
    uptime = ssh.get_uptime()
    print(f"Uptime:            {uptime['formatted']}")
    if uptime.get('boot_time'):
        print(f"Boot Time:         {uptime['boot_time']}")


def demo_resources(ssh: SSHClient) -> None:
    """Demonstrate resource monitoring commands."""
    print_header("SYSTEM RESOURCES")

    # CPU usage
    cpu_usage = ssh.get_cpu_usage()
    load = ssh.get_load_average()
    print(f"CPU Usage:         {cpu_usage:.1f}%")
    print(f"Load Average:      {load['1min']:.2f} (1m) / {load['5min']:.2f} (5m) / {load['15min']:.2f} (15m)")

    # Memory
    print_subheader("Memory")
    mem = ssh.get_memory_usage()
    bar_width = 30
    used_blocks = int((mem['percent_used'] / 100) * bar_width)
    bar = '█' * used_blocks + '░' * (bar_width - used_blocks)
    print(f"  Total:     {mem['total_gb']:.1f} GB")
    print(f"  Used:      {mem['used_gb']:.1f} GB")
    print(f"  Free:      {mem['free_gb']:.1f} GB")
    print(f"  Available: {mem['available_gb']:.1f} GB")
    print(f"  Usage:     [{bar}] {mem['percent_used']:.1f}%")

    # Disk
    print_subheader("Disk (root)")
    disk = ssh.get_disk_usage("/")
    used_blocks = int((disk['percent_used'] / 100) * bar_width)
    bar = '█' * used_blocks + '░' * (bar_width - used_blocks)
    print(f"  Total:     {disk['total_gb']:.1f} GB")
    print(f"  Used:      {disk['used_gb']:.1f} GB")
    print(f"  Free:      {disk['free_gb']:.1f} GB")
    print(f"  Usage:     [{bar}] {disk['percent_used']:.1f}%")

    # Temperature
    print_subheader("Temperature")
    temps = ssh.get_temperature()
    if temps['cpu'] is not None:
        temp = temps['cpu']
        if temp > 80:
            status = "🔥 HIGH"
        elif temp > 60:
            status = "⚠️  WARM"
        else:
            status = "✅ OK"
        print(f"  CPU Temp:  {temp:.1f}°C {status}")
    else:
        print("  Temperature sensors not available")

    for sensor in temps.get('sensors', [])[:3]:
        name = sensor.get('name', f"Zone {sensor.get('zone', '?')}")
        print(f"  {name}: {sensor.get('temp_c', 'N/A')}°C")


def demo_sdr_hardware(ssh: SSHClient) -> None:
    """Demonstrate SDR hardware information commands."""
    print_header("SDR HARDWARE")

    # List SDR device files
    devices = ssh.list_sdr_devices()
    print(f"SDR Device Files: {devices if devices else 'None found'}")

    # Get detailed SDR info
    sdr_cards = ssh.get_sdr_info()
    print(f"SDR Cards Found:  {len(sdr_cards)}")

    for i, sdr in enumerate(sdr_cards, 1):
        print_subheader(f"SDR Card {i}: {sdr.board_type}")
        print(f"  Device ID:      /dev/sdr{sdr.device_id}")
        print(f"  Board Type:     {sdr.board_type}")
        print(f"  Board ID:       {sdr.board_id}")
        print(f"  Serial:         {sdr.serial}")
        print(f"  FPGA Revision:  {sdr.fpga_revision}")
        print(f"  Board Revision: {sdr.board_revision}")
        print(f"  PCIe:           Gen{sdr.pcie_gen} x{sdr.pcie_lanes}")
        print(f"  Max Bandwidth:  {sdr.max_bandwidth_mhz} MHz")

    # RF Configuration
    rf_config = ssh.get_rf_config()
    print_subheader("RF Configuration")
    print(f"  TX Gain: {rf_config.get('tx_gain', 'N/A')} dB")
    print(f"  RX Gain: {rf_config.get('rx_gain', 'N/A')} dB")


def demo_pcie_usb(ssh: SSHClient) -> None:
    """Demonstrate PCIe and USB device enumeration."""
    print_header("HARDWARE DEVICES")

    # PCIe devices
    print_subheader("PCIe Devices")
    pcie_devices = ssh.list_pcie_devices()
    if pcie_devices:
        for dev in pcie_devices[:10]:  # Limit output
            print(f"  [{dev.slot}] {dev.vendor[:30]} - {dev.device[:30]}")
        if len(pcie_devices) > 10:
            print(f"  ... and {len(pcie_devices) - 10} more devices")
    else:
        print("  No PCIe devices found (lspci not available)")

    # USB devices
    print_subheader("USB Devices")
    usb_devices = ssh.list_usb_devices()
    if usb_devices:
        for dev in usb_devices[:10]:  # Limit output
            print(f"  [{dev.vendor_id}:{dev.product_id}] {dev.description[:50]}")
        if len(usb_devices) > 10:
            print(f"  ... and {len(usb_devices) - 10} more devices")
    else:
        print("  No USB devices found (lsusb not available)")


def demo_services(ssh: SSHClient) -> None:
    """Demonstrate service management commands."""
    print_header("LTE SERVICES")

    # Service status
    print_subheader("Service Status")
    services = ssh.get_service_status()
    for service, running in services.items():
        status = "✅ Running" if running else "❌ Stopped"
        print(f"  {service:12}: {status}")

    # Listening ports
    print_subheader("Remote API Ports")
    ports = ssh.get_listening_ports()
    for port_info in ports:
        print(f"  Port {port_info['port']}: {port_info['process']}")

    # Running processes
    print_subheader("LTE Processes")
    processes = ssh.get_process_list("lte")
    for proc in processes[:5]:
        cmd = proc['command'][:50] + "..." if len(proc['command']) > 50 else proc['command']
        print(f"  PID {proc['pid']:6} | CPU {proc['cpu_percent']:5.1f}% | MEM {proc['mem_percent']:5.1f}% | {cmd}")


def demo_network(ssh: SSHClient) -> None:
    """Demonstrate network configuration commands."""
    print_header("NETWORK CONFIGURATION")

    config = ssh.get_network_config()

    # Interfaces
    print_subheader("Network Interfaces")
    for iface in config['interfaces']:
        if isinstance(iface, dict):
            name = iface.get('name', 'unknown')
            ipv4 = iface.get('ipv4_address', 'N/A')
            print(f"  {name:10}: {ipv4}")

    # Gateway and DNS
    print_subheader("Gateway & DNS")
    print(f"  Gateway: {config.get('gateway', 'N/A')}")
    print(f"  DNS:     {', '.join(config.get('dns', [])) or 'N/A'}")

    # Ping test
    print_subheader("Connectivity Test")
    targets = ["8.8.8.8", "1.1.1.1"]
    for target in targets:
        result = ssh.ping(target, count=2, timeout=2)
        if result['success']:
            print(f"  {target}: ✅ {result['rtt_avg_ms']:.1f} ms avg")
        else:
            print(f"  {target}: ❌ {result['packet_loss_percent']:.0f}% loss")


def demo_time(ssh: SSHClient) -> None:
    """Demonstrate time and NTP commands."""
    print_header("TIME & SYNCHRONIZATION")

    time_info = ssh.get_time_info()

    print(f"Current Time:   {time_info.get('current_time', 'N/A')}")
    print(f"Timezone:       {time_info.get('timezone', 'N/A')}")

    ntp_enabled = "✅ Enabled" if time_info.get('ntp_enabled') else "❌ Disabled"
    ntp_sync = "✅ Synchronized" if time_info.get('ntp_synchronized') else "⚠️  Not Synchronized"

    print(f"NTP Service:    {ntp_enabled}")
    print(f"NTP Sync:       {ntp_sync}")

    if time_info.get('ntp_server'):
        print(f"NTP Server:     {time_info['ntp_server']}")


def demo_config_files(ssh: SSHClient) -> None:
    """Demonstrate configuration file management."""
    print_header("CONFIGURATION FILES")

    # List config files
    configs = ssh.list_config_files()

    for category, files in configs.items():
        if files:
            print_subheader(f"{category.upper()} Configs")
            for f in files[:3]:  # Limit output
                print(f"  {f}")
            if len(files) > 3:
                print(f"  ... and {len(files) - 3} more")

    # Show sample of enb config
    print_subheader("ENB Config Sample (first 20 lines)")
    try:
        enb_config = ssh.get_config_file("enb")
        lines = enb_config.split("\n")[:20]
        for line in lines:
            if line.strip() and not line.strip().startswith("//"):
                print(f"  {line[:70]}")
    except Exception as e:
        print(f"  Could not read config: {e}")


def demo_logs(ssh: SSHClient) -> None:
    """Demonstrate log access commands."""
    print_header("SYSTEM LOGS")

    # Recent log entries
    print_subheader("Recent OTS Log (last 10 lines)")
    logs = ssh.get_logs(lines=10, service="ots")
    for line in logs.strip().split("\n")[-10:]:
        if line.strip():
            print(f"  {line[:75]}")

    # Recent errors
    print_subheader("Recent Errors (last 5)")
    errors = ssh.get_log_errors(lines=200)
    for error in errors[-5:]:
        print(f"  {error[:75]}")
    if not errors:
        print("  No recent errors found ✅")


def demo_full_diagnostics(ssh: SSHClient) -> None:
    """Run comprehensive system diagnostics."""
    print_header("COMPREHENSIVE DIAGNOSTICS")

    print("Running system diagnostics... (this may take a moment)")
    results = ssh.run_diagnostics()

    print(f"\nTimestamp: {results['timestamp']}")
    print(f"Host:      {results['host']}")

    # Overall status
    status = results['status']
    if status == "OK":
        print(f"Status:    ✅ {status}")
    elif status == "WARNING":
        print(f"Status:    ⚠️  {status}")
    else:
        print(f"Status:    ❌ {status}")

    # Checks performed
    print_subheader("Checks Performed")
    checks = results.get('checks', {})
    for check, value in checks.items():
        if check == 'sample_errors':
            continue
        if isinstance(value, dict):
            print(f"  {check}: {len(value)} items")
        elif isinstance(value, list):
            print(f"  {check}: {len(value)} items")
        else:
            print(f"  {check}: {value}")

    # Warnings
    if results.get('warnings'):
        print_subheader("Warnings")
        for warning in results['warnings']:
            print(f"  ⚠️  {warning}")

    # Errors
    if results.get('errors'):
        print_subheader("Errors")
        for error in results['errors']:
            print(f"  ❌ {error}")

    # RF Status
    print_subheader("RF Hardware Status")
    rf_status = ssh.check_rf_status()
    print(f"  SDR Devices: {rf_status.get('sdr_devices', [])}")
    print(f"  SDR Cards:   {len(rf_status.get('sdr_cards', []))}")
    if rf_status.get('errors'):
        for error in rf_status['errors']:
            print(f"  ❌ {error}")


def demo_license(ssh: SSHClient) -> None:
    """Demonstrate license information retrieval."""
    print_header("LICENSE INFORMATION")

    license_info = ssh.get_license_info()

    if license_info.get('license_server'):
        print_subheader("License Server")
        server = license_info['license_server']
        if isinstance(server, dict):
            print(f"  Server: {server.get('server_addr', 'N/A')}")

    if license_info.get('local_licenses'):
        print_subheader("Local License Files")
        for lic in license_info['local_licenses']:
            print(f"  {lic.get('file', 'unknown')}:")
            for line in lic.get('content', '').split('\n')[:3]:
                if line.strip():
                    print(f"    {line.strip()}")


def main():
    parser = argparse.ArgumentParser(
        description="SSH Diagnostics Demo - Amarisoft Callbox System Administration"
    )
    parser.add_argument(
        "host",
        help="Callbox IP address (e.g., 192.168.1.80)"
    )
    parser.add_argument(
        "--username", "-u",
        default="root",
        help="SSH username (default: root)"
    )
    parser.add_argument(
        "--password", "-p",
        default="toor",
        help="SSH password (default: toor)"
    )
    parser.add_argument(
        "--section", "-s",
        choices=["all", "system", "resources", "sdr", "devices", "services",
                 "network", "time", "config", "logs", "diagnostics", "license"],
        default="all",
        help="Run specific section only"
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  AMARISOFT CALLBOX - SSH DIAGNOSTICS DEMO")
    print(f"  Host: {args.host}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    try:
        with SSHClient(args.host, args.username, args.password) as ssh:
            print(f"\n✅ SSH Connection established to {args.host}")

            sections = {
                "system": demo_system_info,
                "resources": demo_resources,
                "sdr": demo_sdr_hardware,
                "devices": demo_pcie_usb,
                "services": demo_services,
                "network": demo_network,
                "time": demo_time,
                "config": demo_config_files,
                "logs": demo_logs,
                "diagnostics": demo_full_diagnostics,
                "license": demo_license,
            }

            if args.section == "all":
                for section_name, section_func in sections.items():
                    try:
                        section_func(ssh)
                    except Exception as e:
                        print(f"\n❌ Error in {section_name}: {e}")
            else:
                sections[args.section](ssh)

            print("\n" + "=" * 70)
            print("  SSH DIAGNOSTICS COMPLETE")
            print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nMake sure:")
        print("  1. sshpass is installed (brew install hudochenkov/sshpass/sshpass)")
        print("  2. The Callbox is reachable")
        print("  3. SSH credentials are correct")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
