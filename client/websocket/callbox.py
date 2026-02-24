"""Main Amarisoft Callbox class that orchestrates all service APIs."""

from __future__ import annotations

import logging
import ssl as _ssl
from typing import Any, TYPE_CHECKING

from .client import WebSocketClient
from .enb import ENBApi
from .ims import IMSApi
from .mme import MMEApi
from .ue import UEApi

if TYPE_CHECKING:
    from .capabilities import CapabilityChecker, DeviceCapabilities

logger = logging.getLogger(__name__)


class Callbox:
    """High-level interface to an Amarisoft Callbox system.

    Provides unified access to all Callbox services (eNB/gNB, MME/AMF,
    IMS, UE Simulator) through their respective WebSocket Remote APIs.

    Default ports (as per Amarisoft documentation)::

        MME/AMF : 9000
        eNB/gNB : 9001
        IMS     : 9002
        UE Sim  : 9003

    Example::

        cb = Callbox("192.168.1.100")
        cb.connect_all()
        ues = cb.enb.ue_get()
        cb.enb.cell_gain(cell_id=1, gain=-10)
        cb.mme.ue_detach(imsi="001010123456789")
        cb.close()

    Context manager::

        with Callbox("192.168.1.100") as cb:
            cb.enb.stats()

    With capability validation::

        from amarisoft.capabilities import ValidationContext

        with Callbox("192.168.1.80", ims_port=9003) as cb:
            with ValidationContext(cb) as ctx:
                # Operations are validated against device capabilities
                cb.enb.rf(tx_gain=60)  # Validated
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        *,
        enb_port: int = ENBApi.DEFAULT_PORT,
        mme_port: int = MMEApi.DEFAULT_PORT,
        ims_port: int = IMSApi.DEFAULT_PORT,
        ue_port: int = UEApi.DEFAULT_PORT,
        password: str | None = None,
        ssl: bool = False,
        ssl_context: _ssl.SSLContext | None = None,
        timeout: float = 10.0,
        auto_reconnect: bool = False,
        ssl_verify: bool = False,
    ):
        """Initialize the Callbox interface.

        Args:
            host: IP address or hostname of the Amarisoft Callbox.
            enb_port: WebSocket port for eNB/gNB service.
            mme_port: WebSocket port for MME/AMF service.
            ims_port: WebSocket port for IMS service.
            ue_port: WebSocket port for UE Simulator service.
            password: Authentication password (if ``com_auth`` is
                configured on the Callbox).
            ssl: Use WSS (TLS) for connections.
            ssl_context: Custom :class:`ssl.SSLContext` (e.g. for
                self-signed certificates).
            timeout: Default timeout in seconds for WebSocket operations.
            auto_reconnect: Automatically reconnect on send failure.
            ssl_verify: Verify the server's TLS certificate. Defaults to
                ``False`` so that self-signed certificates on the
                Callbox are accepted without extra configuration.
        """
        self.host = host
        self.password = password
        self.ssl = ssl
        self.timeout = timeout

        # Capability checker (set by ValidationContext or enable_validation)
        self._capability_checker: CapabilityChecker | None = None
        self._capabilities: DeviceCapabilities | None = None

        kwargs: dict[str, Any] = dict(
            password=password,
            ssl=ssl,
            timeout=timeout,
            ssl_context=ssl_context,
            auto_reconnect=auto_reconnect,
            ssl_verify=ssl_verify,
        )

        # Create WebSocket clients for each service
        self._enb_client = WebSocketClient(host, enb_port, **kwargs)
        self._mme_client = WebSocketClient(host, mme_port, **kwargs)
        self._ims_client = WebSocketClient(host, ims_port, **kwargs)
        self._ue_client = WebSocketClient(host, ue_port, **kwargs)

        # Create API instances
        self.enb = ENBApi(self._enb_client)
        self.mme = MMEApi(self._mme_client)
        self.ims = IMSApi(self._ims_client)
        self.ue = UEApi(self._ue_client)

        # Set callbox reference on API instances for validation
        self.enb._callbox = self
        self.mme._callbox = self
        self.ims._callbox = self
        self.ue._callbox = self

        self._clients = {
            "enb": self._enb_client,
            "mme": self._mme_client,
            "ims": self._ims_client,
            "ue": self._ue_client,
        }

    def connect_all(self) -> dict[str, dict[str, Any]]:
        """Connect to all Callbox services.

        Returns:
            Dictionary mapping service names to their ready messages.
            Services that fail to connect will have an ``"error"`` key.

        Note:
            Services that fail to connect will log a warning but won't
            prevent other services from connecting.
        """
        results: dict[str, dict[str, Any]] = {}
        for name, client in self._clients.items():
            try:
                results[name] = client.connect()
                logger.info("Connected to %s at %s", name, client.uri)
            except Exception as e:
                logger.warning(
                    "Failed to connect to %s at %s: %s", name, client.uri, e
                )
                results[name] = {"error": str(e)}
        return results

    def connect_enb(self) -> dict[str, Any]:
        """Connect to the eNB/gNB service."""
        return self._enb_client.connect()

    def connect_mme(self) -> dict[str, Any]:
        """Connect to the MME/AMF service."""
        return self._mme_client.connect()

    def connect_ims(self) -> dict[str, Any]:
        """Connect to the IMS service."""
        return self._ims_client.connect()

    def connect_ue(self) -> dict[str, Any]:
        """Connect to the UE Simulator service."""
        return self._ue_client.connect()

    def close(self) -> None:
        """Close all WebSocket connections."""
        for name, client in self._clients.items():
            try:
                client.close()
            except Exception as e:
                logger.warning("Error closing %s: %s", name, e)

    # Alias for close() for consistency
    disconnect_all = close

    @property
    def status(self) -> dict[str, bool]:
        """Return connection status for each service."""
        return {
            name: client.connected for name, client in self._clients.items()
        }

    def send_raw(
        self,
        service: str,
        message: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a raw JSON message to a specific service.

        Useful for commands not yet wrapped by the API classes.

        Args:
            service: Target service (``"enb"``, ``"mme"``, ``"ims"``,
                ``"ue"``).
            message: Raw JSON message dictionary.

        Returns:
            The parsed response.

        Raises:
            ValueError: If the service name is invalid.
        """
        client = self._clients.get(service)
        if client is None:
            raise ValueError(
                f"Unknown service '{service}'. "
                f"Use: {list(self._clients.keys())}"
            )
        return client.send(message)

    # ──────────────────────────────────────────────
    # Capability Management
    # ──────────────────────────────────────────────

    def discover_capabilities(self) -> "DeviceCapabilities":
        """Discover and cache device capabilities.

        Returns:
            DeviceCapabilities instance with discovered constraints.

        Note:
            Requires at least one service to be connected.
        """
        from .capabilities import DeviceCapabilities

        self._capabilities = DeviceCapabilities.from_callbox(self)
        return self._capabilities

    def get_device_info(self, ssh_info: dict[str, Any] | None = None) -> dict[str, Any]:
        """Get comprehensive device information.

        Returns a detailed overview of the Callbox including hardware,
        license, services, capabilities, constraints, and current status.

        Args:
            ssh_info: Optional hardware info from SSHClient.get_system_info().
                     If provided, includes SDR card details, hostname, OS info.

        Returns:
            Dictionary with all device information.

        Example::

            from amarisoft import Callbox, SSHClient

            cb = Callbox("192.168.1.80", ims_port=9003)
            cb.connect_all()

            # WebSocket only (limited hardware info)
            info = cb.get_device_info()

            # With SSH for full hardware details
            with SSHClient("192.168.1.80") as ssh:
                sys_info = ssh.get_system_info()
                info = cb.get_device_info(ssh_info=sys_info.to_dict())
        """
        from .capabilities import DeviceCapabilities

        # Discover capabilities if not already done
        if self._capabilities is None:
            self._capabilities = DeviceCapabilities.from_callbox(self)

        caps = self._capabilities

        # Get current stats from services
        enb_stats = {}
        enb_ues = []
        mme_ues = []

        if self._enb_client.connected:
            try:
                enb_stats = self.enb.stats()
                ue_data = self.enb.ue_get()
                enb_ues = ue_data.get("ue_list", [])
            except Exception:
                pass

        if self._mme_client.connected:
            try:
                ue_data = self.mme.ue_get()
                mme_ues = ue_data.get("ue_list", [])
            except Exception:
                pass

        # Build hardware section - use SSH info if provided
        if ssh_info:
            hardware = {
                "hostname": ssh_info.get("hostname", caps.hostname),
                "os_name": ssh_info.get("os_name", "unknown"),
                "os_version": ssh_info.get("os_version", caps.os_version),
                "kernel": ssh_info.get("kernel", "unknown"),
                "amarisoft_version": ssh_info.get("amarisoft_version", caps.amarisoft_version),
                "sdr_cards": ssh_info.get("sdr_cards", []),
                "rf_config": ssh_info.get("rf_config", {}),
            }
        else:
            hardware = {
                "hostname": caps.hostname,
                "os_version": caps.os_version,
                "amarisoft_version": caps.amarisoft_version,
                "sdr_cards": [
                    {
                        "device_id": sdr.device_id,
                        "board_type": sdr.board_type,
                        "board_id": sdr.board_id,
                        "serial": sdr.serial,
                        "fpga_revision": sdr.fpga_revision,
                        "max_bandwidth_mhz": sdr.max_bandwidth_mhz,
                    }
                    for sdr in caps.sdr_cards
                ],
            }

        # Build comprehensive info dict
        info = {
            "host": self.host,
            "connection_status": self.status,

            # Hardware
            "hardware": hardware,

            # License
            "license": {
                "user": caps.license_info.user_name if caps.license_info else "unknown",
                "valid_until": caps.license_info.valid_until if caps.license_info else "unknown",
                "products": caps.license_info.products if caps.license_info else [],
                "uid": caps.license_info.license_uid if caps.license_info else "unknown",
            },

            # Constraints
            "constraints": {
                "max_cells": caps.max_cells,
                "max_bandwidth_mhz": caps.max_bandwidth_mhz,
                "max_mimo_layers": caps.max_mimo_layers,
                "supported_rats": [r.value for r in caps.supported_rats],
            },

            # Services
            "services": {
                "enb": {
                    "connected": self._enb_client.connected,
                    "port": self._enb_client.port,
                },
                "mme": {
                    "connected": self._mme_client.connected,
                    "port": self._mme_client.port,
                },
                "ims": {
                    "connected": self._ims_client.connected,
                    "port": self._ims_client.port,
                },
                "ue": {
                    "connected": self._ue_client.connected,
                    "port": self._ue_client.port,
                },
            },

            # Features
            "features": {
                "ue_sim": caps.features.get("ue_sim", False),
                "ims": caps.features.get("ims", False),
                "volte": caps.features.get("volte", False),
                "5gc": caps.features.get("5gc", False),
                "carrier_aggregation": caps.features.get("carrier_aggregation", False),
                "endc": caps.features.get("endc", False),
            },

            # Active cells
            "cells": [
                {
                    "cell_id": cell.cell_id,
                    "rat": cell.rat.value,
                    "band": cell.band,
                    "bandwidth_mhz": cell.bandwidth_mhz,
                    "duplex_mode": cell.duplex_mode.value,
                    "mimo_dl": cell.mimo_layers_dl,
                    "mimo_ul": cell.mimo_layers_ul,
                }
                for cell in caps.cells
            ],

            # Current status
            "current_status": {
                "enb": {
                    "cells": enb_stats.get("cells", {}),
                    "ue_count": len(enb_ues),
                },
                "mme": {
                    "ue_count": len(mme_ues),
                },
                "attached_ues": mme_ues,
            },
        }

        return info

    def print_device_info(self, ssh_info: dict[str, Any] | None = None) -> None:
        """Print a formatted device information summary.

        Args:
            ssh_info: Optional hardware info from SSHClient.get_system_info().
                     If provided, includes SDR card details, hostname, OS info.

        Example::

            from amarisoft import Callbox, SSHClient

            cb = Callbox("192.168.1.80", ims_port=9003)
            cb.connect_all()

            # Basic info (WebSocket only)
            cb.print_device_info()

            # Full info with SSH
            with SSHClient("192.168.1.80") as ssh:
                cb.print_device_info(ssh_info=ssh.get_system_info().to_dict())
        """
        info = self.get_device_info(ssh_info=ssh_info)

        lines = [
            "=" * 70,
            "AMARISOFT CALLBOX DEVICE INFORMATION",
            "=" * 70,
            f"Host: {info['host']}",
            "",
            "─── HARDWARE ───",
            f"  Hostname:          {info['hardware'].get('hostname', 'unknown')}",
            f"  Amarisoft Version: {info['hardware'].get('amarisoft_version', 'unknown')}",
        ]

        # Show OS info if available (from SSH)
        if info['hardware'].get('os_name') and info['hardware']['os_name'] != 'unknown':
            lines.append(f"  OS:                {info['hardware']['os_name']} {info['hardware'].get('os_version', '')}")
        if info['hardware'].get('kernel') and info['hardware']['kernel'] != 'unknown':
            lines.append(f"  Kernel:            {info['hardware']['kernel']}")

        sdr_cards = info['hardware'].get('sdr_cards', [])
        lines.append(f"  SDR Cards:         {len(sdr_cards)}")
        for sdr in sdr_cards:
            lines.append(f"    - {sdr.get('board_type', 'unknown')} (Serial: {sdr.get('serial', 'unknown')})")
            if sdr.get('fpga_revision'):
                lines.append(f"      FPGA: {sdr['fpga_revision']}")
            if sdr.get('pcie'):
                lines.append(f"      PCIe: {sdr['pcie']}")

        # Show RF config if available
        rf_config = info['hardware'].get('rf_config', {})
        if rf_config.get('tx_gain') is not None:
            lines.append(f"  TX Gain:           {rf_config['tx_gain']} dB")
        if rf_config.get('rx_gain') is not None:
            lines.append(f"  RX Gain:           {rf_config['rx_gain']} dB")

        lines.extend([
            "",
            "─── LICENSE ───",
            f"  User:        {info['license']['user']}",
            f"  Valid Until: {info['license']['valid_until']}",
            f"  Products:    {', '.join(info['license']['products'])}",
            "",
            "─── SERVICES ───",
        ])

        for svc, details in info["services"].items():
            status = "✅" if details["connected"] else "❌"
            lines.append(f"  {svc.upper():4}: {status} (port {details['port']})")

        lines.extend([
            "",
            "─── FEATURES ───",
        ])

        for feature, enabled in info["features"].items():
            status = "✅ Supported" if enabled else "❌ Not Available"
            lines.append(f"  {feature:20}: {status}")

        lines.extend([
            "",
            "─── CONSTRAINTS ───",
            f"  Max Cells:     {info['constraints']['max_cells']}",
            f"  Max Bandwidth: {info['constraints']['max_bandwidth_mhz']} MHz",
            f"  Max MIMO:      {info['constraints']['max_mimo_layers']} layers",
            f"  Supported RATs: {', '.join(info['constraints']['supported_rats'])}",
            "",
            "─── CURRENT STATUS ───",
            f"  Active Cells: {len(info['current_status']['enb'].get('cells', {}))}",
            f"  Attached UEs: {info['current_status']['mme']['ue_count']}",
        ])

        if info["cells"]:
            lines.extend([
                "",
                "─── CELL CONFIGURATION ───",
            ])
            for cell in info["cells"]:
                lines.append(
                    f"  Cell {cell['cell_id']}: {cell['rat'].upper()} Band {cell['band']} "
                    f"{cell['bandwidth_mhz']}MHz {cell['duplex_mode'].upper()} "
                    f"{cell['mimo_dl']}x{cell['mimo_ul']} MIMO"
                )

        lines.append("=" * 70)

        print("\n".join(lines))

    @property
    def capabilities(self) -> "DeviceCapabilities | None":
        """Return cached device capabilities, or None if not discovered."""
        return self._capabilities

    # ──────────────────────────────────────────────────────────────────────
    # APN Configuration (Persistent via SSH)
    # ──────────────────────────────────────────────────────────────────────

    def set_default_apn_persistent(
        self,
        apn: str = "default",
        pdn_type: str = "ipv4",
        first_ip: str = "192.168.2.2",
        last_ip: str = "192.168.2.254",
        dns: str | list[str] = "8.8.8.8",
        qci: int = 9,
        priority_level: int = 15,
        ssh_password: str = "toor",
        restart_mme: bool = False,
        backup: bool = True,
    ) -> dict[str, Any]:
        """Set a default APN configuration persistently via SSH config editing.

        Unlike ``mme.set_default_apn()`` which only modifies runtime config,
        this method edits the MME config file directly so changes persist
        across service restarts.

        Args:
            apn: Access Point Name (default: "default").
            pdn_type: PDN type - "ipv4", "ipv6", or "ipv4v6" (default: "ipv4").
            first_ip: First IP address in the pool (default: "192.168.2.2").
            last_ip: Last IP address in the pool (default: "192.168.2.254").
            dns: DNS server address(es). Can be a string or list of strings.
                Example: "8.8.8.8" or ["8.8.8.8", "8.8.4.4"]
            qci: QoS Class Identifier (default: 9 for best-effort).
            priority_level: ARP priority level 1-15 (default: 15).
            ssh_password: SSH password for the callbox (default: "toor").
            restart_mme: If True, restart MME service after config change.
            backup: If True, backup the config file before modifying.

        Returns:
            Dict with status information including:
            - success: True if config was updated
            - backup_path: Path to backup file (if backup=True)
            - config_path: Path to the config file
            - apn_config: The APN configuration that was added/updated

        Example::

            with Callbox("192.168.1.80") as cb:
                # Add a persistent internet APN
                result = cb.set_default_apn_persistent(
                    apn="internet",
                    first_ip="192.168.3.2",
                    last_ip="192.168.3.254",
                    dns="8.8.8.8",
                    restart_mme=True  # Apply immediately
                )
                print(f"Config updated: {result['success']}")

        Note:
            This method modifies ``/root/mme/config/mme.cfg`` on the callbox.
            A backup is created by default before any modifications.
        """
        from .ssh import SSHClient

        config_path = "/root/mme/config/mme.cfg"
        result: dict[str, Any] = {
            "success": False,
            "config_path": config_path,
            "backup_path": None,
            "apn_config": None,
            "message": "",
        }

        # Build the APN config block
        dns_str = (
            f'"{dns}"' if isinstance(dns, str)
            else "[" + ", ".join(f'"{d}"' for d in dns) + "]"
        )

        apn_config = f'''    {{
      pdn_type: "{pdn_type}",
      access_point_name: "{apn}",
      first_ip_addr: "{first_ip}",
      last_ip_addr: "{last_ip}",
      dns_addr: {dns_str},
      erabs: [
        {{
          qci: {qci},
          priority_level: {priority_level},
          pre_emption_capability: "shall_not_trigger_pre_emption",
          pre_emption_vulnerability: "not_pre_emptable",
        }},
      ],
    }}'''

        result["apn_config"] = {
            "apn": apn,
            "pdn_type": pdn_type,
            "first_ip": first_ip,
            "last_ip": last_ip,
            "dns": dns,
            "qci": qci,
            "priority_level": priority_level,
        }

        with SSHClient(self.host, password=ssh_password) as ssh:
            # Read current config
            current_config = ssh._run_command(f"cat {config_path}")
            if not current_config:
                result["message"] = f"Could not read config file: {config_path}"
                return result

            # Backup if requested
            if backup:
                import time
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_path = f"{config_path}.backup_{timestamp}"
                ssh._run_command(f"cp {config_path} {backup_path}")
                result["backup_path"] = backup_path

            # Check if this APN already exists
            apn_pattern = f'access_point_name:\\s*"{apn}"'
            import re
            if re.search(apn_pattern, current_config):
                # APN exists - we need to replace it
                # This is complex, so we'll add a new entry and note the duplicate
                result["message"] = (
                    f"APN '{apn}' already exists in config. "
                    "Adding new entry - please manually remove duplicate if needed."
                )

            # Find the pdn_list section and add our APN
            # Look for the opening of pdn_list: [
            pdn_list_match = re.search(r"pdn_list:\s*\[", current_config)
            if not pdn_list_match:
                result["message"] = "Could not find pdn_list section in config"
                return result

            # Insert our APN config after pdn_list: [
            insert_pos = pdn_list_match.end()
            new_config = (
                current_config[:insert_pos] +
                "\n" + apn_config + "," +
                current_config[insert_pos:]
            )

            # Write the new config using heredoc
            write_cmd = f"cat > {config_path} << 'EOFCONFIG'\n{new_config}\nEOFCONFIG"

            try:
                ssh._run_command(write_cmd)
                result["success"] = True
                if not result["message"]:
                    result["message"] = f"APN '{apn}' added to config successfully"
            except Exception as e:
                result["message"] = f"Failed to write config: {e}"
                return result

            # Restart MME if requested
            if restart_mme and result["success"]:
                try:
                    ssh._run_command("systemctl restart ltemme 2>/dev/null || killall -HUP ltemme 2>/dev/null || true")
                    result["message"] += " (MME restart initiated)"
                except Exception as e:
                    result["message"] += f" (MME restart failed: {e})"

        return result

    def get_apn_config(self, ssh_password: str = "toor") -> list[dict[str, Any]]:
        """Get all configured APNs from the MME config file via SSH.

        Args:
            ssh_password: SSH password for the callbox (default: "toor").

        Returns:
            List of APN configurations parsed from the config file.

        Example::

            with Callbox("192.168.1.80") as cb:
                apns = cb.get_apn_config()
                for apn in apns:
                    print(f"APN: {apn['access_point_name']}")
                    print(f"  IP Pool: {apn['first_ip']} - {apn['last_ip']}")
        """
        from .ssh import SSHClient
        import re

        apns: list[dict[str, Any]] = []

        with SSHClient(self.host, password=ssh_password) as ssh:
            config = ssh._run_command("cat /root/mme/config/mme.cfg 2>/dev/null")
            if not config:
                return apns

            # Find pdn_list section
            pdn_match = re.search(r"pdn_list:\s*\[", config)
            if not pdn_match:
                return apns

            # Extract the pdn_list content
            start = pdn_match.end()
            bracket_count = 1
            end = start

            for i, char in enumerate(config[start:], start):
                if char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
                    if bracket_count == 0:
                        end = i
                        break

            pdn_content = config[start:end]

            # Parse individual APN entries
            entries = re.split(r"\},?\s*(?=\{|$)", pdn_content)

            for entry in entries:
                entry = entry.strip()
                if not entry or entry == "{":
                    continue

                apn: dict[str, Any] = {}

                # Extract key fields
                patterns = {
                    "access_point_name": r'access_point_name:\s*"([^"]+)"',
                    "pdn_type": r'pdn_type:\s*"([^"]+)"',
                    "first_ip": r'first_ip_addr:\s*"([^"]+)"',
                    "last_ip": r'last_ip_addr:\s*"([^"]+)"',
                    "dns": r'dns_addr:\s*"([^"]+)"',
                }

                for key, pattern in patterns.items():
                    match = re.search(pattern, entry)
                    if match:
                        apn[key] = match.group(1)

                # Extract QCI
                qci_match = re.search(r"qci:\s*(\d+)", entry)
                if qci_match:
                    apn["qci"] = int(qci_match.group(1))

                if apn:
                    apns.append(apn)

        return apns

    def enable_validation(
        self,
        capabilities: "DeviceCapabilities | None" = None,
    ) -> "CapabilityChecker":
        """Enable parameter validation on this Callbox.

        Args:
            capabilities: Optional capabilities to use. If None,
                discovers from the connected device.

        Returns:
            The CapabilityChecker instance.

        Example::

            cb = Callbox("192.168.1.80")
            cb.connect_all()
            checker = cb.enable_validation()
            # Now API calls will be validated
        """
        from .capabilities import CapabilityChecker

        if capabilities is None:
            capabilities = self.discover_capabilities()

        self._capabilities = capabilities
        self._capability_checker = CapabilityChecker(capabilities)
        return self._capability_checker

    def disable_validation(self) -> None:
        """Disable parameter validation."""
        self._capability_checker = None

    @property
    def validation_enabled(self) -> bool:
        """Return True if validation is enabled."""
        return self._capability_checker is not None

    def __enter__(self) -> Callbox:
        self.connect_all()
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        connected = sum(1 for c in self._clients.values() if c.connected)
        validation = " [validation]" if self.validation_enabled else ""
        return f"Callbox({self.host}, {connected}/{len(self._clients)} connected{validation})"
