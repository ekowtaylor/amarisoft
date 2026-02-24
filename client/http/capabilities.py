"""Device capabilities and constraints system for Amarisoft Callbox via HTTP.

This module provides the same functionality as the WebSocket capabilities module
but works with the HTTP client.

- DeviceCapabilities: Discovered capabilities from a connected device
- Constraints: Validation rules based on hardware/license limits
- CapabilityChecker: Validates operations against device constraints
- ValidationContext: Context manager for enabling validation

Usage::

    from client.http import Callbox
    from client.http.capabilities import (
        DeviceCapabilities,
        CapabilityChecker,
        ValidationContext,
    )

    cb = Callbox("http://192.168.1.80:9010")

    # Discover device capabilities
    caps = DeviceCapabilities.from_callbox(cb)
    print(f"Max cells: {caps.max_cells}")
    print(f"Supported bands: {caps.bands}")

    # Validate operations
    checker = CapabilityChecker(caps)
    errors = checker.validate_cell_config(cell_id=1, band=78, gain=-10)

    # Or use validation context
    with ValidationContext(cb) as ctx:
        # Operations are automatically validated
        cb.enb.cell_gain(cell_id=1, gain=-10)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .callbox import Callbox

logger = logging.getLogger(__name__)


@dataclass
class BandInfo:
    """Information about a supported frequency band."""

    band: int
    technology: str  # "lte", "nr", "nbiot"
    duplex_mode: str  # "fdd", "tdd"
    min_freq_dl: float | None = None
    max_freq_dl: float | None = None
    min_freq_ul: float | None = None
    max_freq_ul: float | None = None
    max_bandwidth: int | None = None  # MHz
    supported_bandwidths: list[int] = field(default_factory=list)

    def supports_bandwidth(self, bw: int) -> bool:
        """Check if bandwidth is supported."""
        if self.supported_bandwidths:
            return bw in self.supported_bandwidths
        if self.max_bandwidth:
            return bw <= self.max_bandwidth
        return True


@dataclass
class RFLimits:
    """RF hardware limits."""

    min_tx_gain: float = -140.0
    max_tx_gain: float = 0.0
    min_rx_gain: float = 0.0
    max_rx_gain: float = 80.0
    max_tx_power_dbm: float | None = None
    num_antennas: int = 1
    mimo_layers: int = 1


@dataclass
class LicenseLimits:
    """License-based limits."""

    max_cells: int = 1
    max_ues: int = 1
    max_carriers: int = 1
    features: list[str] = field(default_factory=list)
    expiry_date: str | None = None
    is_valid: bool = True


@dataclass
class DeviceCapabilities:
    """Discovered capabilities from a connected Amarisoft device.

    Contains information about:
    - Hardware limits (RF, antennas, etc.)
    - License limits (max cells, UEs, features)
    - Supported bands and configurations
    - Software version and features
    """

    version: str = ""
    hardware_type: str = ""
    bands: list[BandInfo] = field(default_factory=list)
    rf_limits: RFLimits = field(default_factory=RFLimits)
    license_limits: LicenseLimits = field(default_factory=LicenseLimits)
    supported_technologies: list[str] = field(default_factory=list)
    supported_features: list[str] = field(default_factory=list)

    @property
    def max_cells(self) -> int:
        """Maximum number of cells allowed by license."""
        return self.license_limits.max_cells

    @property
    def max_ues(self) -> int:
        """Maximum number of UEs allowed by license."""
        return self.license_limits.max_ues

    @property
    def band_numbers(self) -> list[int]:
        """List of supported band numbers."""
        return [b.band for b in self.bands]

    def supports_band(self, band: int) -> bool:
        """Check if a band is supported."""
        return band in self.band_numbers

    def supports_technology(self, tech: str) -> bool:
        """Check if a technology is supported (lte, nr, nbiot)."""
        return tech.lower() in [t.lower() for t in self.supported_technologies]

    def get_band_info(self, band: int) -> BandInfo | None:
        """Get detailed info for a specific band."""
        for b in self.bands:
            if b.band == band:
                return b
        return None

    @classmethod
    def from_callbox(cls, callbox: "Callbox") -> "DeviceCapabilities":
        """Discover capabilities from a connected HTTP Callbox.

        Args:
            callbox: Connected HTTP Callbox instance.

        Returns:
            DeviceCapabilities instance with discovered limits.
        """
        caps = cls()

        # Get version info
        try:
            version_info = callbox.enb.version()
            caps.version = version_info.get("version", "")
            caps.hardware_type = version_info.get("hardware", "")
        except Exception as e:
            logger.warning(f"Failed to get version info: {e}")

        # Get license info
        try:
            license_info = callbox.enb.license()
            caps.license_limits = cls._parse_license(license_info)
        except Exception as e:
            logger.warning(f"Failed to get license info: {e}")

        # Get config to determine supported bands/features
        try:
            config = callbox.enb.config_get()
            caps.bands = cls._parse_bands(config)
            caps.supported_technologies = cls._parse_technologies(config)
        except Exception as e:
            logger.warning(f"Failed to get config: {e}")

        # Get RF limits from stats
        try:
            stats = callbox.enb.stats(rf=True)
            caps.rf_limits = cls._parse_rf_limits(stats)
        except Exception as e:
            logger.warning(f"Failed to get RF stats: {e}")

        return caps

    @classmethod
    def _parse_license(cls, license_info: dict[str, Any]) -> LicenseLimits:
        """Parse license information."""
        limits = LicenseLimits()

        if "max_cell_count" in license_info:
            limits.max_cells = license_info["max_cell_count"]
        if "max_ue_count" in license_info:
            limits.max_ues = license_info["max_ue_count"]
        if "features" in license_info:
            limits.features = license_info["features"]
        if "expiry" in license_info:
            limits.expiry_date = license_info["expiry"]
        if "valid" in license_info:
            limits.is_valid = license_info["valid"]

        return limits

    @classmethod
    def _parse_bands(cls, config: dict[str, Any]) -> list[BandInfo]:
        """Parse band information from config."""
        bands = []

        # Try to extract from cells config
        cells = config.get("cells", config.get("cell_list", []))
        seen_bands = set()

        for cell in cells:
            band_num = cell.get("band", cell.get("dl_earfcn_band"))
            if band_num and band_num not in seen_bands:
                seen_bands.add(band_num)

                tech = "nr" if cell.get("rat") == "nr" else "lte"
                duplex = cell.get("tdd_config", {}) and "tdd" or "fdd"

                bands.append(BandInfo(
                    band=band_num,
                    technology=tech,
                    duplex_mode=duplex,
                    supported_bandwidths=cell.get("supported_bandwidths", []),
                ))

        return bands

    @classmethod
    def _parse_technologies(cls, config: dict[str, Any]) -> list[str]:
        """Parse supported technologies from config."""
        techs = set()

        cells = config.get("cells", config.get("cell_list", []))
        for cell in cells:
            rat = cell.get("rat", "lte")
            techs.add(rat.lower())

        return list(techs) or ["lte"]

    @classmethod
    def _parse_rf_limits(cls, stats: dict[str, Any]) -> RFLimits:
        """Parse RF limits from stats."""
        limits = RFLimits()

        rf_info = stats.get("rf", {})
        if "tx_gain_range" in rf_info:
            limits.min_tx_gain = rf_info["tx_gain_range"].get("min", -140.0)
            limits.max_tx_gain = rf_info["tx_gain_range"].get("max", 0.0)
        if "rx_gain_range" in rf_info:
            limits.min_rx_gain = rf_info["rx_gain_range"].get("min", 0.0)
            limits.max_rx_gain = rf_info["rx_gain_range"].get("max", 80.0)
        if "num_antennas" in rf_info:
            limits.num_antennas = rf_info["num_antennas"]

        return limits


@dataclass
class ValidationError:
    """A validation error."""

    field: str
    message: str
    value: Any = None
    constraint: Any = None

    def __str__(self) -> str:
        return f"{self.field}: {self.message}"


class CapabilityChecker:
    """Validates operations against device capabilities.

    Example::

        caps = DeviceCapabilities.from_callbox(cb)
        checker = CapabilityChecker(caps)

        errors = checker.validate_gain(cell_id=1, gain=-150)
        if errors:
            for err in errors:
                print(f"Validation error: {err}")
    """

    def __init__(self, capabilities: DeviceCapabilities):
        """Initialize the checker.

        Args:
            capabilities: Device capabilities to validate against.
        """
        self.capabilities = capabilities

    def validate_gain(self, gain: float) -> list[ValidationError]:
        """Validate a gain value.

        Args:
            gain: Gain value in dB.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []
        rf = self.capabilities.rf_limits

        if gain < rf.min_tx_gain:
            errors.append(ValidationError(
                field="gain",
                message=f"Gain {gain} dB is below minimum {rf.min_tx_gain} dB",
                value=gain,
                constraint=rf.min_tx_gain,
            ))
        if gain > rf.max_tx_gain:
            errors.append(ValidationError(
                field="gain",
                message=f"Gain {gain} dB is above maximum {rf.max_tx_gain} dB",
                value=gain,
                constraint=rf.max_tx_gain,
            ))

        return errors

    def validate_cell_id(self, cell_id: int) -> list[ValidationError]:
        """Validate a cell ID.

        Args:
            cell_id: Cell ID to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        if cell_id < 0:
            errors.append(ValidationError(
                field="cell_id",
                message=f"Cell ID {cell_id} must be non-negative",
                value=cell_id,
            ))

        max_cells = self.capabilities.max_cells
        if cell_id >= max_cells:
            errors.append(ValidationError(
                field="cell_id",
                message=f"Cell ID {cell_id} exceeds maximum {max_cells - 1}",
                value=cell_id,
                constraint=max_cells,
            ))

        return errors

    def validate_band(self, band: int) -> list[ValidationError]:
        """Validate a band number.

        Args:
            band: Band number to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        if not self.capabilities.supports_band(band):
            errors.append(ValidationError(
                field="band",
                message=f"Band {band} is not supported. Supported: {self.capabilities.band_numbers}",
                value=band,
                constraint=self.capabilities.band_numbers,
            ))

        return errors

    def validate_cell_config(
        self,
        cell_id: int,
        band: int | None = None,
        gain: float | None = None,
        bandwidth: int | None = None,
    ) -> list[ValidationError]:
        """Validate a complete cell configuration.

        Args:
            cell_id: Cell ID.
            band: Optional band number.
            gain: Optional gain value.
            bandwidth: Optional bandwidth in MHz.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        errors.extend(self.validate_cell_id(cell_id))

        if band is not None:
            errors.extend(self.validate_band(band))

            # Also check bandwidth against band
            if bandwidth is not None:
                band_info = self.capabilities.get_band_info(band)
                if band_info and not band_info.supports_bandwidth(bandwidth):
                    errors.append(ValidationError(
                        field="bandwidth",
                        message=f"Bandwidth {bandwidth} MHz not supported for band {band}",
                        value=bandwidth,
                        constraint=band_info.supported_bandwidths,
                    ))

        if gain is not None:
            errors.extend(self.validate_gain(gain))

        return errors

    def validate_ue_count(self, ue_count: int) -> list[ValidationError]:
        """Validate UE count against license limits.

        Args:
            ue_count: Number of UEs.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        max_ues = self.capabilities.max_ues
        if ue_count > max_ues:
            errors.append(ValidationError(
                field="ue_count",
                message=f"UE count {ue_count} exceeds license limit {max_ues}",
                value=ue_count,
                constraint=max_ues,
            ))

        return errors


class ValidationContext:
    """Context manager for enabling operation validation.

    When active, operations on the callbox will be validated against
    device capabilities before execution.

    Example::

        cb = Callbox("http://192.168.1.80:9010")

        with ValidationContext(cb) as ctx:
            # Access the checker
            errors = ctx.checker.validate_gain(-150)

            # Or validate manually
            cb.enb.cell_gain(cell_id=1, gain=-10)
    """

    def __init__(
        self,
        callbox: "Callbox",
        capabilities: DeviceCapabilities | None = None,
    ):
        """Initialize the validation context.

        Args:
            callbox: HTTP Callbox instance.
            capabilities: Pre-discovered capabilities (will discover if not provided).
        """
        self.callbox = callbox
        self.capabilities = capabilities
        self._old_checker: CapabilityChecker | None = None

    def __enter__(self) -> "ValidationContext":
        """Enter validation context."""
        if self.capabilities is None:
            self.capabilities = DeviceCapabilities.from_callbox(self.callbox)

        self._old_checker = getattr(self.callbox, "_capability_checker", None)
        self.callbox._capability_checker = CapabilityChecker(self.capabilities)
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        """Exit validation context."""
        self.callbox._capability_checker = self._old_checker
        return False

    @property
    def checker(self) -> CapabilityChecker:
        """Get the capability checker."""
        return self.callbox._capability_checker
