"""Tests for SSHClient module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, mock_open
import subprocess

import pytest

from client.websocket.ssh import (
    SSHClient,
    SDRCard,
    SystemInfo,
    PCIeDevice,
    USBDevice,
    NetworkInterface,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def ssh_client():
    """Create an SSHClient instance without connecting."""
    return SSHClient("192.168.1.80", "root", "toor")


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for SSH commands."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )
        yield mock_run


# ══════════════════════════════════════════════════════════════════════════════
# DATACLASS TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestSDRCard:
    """Tests for SDRCard dataclass."""

    def test_sdr50_max_bandwidth(self):
        sdr = SDRCard(
            device_id=0,
            board_type="SDR50",
            board_id="0x4b01",
            serial="123456",
            fpga_revision="2024-01-01",
        )
        assert sdr.max_bandwidth_mhz == 50

    def test_sdr100_max_bandwidth(self):
        sdr = SDRCard(
            device_id=0,
            board_type="SDR100",
            board_id="0x4b02",
            serial="123456",
            fpga_revision="2024-01-01",
        )
        assert sdr.max_bandwidth_mhz == 100

    def test_to_dict(self):
        sdr = SDRCard(
            device_id=0,
            board_type="SDR50",
            board_id="0x4b01",
            serial="202405001019",
            fpga_revision="2024-07-02",
            pcie_gen=2,
            pcie_lanes=1,
        )
        d = sdr.to_dict()

        assert d["device_id"] == 0
        assert d["board_type"] == "SDR50"
        assert d["serial"] == "202405001019"
        assert d["pcie"] == "gen2 x1"
        assert d["max_bandwidth_mhz"] == 50


class TestPCIeDevice:
    """Tests for PCIeDevice dataclass."""

    def test_to_dict(self):
        pcie = PCIeDevice(
            slot="00:02.0",
            device_class="VGA",
            vendor="Intel",
            device="UHD Graphics",
            driver="i915",
        )
        d = pcie.to_dict()

        assert d["slot"] == "00:02.0"
        assert d["class"] == "VGA"
        assert d["vendor"] == "Intel"
        assert d["driver"] == "i915"


class TestUSBDevice:
    """Tests for USBDevice dataclass."""

    def test_to_dict(self):
        usb = USBDevice(
            bus="001",
            device="002",
            vendor_id="1d6b",
            product_id="0002",
            description="Linux Foundation 2.0 root hub",
        )
        d = usb.to_dict()

        assert d["bus"] == "001"
        assert d["vendor_id"] == "1d6b"
        assert d["description"] == "Linux Foundation 2.0 root hub"


class TestNetworkInterface:
    """Tests for NetworkInterface dataclass."""

    def test_to_dict(self):
        iface = NetworkInterface(
            name="eth0",
            ipv4_address="192.168.1.80",
            ipv4_netmask="24",
            state="UP",
        )
        d = iface.to_dict()

        assert d["name"] == "eth0"
        assert d["ipv4_address"] == "192.168.1.80"
        assert d["state"] == "UP"


class TestSystemInfo:
    """Tests for SystemInfo dataclass."""

    def test_to_dict_empty(self):
        info = SystemInfo()
        d = info.to_dict()

        assert d["hostname"] == "unknown"
        assert d["sdr_cards"] == []

    def test_to_dict_with_sdr(self):
        sdr = SDRCard(
            device_id=0,
            board_type="SDR50",
            board_id="0x4b01",
            serial="123456",
            fpga_revision="2024-01-01",
        )
        info = SystemInfo(hostname="callbox", sdr_cards=[sdr])
        d = info.to_dict()

        assert d["hostname"] == "callbox"
        assert len(d["sdr_cards"]) == 1
        assert d["sdr_cards"][0]["board_type"] == "SDR50"


# ══════════════════════════════════════════════════════════════════════════════
# SSH CLIENT TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestSSHClientInit:
    """Tests for SSHClient initialization."""

    def test_default_credentials(self):
        client = SSHClient("192.168.1.80")
        assert client.host == "192.168.1.80"
        assert client.username == "root"
        assert client.password == "toor"
        assert client.port == 22

    def test_custom_credentials(self):
        client = SSHClient(
            "10.0.0.1",
            username="admin",
            password="secret",
            port=2222,
        )
        assert client.host == "10.0.0.1"
        assert client.username == "admin"
        assert client.password == "secret"
        assert client.port == 2222


class TestSSHClientRunCommand:
    """Tests for SSHClient._run_command method."""

    def test_run_command_builds_correct_ssh_args(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "test output"

        result = ssh_client._run_command("echo hello")

        call_args = mock_subprocess.call_args[0][0]
        assert "sshpass" in call_args
        assert "-p" in call_args
        assert "toor" in call_args
        assert "ssh" in call_args
        assert "root@192.168.1.80" in call_args
        assert "echo hello" in call_args

    def test_run_command_returns_stdout(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "command output"

        result = ssh_client._run_command("echo test")

        assert result == "command output"

    def test_run_command_timeout(self, ssh_client, mock_subprocess):
        mock_subprocess.side_effect = subprocess.TimeoutExpired("cmd", 10)

        with pytest.raises(RuntimeError, match="timed out"):
            ssh_client._run_command("sleep 100")

    def test_run_command_sshpass_not_found(self, ssh_client, mock_subprocess):
        mock_subprocess.side_effect = FileNotFoundError()

        with pytest.raises(RuntimeError, match="sshpass not found"):
            ssh_client._run_command("echo test")


class TestSSHClientConnect:
    """Tests for SSHClient.connect method."""

    def test_connect_success(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "connected"

        result = ssh_client.connect()

        assert result is True
        assert ssh_client.connected is True

    def test_connect_failure(self, ssh_client, mock_subprocess):
        mock_subprocess.side_effect = Exception("Connection refused")

        with pytest.raises(ConnectionError):
            ssh_client.connect()


class TestSSHClientContextManager:
    """Tests for SSHClient context manager."""

    def test_context_manager(self, mock_subprocess):
        mock_subprocess.return_value.stdout = "connected"

        with SSHClient("192.168.1.80") as ssh:
            assert ssh.connected is True

        assert ssh.connected is False


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM INFORMATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestGetHostname:
    """Tests for get_hostname method."""

    def test_returns_hostname(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "callbox-001\n"

        result = ssh_client.get_hostname()

        assert result == "callbox-001"


class TestGetOsInfo:
    """Tests for get_os_info method."""

    def test_parses_os_release(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = """NAME="Fedora Linux"
VERSION="39 (Workstation Edition)"
"""

        def side_effect(cmd, **kwargs):
            if "os-release" in cmd[0] if isinstance(cmd, list) else "os-release" in cmd:
                return MagicMock(stdout="""NAME="Fedora Linux"
VERSION="39 (Workstation Edition)"
""", returncode=0)
            if "uname" in str(cmd):
                return MagicMock(stdout="6.11.9-100.fc39.x86_64\n", returncode=0)
            return MagicMock(stdout="", returncode=0)

        mock_subprocess.side_effect = side_effect

        result = ssh_client.get_os_info()

        assert "os_name" in result
        assert "kernel" in result


class TestGetCpuInfo:
    """Tests for get_cpu_info method."""

    def test_parses_cpuinfo(self, ssh_client, mock_subprocess):
        cpuinfo = """processor       : 0
model name      : Intel(R) Core(TM) i3-10105 CPU @ 3.70GHz
cpu cores       : 4
processor       : 1
model name      : Intel(R) Core(TM) i3-10105 CPU @ 3.70GHz
cpu cores       : 4
"""

        def side_effect(cmd, **kwargs):
            if "cpuinfo" in str(cmd):
                return MagicMock(stdout=cpuinfo, returncode=0)
            if "uname -m" in str(cmd):
                return MagicMock(stdout="x86_64\n", returncode=0)
            return MagicMock(stdout="", returncode=0)

        mock_subprocess.side_effect = side_effect

        result = ssh_client.get_cpu_info()

        assert "Intel" in result["model"]
        assert result["threads"] == 2
        assert result["architecture"] == "x86_64"


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM RESOURCES TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestGetCpuUsage:
    """Tests for get_cpu_usage method."""

    def test_returns_float(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "15.5"

        result = ssh_client.get_cpu_usage()

        assert isinstance(result, float)
        assert result == 15.5


class TestGetMemoryUsage:
    """Tests for get_memory_usage method."""

    def test_parses_free_output(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = """              total        used        free      shared  buff/cache   available
Mem:     8153726976  1815080960  5224644608    17821696  1113997312  6100217856
Swap:             0           0           0
"""

        result = ssh_client.get_memory_usage()

        assert "total_gb" in result
        assert "used_gb" in result
        assert "percent_used" in result
        assert result["total_gb"] > 0


class TestGetDiskUsage:
    """Tests for get_disk_usage method."""

    def test_parses_df_output(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "/dev/sda1 246533988352 16192929792 229075574784   8% /"

        result = ssh_client.get_disk_usage("/")

        assert "total_gb" in result
        assert "used_gb" in result
        assert result["mount_point"] == "/"


class TestGetTemperature:
    """Tests for get_temperature method."""

    def test_parses_thermal_zone(self, ssh_client, mock_subprocess):
        def side_effect(cmd, **kwargs):
            if "thermal_zone" in str(cmd):
                return MagicMock(stdout="45000\n50000\n", returncode=0)
            return MagicMock(stdout="", returncode=0)

        mock_subprocess.side_effect = side_effect

        result = ssh_client.get_temperature()

        assert result["cpu"] == 45.0
        assert len(result["sensors"]) >= 1


class TestGetLoadAverage:
    """Tests for get_load_average method."""

    def test_parses_loadavg(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "0.15 0.10 0.05 1/234 5678"

        result = ssh_client.get_load_average()

        assert result["1min"] == 0.15
        assert result["5min"] == 0.10
        assert result["15min"] == 0.05


class TestGetUptime:
    """Tests for get_uptime method."""

    def test_parses_uptime(self, ssh_client, mock_subprocess):
        def side_effect(cmd, **kwargs):
            if "proc/uptime" in str(cmd):
                return MagicMock(stdout="26481.15 104924.60", returncode=0)
            if "uptime -s" in str(cmd):
                return MagicMock(stdout="2024-01-01 10:00:00", returncode=0)
            return MagicMock(stdout="", returncode=0)

        mock_subprocess.side_effect = side_effect

        result = ssh_client.get_uptime()

        assert result["seconds"] == 26481
        assert "formatted" in result


# ══════════════════════════════════════════════════════════════════════════════
# SDR HARDWARE TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestGetSdrInfo:
    """Tests for get_sdr_info method."""

    def test_parses_ots_log(self, ssh_client, mock_subprocess):
        ots_log = """=== Device /dev/sdr0 ===
Board ID:       0x4b01 (SDR50)
Serial          '202405001019'
FPGA revision:  2024-07-02 15:35:40
Board revision: 0x0
PCIe: gen2 x1
"""
        mock_subprocess.return_value.stdout = ots_log

        result = ssh_client.get_sdr_info()

        assert len(result) == 1
        assert result[0].board_type == "SDR50"
        assert result[0].serial == "202405001019"
        assert result[0].pcie_gen == 2

    def test_deduplicates_by_serial(self, ssh_client, mock_subprocess):
        ots_log = """=== Device /dev/sdr0 ===
Board ID:       0x4b01 (SDR50)
Serial          '123456'
FPGA revision:  2024-07-02
=== Device /dev/sdr0 ===
Board ID:       0x4b01 (SDR50)
Serial          '123456'
FPGA revision:  2024-07-02
"""
        mock_subprocess.return_value.stdout = ots_log

        result = ssh_client.get_sdr_info()

        assert len(result) == 1


class TestListSdrDevices:
    """Tests for list_sdr_devices method."""

    def test_lists_devices(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "/dev/sdr0\n/dev/sdr1\n"

        result = ssh_client.list_sdr_devices()

        assert "/dev/sdr0" in result
        assert "/dev/sdr1" in result


class TestGetRfConfig:
    """Tests for get_rf_config method."""

    def test_parses_config(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = """tx_gain: 90.0
rx_gain: 60.0
"""

        result = ssh_client.get_rf_config()

        assert result["tx_gain"] == 90.0
        assert result["rx_gain"] == 60.0


# ══════════════════════════════════════════════════════════════════════════════
# PCIE AND USB TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestListPcieDevices:
    """Tests for list_pcie_devices method."""

    def test_parses_lspci(self, ssh_client, mock_subprocess):
        lspci_output = """Slot:	00:00.0
Class:	Host bridge
Vendor:	Intel Corporation
Device:	Device 9b53

Slot:	00:02.0
Class:	VGA compatible controller
Vendor:	Intel Corporation
Device:	CometLake-S GT2
"""
        mock_subprocess.return_value.stdout = lspci_output

        result = ssh_client.list_pcie_devices()

        assert len(result) == 2
        assert result[0].slot == "00:00.0"
        assert result[1].device_class == "VGA compatible controller"


class TestListUsbDevices:
    """Tests for list_usb_devices method."""

    def test_parses_lsusb(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = """Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
Bus 001 Device 002: ID 18d1:4eec Google Inc. Pixel 8 Pro
"""

        result = ssh_client.list_usb_devices()

        assert len(result) == 2
        assert result[0].vendor_id == "1d6b"
        assert result[1].description == "Google Inc. Pixel 8 Pro"


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION MANAGEMENT TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestGetConfigFile:
    """Tests for get_config_file method."""

    def test_reads_named_config(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "/* enb config */\n{...}"

        result = ssh_client.get_config_file("enb")

        assert "enb config" in result

    def test_reads_path_config(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "custom config"

        result = ssh_client.get_config_file("/root/custom.cfg")

        assert result == "custom config"

    def test_invalid_config_name(self, ssh_client):
        with pytest.raises(ValueError, match="Unknown config"):
            ssh_client.get_config_file("invalid")


class TestListConfigFiles:
    """Tests for list_config_files method."""

    def test_lists_configs(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "/root/enb/config/enb.cfg\n/root/enb/config/drb.cfg"

        result = ssh_client.list_config_files()

        assert "enb" in result


# ══════════════════════════════════════════════════════════════════════════════
# SERVICE MANAGEMENT TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestServiceManagement:
    """Tests for service management methods."""

    def test_restart_services(self, ssh_client, mock_subprocess):
        ssh_client.restart_services()
        assert "lte.service" in str(mock_subprocess.call_args)

    def test_stop_services(self, ssh_client, mock_subprocess):
        ssh_client.stop_services()
        assert "stop" in str(mock_subprocess.call_args)

    def test_start_services(self, ssh_client, mock_subprocess):
        ssh_client.start_services()
        assert "start" in str(mock_subprocess.call_args)


class TestGetServiceStatus:
    """Tests for get_service_status method."""

    def test_parses_status(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = """LISTEN  0  128  *:9000  *:*  users:(("ltemme",pid=1234))
LISTEN  0  128  *:9001  *:*  users:(("lteenb",pid=1235))
"""

        result = ssh_client.get_service_status()

        assert result["ltemme"] is True
        assert result["lteenb"] is True


class TestGetListeningPorts:
    """Tests for get_listening_ports method."""

    def test_parses_ports(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = """LISTEN  0  128  *:9000  *:*  users:(("ltemme",pid=1234))
LISTEN  0  128  *:9001  *:*  users:(("lteenb",pid=1235))
"""

        result = ssh_client.get_listening_ports()

        assert len(result) == 2
        assert result[0]["port"] == 9000
        assert result[0]["process"] == "ltemme"


# ══════════════════════════════════════════════════════════════════════════════
# NETWORK TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestPing:
    """Tests for ping method."""

    def test_successful_ping(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = """PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
--- 8.8.8.8 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3004ms
rtt min/avg/max/mdev = 10.123/15.456/20.789/3.456 ms
"""

        result = ssh_client.ping("8.8.8.8")

        assert result["success"] is True
        assert result["packet_loss_percent"] == 0
        assert result["rtt_avg_ms"] == 15.456

    def test_failed_ping(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = """--- 8.8.8.8 ping statistics ---
4 packets transmitted, 0 received, 100% packet loss, time 3004ms
"""

        result = ssh_client.ping("8.8.8.8")

        assert result["success"] is False
        assert result["packet_loss_percent"] == 100


class TestGetNetworkConfig:
    """Tests for get_network_config method."""

    def test_parses_config(self, ssh_client, mock_subprocess):
        def side_effect(cmd, **kwargs):
            if "ip -o addr" in str(cmd):
                return MagicMock(stdout="1: lo inet 127.0.0.1/8\n2: eth0 inet 192.168.1.80/24\n", returncode=0)
            if "ip route" in str(cmd):
                return MagicMock(stdout="default via 192.168.1.1 dev eth0\n", returncode=0)
            if "resolv.conf" in str(cmd):
                return MagicMock(stdout="nameserver 8.8.8.8\n", returncode=0)
            return MagicMock(stdout="", returncode=0)

        mock_subprocess.side_effect = side_effect

        result = ssh_client.get_network_config()

        assert "interfaces" in result
        assert result["gateway"] == "192.168.1.1"
        assert "8.8.8.8" in result["dns"]


# ══════════════════════════════════════════════════════════════════════════════
# TIME TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestGetTimeInfo:
    """Tests for get_time_info method."""

    def test_parses_time_info(self, ssh_client, mock_subprocess):
        def side_effect(cmd, **kwargs):
            if "date" in str(cmd):
                return MagicMock(stdout="2024-01-15 10:30:00 UTC\n", returncode=0)
            if "timezone" in str(cmd):
                return MagicMock(stdout="UTC\n", returncode=0)
            if "timedatectl" in str(cmd):
                return MagicMock(stdout="NTP service: active\nSystem clock synchronized: yes\n", returncode=0)
            if "chronyc" in str(cmd):
                return MagicMock(stdout="", returncode=0)
            return MagicMock(stdout="", returncode=0)

        mock_subprocess.side_effect = side_effect

        result = ssh_client.get_time_info()

        assert result["current_time"] == "2024-01-15 10:30:00 UTC"
        assert result["ntp_enabled"] is True
        assert result["ntp_synchronized"] is True


# ══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestRunDiagnostics:
    """Tests for run_diagnostics method."""

    def test_returns_structured_results(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = ""
        ssh_client._connected = True

        result = ssh_client.run_diagnostics()

        assert "timestamp" in result
        assert "host" in result
        assert "checks" in result
        assert "warnings" in result
        assert "errors" in result
        assert "status" in result


class TestCheckRfStatus:
    """Tests for check_rf_status method."""

    def test_returns_rf_info(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = ""

        result = ssh_client.check_rf_status()

        assert "sdr_devices" in result
        assert "rf_config" in result
        assert "errors" in result


# ══════════════════════════════════════════════════════════════════════════════
# LOG TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestGetLogs:
    """Tests for get_logs method."""

    def test_gets_ots_log(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "log line 1\nlog line 2\n"

        result = ssh_client.get_logs(lines=10)

        assert "log line 1" in result


class TestGetLogErrors:
    """Tests for get_log_errors method."""

    def test_filters_errors(self, ssh_client, mock_subprocess):
        mock_subprocess.return_value.stdout = "Error: something failed\nWarning: something wrong\n"

        result = ssh_client.get_log_errors()

        assert len(result) == 2
