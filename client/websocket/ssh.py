"""SSH client for Amarisoft Callbox system administration.

This module provides SSH-based access to the Callbox for operations
that are not available via the WebSocket Remote API, such as:
- Hardware information (SDR cards, serial numbers, PCIe devices)
- System information (hostname, OS version, CPU, memory, disk)
- Service management (restart, stop, start)
- Configuration file management (backup, restore, list)
- File transfer (upload, download, IQ samples)
- Network diagnostics (IP config, ping, routes)
- Time synchronization (NTP status, sync)
- Diagnostics and troubleshooting

Usage::

    from amarisoft.ssh import SSHClient

    with SSHClient("192.168.1.80") as ssh:
        # Get comprehensive system info
        info = ssh.get_system_info()
        print(info)

        # Check system resources
        print(f"CPU: {ssh.get_cpu_usage()}%")
        print(f"Memory: {ssh.get_memory_usage()}")
        print(f"Disk: {ssh.get_disk_usage()}")

        # Backup configuration
        ssh.backup_config("/tmp/callbox_backup")

        # Download IQ samples
        ssh.download_file("/tmp/rx.bin", "./rx_samples.bin")
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SDRCard:
    """SDR hardware information."""

    device_id: int
    board_type: str  # SDR50, SDR100
    board_id: str
    serial: str
    fpga_revision: str
    board_revision: str = "0x0"
    pcie_gen: int = 2
    pcie_lanes: int = 1

    @property
    def max_bandwidth_mhz(self) -> int:
        """Maximum bandwidth based on board type."""
        return 100 if self.board_type == "SDR100" else 50

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "device_id": self.device_id,
            "board_type": self.board_type,
            "board_id": self.board_id,
            "serial": self.serial,
            "fpga_revision": self.fpga_revision,
            "board_revision": self.board_revision,
            "pcie_gen": self.pcie_gen,
            "pcie_lanes": self.pcie_lanes,
            "max_bandwidth_mhz": self.max_bandwidth_mhz,
            "pcie": f"gen{self.pcie_gen} x{self.pcie_lanes}",
        }


@dataclass
class PCIeDevice:
    """PCIe device information."""

    slot: str
    device_class: str
    vendor: str
    device: str
    driver: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "slot": self.slot,
            "class": self.device_class,
            "vendor": self.vendor,
            "device": self.device,
            "driver": self.driver,
        }


@dataclass
class USBDevice:
    """USB device information."""

    bus: str
    device: str
    vendor_id: str
    product_id: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "bus": self.bus,
            "device": self.device,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "description": self.description,
        }


@dataclass
class NetworkInterface:
    """Network interface information."""

    name: str
    ipv4_address: str | None = None
    ipv4_netmask: str | None = None
    ipv6_address: str | None = None
    mac_address: str | None = None
    state: str = "unknown"
    mtu: int = 1500

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "ipv4_address": self.ipv4_address,
            "ipv4_netmask": self.ipv4_netmask,
            "ipv6_address": self.ipv6_address,
            "mac_address": self.mac_address,
            "state": self.state,
            "mtu": self.mtu,
        }


@dataclass
class SystemInfo:
    """Comprehensive system information from SSH."""

    hostname: str = "unknown"
    os_name: str = "unknown"
    os_version: str = "unknown"
    kernel: str = "unknown"
    motherboard: str = "unknown"
    amarisoft_version: str = "unknown"
    sdr_cards: list[SDRCard] = field(default_factory=list)
    rf_config: dict[str, Any] = field(default_factory=dict)
    cpu_model: str = "unknown"
    cpu_cores: int = 0
    memory_total_gb: float = 0.0
    disk_total_gb: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hostname": self.hostname,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "kernel": self.kernel,
            "motherboard": self.motherboard,
            "amarisoft_version": self.amarisoft_version,
            "sdr_cards": [card.to_dict() for card in self.sdr_cards],
            "rf_config": self.rf_config,
            "cpu_model": self.cpu_model,
            "cpu_cores": self.cpu_cores,
            "memory_total_gb": self.memory_total_gb,
            "disk_total_gb": self.disk_total_gb,
        }


class SSHClient:
    """SSH client for Callbox system administration.

    Provides access to system-level operations not available via WebSocket.

    Note:
        Requires `sshpass` to be installed for password authentication.
        On macOS: `brew install hudochenkov/sshpass/sshpass`
        On Linux: `apt install sshpass` or `yum install sshpass`

    Example::

        with SSHClient("192.168.1.80") as ssh:
            # Get system info
            info = ssh.get_system_info()
            print(f"Hostname: {info.hostname}")

            # Check resources
            print(f"CPU: {ssh.get_cpu_usage()}%")

            # Backup config
            ssh.backup_config("./backup")
    """

    # Standard Amarisoft config file locations
    CONFIG_PATHS = {
        "enb": "/root/enb/config/enb.cfg",
        "mme": "/root/mme/config/mme.cfg",
        "ims": "/root/mme/config/ims.cfg",
        "ue": "/root/ue/config/ue.cfg",
        "rf_driver": "/root/enb/config/rf_driver/config.cfg",
    }

    LOG_PATHS = {
        "enb": "/tmp/enb0.log",
        "mme": "/tmp/mme0.log",
        "ims": "/tmp/ims0.log",
        "ots": "/var/log/lte/ots.log",
    }

    def __init__(
        self,
        host: str,
        username: str = "root",
        password: str = "toor",
        port: int = 22,
        timeout: float = 10.0,
    ):
        """Initialize SSH client.

        Args:
            host: Callbox IP address or hostname.
            username: SSH username (default: root).
            password: SSH password (default: toor).
            port: SSH port (default: 22).
            timeout: Command timeout in seconds.
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self._connected = False

    def connect(self) -> bool:
        """Test SSH connectivity.

        Returns:
            True if connection successful.

        Raises:
            ConnectionError: If SSH connection fails.
        """
        try:
            result = self._run_command("echo connected")
            self._connected = "connected" in result
            if self._connected:
                logger.info(f"SSH connected to {self.host}")
            return self._connected
        except Exception as e:
            raise ConnectionError(f"SSH connection failed: {e}") from e

    def close(self) -> None:
        """Close SSH connection (no-op for subprocess-based SSH)."""
        self._connected = False

    @property
    def connected(self) -> bool:
        """Return connection status."""
        return self._connected

    def _run_command(self, command: str, timeout: float | None = None) -> str:
        """Run a command via SSH.

        Args:
            command: Shell command to execute.
            timeout: Command timeout (uses default if None).

        Returns:
            Command output (stdout).

        Raises:
            RuntimeError: If command fails.
        """
        ssh_cmd = [
            "sshpass", "-p", self.password,
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR",
            "-p", str(self.port),
            f"{self.username}@{self.host}",
            command,
        ]

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )

            if result.returncode != 0 and result.stderr:
                logger.debug(f"SSH command warning: {result.stderr}")

            return result.stdout

        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"SSH command timed out: {command}") from e
        except FileNotFoundError:
            raise RuntimeError(
                "sshpass not found. Install with: brew install hudochenkov/sshpass/sshpass (macOS) "
                "or apt install sshpass (Linux)"
            )
        except Exception as e:
            raise RuntimeError(f"SSH command failed: {e}") from e

    def _run_scp(
        self,
        source: str,
        destination: str,
        download: bool = True,
        timeout: float | None = None,
    ) -> bool:
        """Transfer files via SCP.

        Args:
            source: Source path.
            destination: Destination path.
            download: True for download, False for upload.
            timeout: Transfer timeout.

        Returns:
            True if successful.
        """
        if download:
            remote_path = f"{self.username}@{self.host}:{source}"
            local_path = destination
            scp_cmd = [
                "sshpass", "-p", self.password,
                "scp",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "LogLevel=ERROR",
                "-P", str(self.port),
                remote_path,
                local_path,
            ]
        else:
            local_path = source
            remote_path = f"{self.username}@{self.host}:{destination}"
            scp_cmd = [
                "sshpass", "-p", self.password,
                "scp",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "LogLevel=ERROR",
                "-P", str(self.port),
                local_path,
                remote_path,
            ]

        try:
            result = subprocess.run(
                scp_cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout * 10,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"SCP failed: {e}")
            return False

    # ══════════════════════════════════════════════════════════════════════════
    # SYSTEM INFORMATION
    # ══════════════════════════════════════════════════════════════════════════

    def get_hostname(self) -> str:
        """Get the Callbox hostname."""
        return self._run_command("hostname").strip()

    def get_os_info(self) -> dict[str, str]:
        """Get OS information.

        Returns:
            Dictionary with os_name, os_version, kernel.
        """
        info = {
            "os_name": "unknown",
            "os_version": "unknown",
            "kernel": "unknown",
        }

        try:
            release = self._run_command(
                "cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null"
            )
            if "NAME=" in release:
                match = re.search(r'NAME="?([^"\n]+)"?', release)
                if match:
                    info["os_name"] = match.group(1)
            if "VERSION=" in release:
                match = re.search(r'VERSION="?([^"\n]+)"?', release)
                if match:
                    info["os_version"] = match.group(1)

            kernel = self._run_command("uname -r").strip()
            if kernel:
                info["kernel"] = kernel

        except Exception as e:
            logger.debug(f"Could not get OS info: {e}")

        return info

    def get_amarisoft_version(self) -> str:
        """Get installed Amarisoft software version."""
        try:
            result = self._run_command(
                "ls -la /root/enb 2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}'"
            )
            version = result.strip().split("\n")[0] if result.strip() else "unknown"
            return version
        except Exception:
            return "unknown"

    def get_cpu_info(self) -> dict[str, Any]:
        """Get CPU information.

        Returns:
            Dictionary with model, cores, threads, architecture.
        """
        info = {
            "model": "unknown",
            "cores": 0,
            "threads": 0,
            "architecture": "unknown",
        }

        try:
            cpuinfo = self._run_command("cat /proc/cpuinfo")

            model_match = re.search(r"model name\s*:\s*(.+)", cpuinfo)
            if model_match:
                info["model"] = model_match.group(1).strip()

            cores = len(re.findall(r"^processor\s*:", cpuinfo, re.MULTILINE))
            info["threads"] = cores

            core_match = re.search(r"cpu cores\s*:\s*(\d+)", cpuinfo)
            if core_match:
                info["cores"] = int(core_match.group(1))
            else:
                info["cores"] = cores

            arch = self._run_command("uname -m").strip()
            info["architecture"] = arch

        except Exception as e:
            logger.debug(f"Could not get CPU info: {e}")

        return info

    def get_motherboard_info(self) -> str:
        """Get motherboard/system information."""
        try:
            result = self._run_command(
                "cat /sys/class/dmi/id/product_name 2>/dev/null"
            )
            return result.strip() if result.strip() else "unknown"
        except Exception:
            return "unknown"

    def get_system_info(self) -> SystemInfo:
        """Get comprehensive system information.

        Returns:
            SystemInfo object with all available information.
        """
        os_info = self.get_os_info()
        cpu_info = self.get_cpu_info()
        memory = self.get_memory_usage()
        disk = self.get_disk_usage()

        return SystemInfo(
            hostname=self.get_hostname(),
            os_name=os_info.get("os_name", "unknown"),
            os_version=os_info.get("os_version", "unknown"),
            kernel=os_info.get("kernel", "unknown"),
            motherboard=self.get_motherboard_info(),
            amarisoft_version=self.get_amarisoft_version(),
            sdr_cards=self.get_sdr_info(),
            rf_config=self.get_rf_config(),
            cpu_model=cpu_info.get("model", "unknown"),
            cpu_cores=cpu_info.get("cores", 0),
            memory_total_gb=memory.get("total_gb", 0.0),
            disk_total_gb=disk.get("total_gb", 0.0),
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SYSTEM RESOURCES
    # ══════════════════════════════════════════════════════════════════════════

    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage.

        Returns:
            CPU usage as percentage (0-100).
        """
        try:
            result = self._run_command(
                "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1"
            )
            usage = result.strip()
            if usage:
                return float(usage)

            result = self._run_command(
                "grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage}'"
            )
            return float(result.strip()) if result.strip() else 0.0

        except Exception as e:
            logger.debug(f"Could not get CPU usage: {e}")
            return 0.0

    def get_memory_usage(self) -> dict[str, Any]:
        """Get memory usage information.

        Returns:
            Dictionary with total, used, free, percentage.
        """
        info = {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "available_gb": 0.0,
            "percent_used": 0.0,
        }

        try:
            result = self._run_command("free -b")

            mem_line = None
            for line in result.split("\n"):
                if line.startswith("Mem:"):
                    mem_line = line
                    break

            if mem_line:
                parts = mem_line.split()
                total = int(parts[1])
                used = int(parts[2])
                free = int(parts[3])
                available = int(parts[6]) if len(parts) > 6 else free

                info["total_gb"] = round(total / (1024**3), 2)
                info["used_gb"] = round(used / (1024**3), 2)
                info["free_gb"] = round(free / (1024**3), 2)
                info["available_gb"] = round(available / (1024**3), 2)
                info["percent_used"] = round((used / total) * 100, 1) if total > 0 else 0.0

        except Exception as e:
            logger.debug(f"Could not get memory usage: {e}")

        return info

    def get_disk_usage(self, path: str = "/") -> dict[str, Any]:
        """Get disk usage information.

        Args:
            path: Path to check disk usage for.

        Returns:
            Dictionary with total, used, free, percentage.
        """
        info = {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "percent_used": 0.0,
            "mount_point": path,
        }

        try:
            result = self._run_command(f"df -B1 {path} | tail -1")
            parts = result.split()

            if len(parts) >= 4:
                total = int(parts[1])
                used = int(parts[2])
                free = int(parts[3])

                info["total_gb"] = round(total / (1024**3), 2)
                info["used_gb"] = round(used / (1024**3), 2)
                info["free_gb"] = round(free / (1024**3), 2)
                info["percent_used"] = round((used / total) * 100, 1) if total > 0 else 0.0

        except Exception as e:
            logger.debug(f"Could not get disk usage: {e}")

        return info

    def get_temperature(self) -> dict[str, Any]:
        """Get system temperature readings.

        Returns:
            Dictionary with CPU and other sensor temperatures.
        """
        temps = {
            "cpu": None,
            "sensors": [],
        }

        try:
            result = self._run_command("cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null")
            if result.strip():
                for i, line in enumerate(result.strip().split("\n")):
                    try:
                        temp_c = int(line) / 1000
                        temps["sensors"].append({
                            "zone": i,
                            "temp_c": temp_c,
                        })
                        if temps["cpu"] is None:
                            temps["cpu"] = temp_c
                    except ValueError:
                        pass

            sensors_result = self._run_command("sensors 2>/dev/null | grep -E 'Core|temp'")
            if sensors_result.strip():
                for line in sensors_result.strip().split("\n"):
                    match = re.search(r"(\+[\d.]+)°C", line)
                    if match:
                        name = line.split(":")[0].strip() if ":" in line else "sensor"
                        temps["sensors"].append({
                            "name": name,
                            "temp_c": float(match.group(1)),
                        })

        except Exception as e:
            logger.debug(f"Could not get temperature: {e}")

        return temps

    def get_load_average(self) -> dict[str, float]:
        """Get system load average.

        Returns:
            Dictionary with 1min, 5min, 15min load averages.
        """
        load = {
            "1min": 0.0,
            "5min": 0.0,
            "15min": 0.0,
        }

        try:
            result = self._run_command("cat /proc/loadavg")
            parts = result.split()
            if len(parts) >= 3:
                load["1min"] = float(parts[0])
                load["5min"] = float(parts[1])
                load["15min"] = float(parts[2])
        except Exception as e:
            logger.debug(f"Could not get load average: {e}")

        return load

    def get_uptime(self) -> dict[str, Any]:
        """Get system uptime.

        Returns:
            Dictionary with uptime in seconds, formatted string, and boot time.
        """
        info = {
            "seconds": 0,
            "formatted": "unknown",
            "boot_time": None,
        }

        try:
            result = self._run_command("cat /proc/uptime")
            uptime_seconds = float(result.split()[0])
            info["seconds"] = int(uptime_seconds)

            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)

            if days > 0:
                info["formatted"] = f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                info["formatted"] = f"{hours}h {minutes}m"
            else:
                info["formatted"] = f"{minutes}m"

            boot_result = self._run_command("uptime -s 2>/dev/null")
            if boot_result.strip():
                info["boot_time"] = boot_result.strip()

        except Exception as e:
            logger.debug(f"Could not get uptime: {e}")

        return info

    # ══════════════════════════════════════════════════════════════════════════
    # HARDWARE: SDR CARDS
    # ══════════════════════════════════════════════════════════════════════════

    def get_sdr_info(self) -> list[SDRCard]:
        """Get SDR card information from OTS logs.

        Returns:
            List of SDRCard objects (deduplicated by serial number).
        """
        sdr_cards = []
        seen_serials: set[str] = set()

        try:
            log_output = self._run_command(
                "grep -A10 'Device /dev/sdr' /var/log/lte/ots.log 2>/dev/null | tail -50"
            )

            if not log_output:
                return sdr_cards

            devices = re.split(r"=== Device /dev/sdr(\d+) ===", log_output)

            for i in range(1, len(devices), 2):
                device_id = int(devices[i])
                device_info = devices[i + 1] if i + 1 < len(devices) else ""

                card = self._parse_sdr_info(device_info, device_id)
                if card and card.serial not in seen_serials:
                    sdr_cards.append(card)
                    seen_serials.add(card.serial)

        except Exception as e:
            logger.debug(f"Could not get SDR info: {e}")

        return sdr_cards

    def _parse_sdr_info(self, log_text: str, device_id: int) -> SDRCard | None:
        """Parse SDR info from log text."""
        board_id_match = re.search(r"Board ID:\s*(0x[0-9a-fA-F]+)\s*\((\w+)\)", log_text)
        serial_match = re.search(r"Serial\s*'([^']+)'", log_text)
        fpga_match = re.search(r"FPGA revision:\s*([^\n(]+)", log_text)
        pcie_match = re.search(r"PCIe.*gen(\d+)\s*x(\d+)", log_text)
        board_rev_match = re.search(r"Board revision:\s*(0x[0-9a-fA-F]+)", log_text)

        if not board_id_match:
            return None

        return SDRCard(
            device_id=device_id,
            board_id=board_id_match.group(1),
            board_type=board_id_match.group(2),
            serial=serial_match.group(1) if serial_match else "unknown",
            fpga_revision=fpga_match.group(1).strip() if fpga_match else "unknown",
            board_revision=board_rev_match.group(1) if board_rev_match else "0x0",
            pcie_gen=int(pcie_match.group(1)) if pcie_match else 2,
            pcie_lanes=int(pcie_match.group(2)) if pcie_match else 1,
        )

    def list_sdr_devices(self) -> list[str]:
        """List available SDR device files.

        Returns:
            List of SDR device paths (e.g., ['/dev/sdr0', '/dev/sdr1']).
        """
        devices = []
        try:
            result = self._run_command("ls -1 /dev/sdr* 2>/dev/null")
            for line in result.strip().split("\n"):
                if line.startswith("/dev/sdr"):
                    devices.append(line)
        except Exception as e:
            logger.debug(f"Could not list SDR devices: {e}")
        return devices

    def get_rf_config(self) -> dict[str, Any]:
        """Get current RF configuration (tx_gain, rx_gain, etc).

        Returns:
            Dictionary with RF settings.
        """
        config: dict[str, Any] = {
            "tx_gain": None,
            "rx_gain": None,
        }

        try:
            result = self._run_command(
                "grep -E '^tx_gain:|^rx_gain:' /root/enb/config/rf_driver/config.cfg 2>/dev/null"
            )

            for line in result.strip().split("\n"):
                if "tx_gain:" in line:
                    match = re.search(r"tx_gain:\s*([0-9.]+)", line)
                    if match:
                        config["tx_gain"] = float(match.group(1))
                elif "rx_gain:" in line:
                    match = re.search(r"rx_gain:\s*([0-9.]+)", line)
                    if match:
                        config["rx_gain"] = float(match.group(1))

        except Exception as e:
            logger.debug(f"Could not get RF config: {e}")

        return config

    def reset_sdr(self, device_id: int = 0) -> bool:
        """Reset an SDR device.

        Args:
            device_id: SDR device ID to reset (default 0).

        Returns:
            True if reset successful.

        Note:
            This stops services, resets the device, and restarts services.
        """
        try:
            logger.info(f"Resetting SDR device {device_id}...")

            self._run_command("systemctl stop lte.service")

            self._run_command(f"echo 1 > /sys/class/sdr/sdr{device_id}/reset 2>/dev/null")

            import time
            time.sleep(2)

            self._run_command("systemctl start lte.service")

            logger.info(f"SDR device {device_id} reset complete")
            return True

        except Exception as e:
            logger.error(f"SDR reset failed: {e}")
            return False

    # ══════════════════════════════════════════════════════════════════════════
    # HARDWARE: PCIE DEVICES
    # ══════════════════════════════════════════════════════════════════════════

    def list_pcie_devices(self) -> list[PCIeDevice]:
        """List all PCIe devices.

        Returns:
            List of PCIeDevice objects.
        """
        devices = []

        try:
            result = self._run_command("lspci -vmm 2>/dev/null")

            current_device: dict[str, str] = {}
            for line in result.split("\n"):
                if not line.strip():
                    if current_device:
                        devices.append(PCIeDevice(
                            slot=current_device.get("Slot", ""),
                            device_class=current_device.get("Class", ""),
                            vendor=current_device.get("Vendor", ""),
                            device=current_device.get("Device", ""),
                            driver=current_device.get("Driver"),
                        ))
                        current_device = {}
                    continue

                if ":" in line:
                    key, value = line.split(":", 1)
                    current_device[key.strip()] = value.strip()

            if current_device:
                devices.append(PCIeDevice(
                    slot=current_device.get("Slot", ""),
                    device_class=current_device.get("Class", ""),
                    vendor=current_device.get("Vendor", ""),
                    device=current_device.get("Device", ""),
                    driver=current_device.get("Driver"),
                ))

        except Exception as e:
            logger.debug(f"Could not list PCIe devices: {e}")

        return devices

    def get_sdr_pcie_info(self) -> list[dict[str, Any]]:
        """Get PCIe information specifically for SDR cards.

        Returns:
            List of SDR PCIe device info dictionaries.
        """
        sdr_devices = []

        try:
            result = self._run_command("lspci -v 2>/dev/null | grep -A15 -i 'amari\\|sdr'")

            if result.strip():
                for block in result.split("\n\n"):
                    if "amari" in block.lower() or "sdr" in block.lower():
                        slot_match = re.match(r"([0-9a-f:\.]+)\s+(.+)", block)
                        if slot_match:
                            sdr_devices.append({
                                "slot": slot_match.group(1),
                                "description": slot_match.group(2),
                                "details": block,
                            })

        except Exception as e:
            logger.debug(f"Could not get SDR PCIe info: {e}")

        return sdr_devices

    # ══════════════════════════════════════════════════════════════════════════
    # HARDWARE: USB DEVICES
    # ══════════════════════════════════════════════════════════════════════════

    def list_usb_devices(self) -> list[USBDevice]:
        """List all USB devices.

        Returns:
            List of USBDevice objects.
        """
        devices = []

        try:
            result = self._run_command("lsusb 2>/dev/null")

            for line in result.strip().split("\n"):
                if not line.strip():
                    continue

                match = re.match(
                    r"Bus (\d+) Device (\d+): ID ([0-9a-fA-F]+):([0-9a-fA-F]+)\s*(.*)",
                    line
                )
                if match:
                    devices.append(USBDevice(
                        bus=match.group(1),
                        device=match.group(2),
                        vendor_id=match.group(3),
                        product_id=match.group(4),
                        description=match.group(5).strip(),
                    ))

        except Exception as e:
            logger.debug(f"Could not list USB devices: {e}")

        return devices

    # ══════════════════════════════════════════════════════════════════════════
    # CONFIGURATION MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def list_config_files(self) -> dict[str, list[str]]:
        """List all available configuration files.

        Returns:
            Dictionary mapping config types to file lists.
        """
        configs: dict[str, list[str]] = {
            "enb": [],
            "mme": [],
            "ims": [],
            "ue": [],
            "rf_driver": [],
            "other": [],
        }

        try:
            for name, path in self.CONFIG_PATHS.items():
                dir_path = os.path.dirname(path)
                result = self._run_command(f"ls -1 {dir_path}/*.cfg 2>/dev/null")
                for line in result.strip().split("\n"):
                    if line.endswith(".cfg"):
                        configs[name].append(line)

            for path in ["/root/enb/config", "/root/mme/config"]:
                result = self._run_command(f"find {path} -name '*.cfg' 2>/dev/null")
                for line in result.strip().split("\n"):
                    if line.strip() and line not in [f for files in configs.values() for f in files]:
                        configs["other"].append(line)

        except Exception as e:
            logger.debug(f"Could not list config files: {e}")

        return configs

    def get_config_file(self, config_name: str) -> str:
        """Read a configuration file.

        Args:
            config_name: Config name ('enb', 'mme', 'ims', 'ue', 'rf_driver')
                        or full path to config file.

        Returns:
            Configuration file contents.

        Raises:
            ValueError: If config name is invalid.
            RuntimeError: If file cannot be read.
        """
        if config_name in self.CONFIG_PATHS:
            path = self.CONFIG_PATHS[config_name]
        elif config_name.startswith("/"):
            path = config_name
        else:
            raise ValueError(
                f"Unknown config '{config_name}'. "
                f"Use: {list(self.CONFIG_PATHS.keys())} or full path"
            )

        result = self._run_command(f"cat {path}")
        if not result.strip():
            raise RuntimeError(f"Could not read config file: {path}")

        return result

    def backup_config(self, backup_dir: str, include_rf: bool = True) -> list[str]:
        """Backup all configuration files.

        Args:
            backup_dir: Local directory to save backups.
            include_rf: Include RF driver config.

        Returns:
            List of backed up file paths.
        """
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backed_up = []

        configs_to_backup = ["enb", "mme", "ims", "ue"]
        if include_rf:
            configs_to_backup.append("rf_driver")

        for config_name in configs_to_backup:
            try:
                path = self.CONFIG_PATHS[config_name]
                filename = f"{config_name}_{timestamp}.cfg"
                local_path = os.path.join(backup_dir, filename)

                if self._run_scp(path, local_path, download=True):
                    backed_up.append(local_path)
                    logger.info(f"Backed up {config_name} -> {local_path}")
                else:
                    content = self.get_config_file(config_name)
                    with open(local_path, "w") as f:
                        f.write(content)
                    backed_up.append(local_path)
                    logger.info(f"Backed up {config_name} -> {local_path}")

            except Exception as e:
                logger.warning(f"Could not backup {config_name}: {e}")

        return backed_up

    def restore_config(self, local_file: str, config_name: str) -> bool:
        """Restore a configuration file.

        Args:
            local_file: Local config file path.
            config_name: Target config name ('enb', 'mme', etc.).

        Returns:
            True if restore successful.
        """
        if config_name not in self.CONFIG_PATHS:
            raise ValueError(f"Unknown config '{config_name}'")

        remote_path = self.CONFIG_PATHS[config_name]

        self._run_command(f"cp {remote_path} {remote_path}.bak")

        success = self._run_scp(local_file, remote_path, download=False)
        if success:
            logger.info(f"Restored {config_name} from {local_file}")
        return success

    # ══════════════════════════════════════════════════════════════════════════
    # FILE TRANSFER
    # ══════════════════════════════════════════════════════════════════════════

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the Callbox.

        Args:
            remote_path: Path on the Callbox.
            local_path: Local destination path.

        Returns:
            True if download successful.
        """
        logger.info(f"Downloading {remote_path} -> {local_path}")
        return self._run_scp(remote_path, local_path, download=True)

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a file to the Callbox.

        Args:
            local_path: Local source path.
            remote_path: Path on the Callbox.

        Returns:
            True if upload successful.
        """
        logger.info(f"Uploading {local_path} -> {remote_path}")
        return self._run_scp(local_path, remote_path, download=False)

    def get_iq_samples(
        self,
        remote_path: str,
        local_path: str,
        timeout: float = 300.0,
    ) -> bool:
        """Download IQ sample files (typically large).

        Args:
            remote_path: Path to IQ file on Callbox.
            local_path: Local destination path.
            timeout: Transfer timeout (default 5 minutes for large files).

        Returns:
            True if download successful.
        """
        logger.info(f"Downloading IQ samples {remote_path} -> {local_path}")
        return self._run_scp(remote_path, local_path, download=True, timeout=timeout)

    def list_iq_files(self, directory: str = "/tmp") -> list[dict[str, Any]]:
        """List IQ sample files on the Callbox.

        Args:
            directory: Directory to search.

        Returns:
            List of file info dictionaries.
        """
        files = []

        try:
            result = self._run_command(
                f"ls -lh {directory}/*.bin {directory}/*iq* 2>/dev/null"
            )

            for line in result.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) >= 9:
                    files.append({
                        "path": parts[-1],
                        "size": parts[4],
                        "date": f"{parts[5]} {parts[6]} {parts[7]}",
                    })

        except Exception as e:
            logger.debug(f"Could not list IQ files: {e}")

        return files

    # ══════════════════════════════════════════════════════════════════════════
    # NETWORK CONFIGURATION
    # ══════════════════════════════════════════════════════════════════════════

    def get_network_config(self) -> dict[str, Any]:
        """Get network configuration.

        Returns:
            Dictionary with interfaces, routes, and DNS info.
        """
        config: dict[str, Any] = {
            "interfaces": [],
            "routes": [],
            "dns": [],
            "gateway": None,
        }

        try:
            ip_result = self._run_command("ip -o addr show")
            for line in ip_result.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) >= 4:
                    iface_name = parts[1]
                    existing = next(
                        (i for i in config["interfaces"] if i["name"] == iface_name),
                        None
                    )
                    if not existing:
                        existing = NetworkInterface(name=iface_name)
                        config["interfaces"].append(existing)

                    if "inet " in line:
                        match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", line)
                        if match:
                            existing.ipv4_address = match.group(1)
                            existing.ipv4_netmask = match.group(2)
                    elif "inet6 " in line:
                        match = re.search(r"inet6 ([a-f0-9:]+)/(\d+)", line)
                        if match:
                            existing.ipv6_address = match.group(1)

            route_result = self._run_command("ip route")
            for line in route_result.strip().split("\n"):
                if "default" in line:
                    match = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", line)
                    if match:
                        config["gateway"] = match.group(1)
                config["routes"].append(line.strip())

            dns_result = self._run_command("cat /etc/resolv.conf")
            for line in dns_result.split("\n"):
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2:
                        config["dns"].append(parts[1])

            config["interfaces"] = [
                i.to_dict() if isinstance(i, NetworkInterface) else i
                for i in config["interfaces"]
            ]

        except Exception as e:
            logger.debug(f"Could not get network config: {e}")

        return config

    def ping(self, host: str, count: int = 4, timeout: int = 5) -> dict[str, Any]:
        """Ping a host from the Callbox.

        Args:
            host: Host to ping.
            count: Number of ping packets.
            timeout: Timeout in seconds.

        Returns:
            Dictionary with success status and statistics.
        """
        result_info: dict[str, Any] = {
            "success": False,
            "host": host,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_percent": 100.0,
            "rtt_min_ms": None,
            "rtt_avg_ms": None,
            "rtt_max_ms": None,
        }

        try:
            result = self._run_command(
                f"ping -c {count} -W {timeout} {host} 2>&1",
                timeout=float(timeout * count + 5)
            )

            loss_match = re.search(r"(\d+)% packet loss", result)
            if loss_match:
                result_info["packet_loss_percent"] = float(loss_match.group(1))
                result_info["packets_received"] = int(
                    count * (100 - result_info["packet_loss_percent"]) / 100
                )
                result_info["success"] = result_info["packet_loss_percent"] < 100

            rtt_match = re.search(r"rtt min/avg/max[^=]*= ([\d.]+)/([\d.]+)/([\d.]+)", result)
            if rtt_match:
                result_info["rtt_min_ms"] = float(rtt_match.group(1))
                result_info["rtt_avg_ms"] = float(rtt_match.group(2))
                result_info["rtt_max_ms"] = float(rtt_match.group(3))

        except Exception as e:
            logger.debug(f"Ping failed: {e}")

        return result_info

    def traceroute(self, host: str, max_hops: int = 30) -> list[dict[str, Any]]:
        """Run traceroute to a host.

        Args:
            host: Target host.
            max_hops: Maximum number of hops.

        Returns:
            List of hop info dictionaries.
        """
        hops = []

        try:
            result = self._run_command(
                f"traceroute -m {max_hops} -w 2 {host} 2>&1",
                timeout=60.0
            )

            for line in result.strip().split("\n"):
                if line.strip() and not line.startswith("traceroute"):
                    hop_match = re.match(r"\s*(\d+)\s+(.+)", line)
                    if hop_match:
                        hops.append({
                            "hop": int(hop_match.group(1)),
                            "details": hop_match.group(2).strip(),
                        })

        except Exception as e:
            logger.debug(f"Traceroute failed: {e}")

        return hops

    # ══════════════════════════════════════════════════════════════════════════
    # TIME AND SYNCHRONIZATION
    # ══════════════════════════════════════════════════════════════════════════

    def get_time_info(self) -> dict[str, Any]:
        """Get system time and NTP status.

        Returns:
            Dictionary with current time, timezone, and NTP info.
        """
        info: dict[str, Any] = {
            "current_time": None,
            "timezone": None,
            "ntp_enabled": False,
            "ntp_synchronized": False,
            "ntp_server": None,
        }

        try:
            date_result = self._run_command("date '+%Y-%m-%d %H:%M:%S %Z'")
            info["current_time"] = date_result.strip()

            tz_result = self._run_command("cat /etc/timezone 2>/dev/null || timedatectl show --property=Timezone --value 2>/dev/null")
            info["timezone"] = tz_result.strip() if tz_result.strip() else "unknown"

            timedatectl = self._run_command("timedatectl status 2>/dev/null")
            if "NTP service: active" in timedatectl or "NTP enabled: yes" in timedatectl:
                info["ntp_enabled"] = True
            if "System clock synchronized: yes" in timedatectl:
                info["ntp_synchronized"] = True

            chrony = self._run_command("chronyc sources 2>/dev/null | head -5")
            if chrony.strip() and "^*" in chrony:
                info["ntp_synchronized"] = True
                for line in chrony.split("\n"):
                    if "^*" in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            info["ntp_server"] = parts[1]
                        break

        except Exception as e:
            logger.debug(f"Could not get time info: {e}")

        return info

    def sync_time(self, ntp_server: str | None = None) -> bool:
        """Synchronize system time via NTP.

        Args:
            ntp_server: NTP server to use (uses default if None).

        Returns:
            True if sync successful.
        """
        try:
            if ntp_server:
                self._run_command(f"ntpdate -u {ntp_server} 2>&1")
            else:
                self._run_command("chronyc makestep 2>&1 || ntpdate -u pool.ntp.org 2>&1")

            time_info = self.get_time_info()
            return time_info.get("ntp_synchronized", False)

        except Exception as e:
            logger.error(f"Time sync failed: {e}")
            return False

    def set_timezone(self, timezone: str) -> bool:
        """Set system timezone.

        Args:
            timezone: Timezone string (e.g., 'America/Los_Angeles').

        Returns:
            True if successful.
        """
        try:
            self._run_command(f"timedatectl set-timezone {timezone}")
            return True
        except Exception as e:
            logger.error(f"Failed to set timezone: {e}")
            return False

    # ══════════════════════════════════════════════════════════════════════════
    # SERVICE MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def restart_services(self) -> str:
        """Restart all LTE services.

        Returns:
            Command output.
        """
        logger.info("Restarting LTE services...")
        return self._run_command("systemctl restart lte.service")

    def stop_services(self) -> str:
        """Stop all LTE services.

        Returns:
            Command output.
        """
        logger.info("Stopping LTE services...")
        return self._run_command("systemctl stop lte.service")

    def start_services(self) -> str:
        """Start all LTE services.

        Returns:
            Command output.
        """
        logger.info("Starting LTE services...")
        return self._run_command("systemctl start lte.service")

    def get_service_status(self) -> dict[str, bool]:
        """Get status of LTE services.

        Returns:
            Dictionary mapping service names to running status.
        """
        status = {
            "ltemme": False,
            "lteenb": False,
            "lteims": False,
            "ltembmsgw": False,
        }

        try:
            result = self._run_command("ss -tlnp | grep 900")

            if "ltemme" in result:
                status["ltemme"] = True
            if "lteenb" in result:
                status["lteenb"] = True
            if "lteims" in result:
                status["lteims"] = True
            if "ltembmsgw" in result:
                status["ltembmsgw"] = True

        except Exception as e:
            logger.debug(f"Could not get service status: {e}")

        return status

    def get_listening_ports(self) -> list[dict[str, Any]]:
        """Get list of listening ports for LTE services.

        Returns:
            List of port info dictionaries.
        """
        ports = []

        try:
            result = self._run_command("ss -tlnp | grep 900")

            for line in result.strip().split("\n"):
                if not line.strip():
                    continue

                port_match = re.search(r"\*:(\d+)", line)
                proc_match = re.search(r'users:\(\("([^"]+)"', line)

                if port_match:
                    ports.append({
                        "port": int(port_match.group(1)),
                        "process": proc_match.group(1) if proc_match else "unknown",
                    })

        except Exception as e:
            logger.debug(f"Could not get listening ports: {e}")

        return ports

    # ══════════════════════════════════════════════════════════════════════════
    # LOG ACCESS
    # ══════════════════════════════════════════════════════════════════════════

    def get_logs(self, lines: int = 100, service: str | None = None) -> str:
        """Get recent log entries.

        Args:
            lines: Number of lines to retrieve.
            service: Filter by service (enb, mme, ims). None for all.

        Returns:
            Log content as string.
        """
        if service and service in self.LOG_PATHS:
            log_file = self.LOG_PATHS[service]
        else:
            log_file = self.LOG_PATHS["ots"]

        return self._run_command(f"tail -n {lines} {log_file} 2>/dev/null")

    def get_log_errors(self, lines: int = 500) -> list[str]:
        """Get recent error entries from logs.

        Args:
            lines: Number of lines to search.

        Returns:
            List of error lines.
        """
        errors = []

        try:
            result = self._run_command(
                f"tail -n {lines} /var/log/lte/ots.log 2>/dev/null | grep -iE 'error|fail|warn'"
            )
            errors = [line for line in result.strip().split("\n") if line.strip()]
        except Exception as e:
            logger.debug(f"Could not get log errors: {e}")

        return errors

    def clear_logs(self, service: str | None = None) -> bool:
        """Clear log files.

        Args:
            service: Service to clear logs for (None for all).

        Returns:
            True if successful.
        """
        try:
            if service and service in self.LOG_PATHS:
                self._run_command(f"truncate -s 0 {self.LOG_PATHS[service]}")
            else:
                for path in self.LOG_PATHS.values():
                    self._run_command(f"truncate -s 0 {path} 2>/dev/null")
            return True
        except Exception as e:
            logger.error(f"Failed to clear logs: {e}")
            return False

    def get_license_info(self) -> dict[str, Any]:
        """Get license configuration.

        Returns:
            Dictionary with license server config and local license info.
        """
        info: dict[str, Any] = {
            "license_server": None,
            "local_licenses": [],
        }

        try:
            server_cfg = self._run_command("cat /root/.amarisoft/license_server.cfg 2>/dev/null")
            if server_cfg and "server_addr" in server_cfg:
                import json
                try:
                    info["license_server"] = json.loads(server_cfg)
                except json.JSONDecodeError:
                    pass

            for key_file in ["lteenb.key", "ltemme.key"]:
                key_info = self._run_command(
                    f"strings /root/.amarisoft/{key_file} 2>/dev/null | grep -E 'product|user|version'"
                )
                if key_info:
                    info["local_licenses"].append({
                        "file": key_file,
                        "content": key_info.strip(),
                    })

        except Exception as e:
            logger.debug(f"Could not get license info: {e}")

        return info

    # ══════════════════════════════════════════════════════════════════════════
    # DIAGNOSTICS
    # ══════════════════════════════════════════════════════════════════════════

    def run_diagnostics(self) -> dict[str, Any]:
        """Run comprehensive system diagnostics.

        Returns:
            Dictionary with diagnostic results.
        """
        logger.info("Running system diagnostics...")

        results: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "host": self.host,
            "checks": {},
            "warnings": [],
            "errors": [],
        }

        results["checks"]["ssh_connection"] = self.connected

        try:
            services = self.get_service_status()
            results["checks"]["services"] = services
            if not any(services.values()):
                results["errors"].append("No LTE services are running")
            elif not all(services.values()):
                stopped = [s for s, running in services.items() if not running]
                results["warnings"].append(f"Some services not running: {stopped}")
        except Exception as e:
            results["errors"].append(f"Service check failed: {e}")

        try:
            sdr_cards = self.get_sdr_info()
            results["checks"]["sdr_cards"] = len(sdr_cards)
            if not sdr_cards:
                results["errors"].append("No SDR cards detected")
        except Exception as e:
            results["errors"].append(f"SDR check failed: {e}")

        try:
            memory = self.get_memory_usage()
            results["checks"]["memory"] = memory
            if memory["percent_used"] > 90:
                results["warnings"].append(f"High memory usage: {memory['percent_used']}%")
        except Exception as e:
            results["warnings"].append(f"Memory check failed: {e}")

        try:
            disk = self.get_disk_usage()
            results["checks"]["disk"] = disk
            if disk["percent_used"] > 90:
                results["warnings"].append(f"High disk usage: {disk['percent_used']}%")
        except Exception as e:
            results["warnings"].append(f"Disk check failed: {e}")

        try:
            cpu = self.get_cpu_usage()
            results["checks"]["cpu_usage"] = cpu
            if cpu > 90:
                results["warnings"].append(f"High CPU usage: {cpu}%")
        except Exception as e:
            results["warnings"].append(f"CPU check failed: {e}")

        try:
            temps = self.get_temperature()
            results["checks"]["temperature"] = temps
            if temps.get("cpu") and temps["cpu"] > 80:
                results["warnings"].append(f"High CPU temperature: {temps['cpu']}°C")
        except Exception as e:
            results["warnings"].append(f"Temperature check failed: {e}")

        try:
            time_info = self.get_time_info()
            results["checks"]["time"] = time_info
            if not time_info.get("ntp_synchronized"):
                results["warnings"].append("System time not synchronized with NTP")
        except Exception as e:
            results["warnings"].append(f"Time check failed: {e}")

        try:
            errors = self.get_log_errors(lines=100)
            results["checks"]["recent_log_errors"] = len(errors)
            if errors:
                results["checks"]["sample_errors"] = errors[:5]
        except Exception as e:
            results["warnings"].append(f"Log check failed: {e}")

        results["status"] = "ERROR" if results["errors"] else ("WARNING" if results["warnings"] else "OK")

        return results

    def check_rf_status(self) -> dict[str, Any]:
        """Check RF hardware status.

        Returns:
            Dictionary with RF status information.
        """
        status: dict[str, Any] = {
            "sdr_devices": [],
            "rf_config": {},
            "errors": [],
        }

        try:
            sdr_devices = self.list_sdr_devices()
            status["sdr_devices"] = sdr_devices

            sdr_cards = self.get_sdr_info()
            status["sdr_cards"] = [card.to_dict() for card in sdr_cards]

            rf_config = self.get_rf_config()
            status["rf_config"] = rf_config

            for device in sdr_devices:
                result = self._run_command(f"cat /sys/class/sdr/{os.path.basename(device)}/status 2>/dev/null")
                if "error" in result.lower():
                    status["errors"].append(f"{device}: {result.strip()}")

        except Exception as e:
            status["errors"].append(f"RF status check failed: {e}")

        return status

    def get_process_list(self, filter_pattern: str = "lte") -> list[dict[str, Any]]:
        """Get running processes.

        Args:
            filter_pattern: Pattern to filter processes.

        Returns:
            List of process info dictionaries.
        """
        processes = []

        try:
            result = self._run_command(
                f"ps aux | grep -E '{filter_pattern}' | grep -v grep"
            )

            for line in result.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split(None, 10)
                if len(parts) >= 11:
                    processes.append({
                        "user": parts[0],
                        "pid": int(parts[1]),
                        "cpu_percent": float(parts[2]),
                        "mem_percent": float(parts[3]),
                        "command": parts[10],
                    })

        except Exception as e:
            logger.debug(f"Could not get process list: {e}")

        return processes

    # ══════════════════════════════════════════════════════════════════════════
    # CONTEXT MANAGER
    # ══════════════════════════════════════════════════════════════════════════

    def __enter__(self) -> "SSHClient":
        self.connect()
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return f"SSHClient({self.host}, {status})"
