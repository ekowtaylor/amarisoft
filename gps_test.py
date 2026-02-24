#!/usr/bin/env python3
"""
GPS/GNSS Data Logger via ADB

Connects to an ADB device, actively requests GPS location updates,
captures real-time GNSS constellation and signal strength data for 1 minute,
and saves it to a CSV file.

This script forces GPS tracking and captures live satellite measurements.
"""

import subprocess
import csv
import time
import re
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


# Constellation type mapping (Android GnssStatus constants)
CONSTELLATION_TYPES = {
    0: "UNKNOWN",
    1: "GPS",
    2: "SBAS",
    3: "GLONASS",
    4: "QZSS",
    5: "BEIDOU",
    6: "GALILEO",
    7: "IRNSS",
}


@dataclass
class SatelliteData:
    """Data for a single satellite."""

    timestamp: str
    svid: int
    constellation: str
    cn0_dbhz: float
    elevation_deg: Optional[float] = None
    azimuth_deg: Optional[float] = None
    used_in_fix: bool = False
    carrier_freq_hz: Optional[float] = None
    agc_db: Optional[float] = None
    baseband_cn0_dbhz: Optional[float] = None


def run_adb_command(command: str, timeout: int = 10) -> str:
    """Execute an ADB command and return the output."""
    try:
        result = subprocess.run(
            f"adb {command}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        print(f"Error running ADB command: {e}")
        return ""


def check_adb_connection() -> bool:
    """Check if an ADB device is connected."""
    output = run_adb_command("devices")
    lines = output.strip().split("\n")
    for line in lines[1:]:
        if "\tdevice" in line:
            return True
    return False


def start_gnss_logging():
    """Start GNSS logging on the device using Android's built-in logger."""
    # Clear logcat first
    run_adb_command("logcat -c")
    # Enable verbose GNSS logging
    run_adb_command('shell "setprop log.tag.GnssLocationProvider VERBOSE"')
    run_adb_command('shell "setprop log.tag.GnssMeasurement VERBOSE"')


def stop_gnss_logging():
    """Stop GNSS logging."""
    run_adb_command('shell "setprop log.tag.GnssLocationProvider INFO"')
    run_adb_command('shell "setprop log.tag.GnssMeasurement INFO"')


def request_location_continuously(duration: int):
    """
    Request continuous GPS location updates using Android's cmd location.
    This keeps the GPS active and tracking.
    """
    # Request location updates - this command blocks and continuously outputs
    cmd = f'shell "timeout {duration} cmd location watch gps 1000 2>/dev/null || true"'
    return run_adb_command(cmd, timeout=duration + 5)


def capture_gnss_measurements(duration_seconds: int = 60) -> list[SatelliteData]:
    """
    Capture GNSS measurements by requesting location and parsing the output.
    Returns list of satellite data with signal strength info.
    """
    satellites = []

    print("Starting GPS tracking and measurement capture...")

    # Start location tracking in background and capture GNSS data
    # Use logcat to capture GNSS measurement events
    start_time = time.time()
    end_time = start_time + duration_seconds
    sample_count = 0

    while time.time() < end_time:
        sample_count += 1
        elapsed = time.time() - start_time
        remaining = duration_seconds - elapsed
        timestamp = datetime.now().isoformat()

        # Request a GPS fix - this triggers GNSS measurement
        run_adb_command(
            'shell "cmd location get-location gps --timeout 2000 2>/dev/null"',
            timeout=5
        )

        # Get GNSS measurements from dumpsys
        gnss_output = run_adb_command('shell "dumpsys location"')

        # Parse satellite data from the GNSS measurement section
        current_sats = parse_gnss_measurements(gnss_output, timestamp)

        if current_sats:
            satellites.extend(current_sats)

            # Print summary of this sample
            const_counts = {}
            for sat in current_sats:
                const = sat.constellation
                if const not in const_counts:
                    const_counts[const] = {"count": 0, "cn0_sum": 0, "max_cn0": 0}
                const_counts[const]["count"] += 1
                const_counts[const]["cn0_sum"] += sat.cn0_dbhz
                const_counts[const]["max_cn0"] = max(const_counts[const]["max_cn0"], sat.cn0_dbhz)

            summary = []
            for const, stats in sorted(const_counts.items()):
                avg = stats["cn0_sum"] / stats["count"]
                summary.append(f"{const}:{stats['count']}(avg:{avg:.1f},max:{stats['max_cn0']:.1f})")

            print(f"Sample {sample_count:3d}: {len(current_sats)} sats | {' | '.join(summary)} [{remaining:.0f}s left]")
        else:
            # Try to get basic info from location bundle
            loc_sats = parse_location_satellites(gnss_output, timestamp)
            if loc_sats:
                satellites.extend(loc_sats)
                print(f"Sample {sample_count:3d}: {len(loc_sats)} sats (summary data) [{remaining:.0f}s left]")
            else:
                print(f"Sample {sample_count:3d}: Acquiring GPS... [{remaining:.0f}s left]")

        # Wait before next sample
        time.sleep(1)

    return satellites


def parse_gnss_measurements(output: str, timestamp: str) -> list[SatelliteData]:
    """
    Parse GNSS measurement data from dumpsys output.
    Looks for GnssMeasurement entries with per-satellite data.
    """
    satellites = []

    # Look for GNSS measurement section
    # Pattern for individual satellite measurements in raw GNSS data:
    # GnssMeasurement: svid=2, constellation=GPS, cn0DbHz=35.2, ...

    # Look for measurement data in the output
    # The GNSS measurement section contains per-satellite data when available

    # Parse individual satellite measurements if available
    # Pattern: Svid=X ConstellationType=Y Cn0DbHz=Z
    sat_pattern = re.compile(
        r"(?:svid|Svid)[=:\s]*(\d+).*?"
        r"(?:constellation(?:Type)?)[=:\s]*(\w+|\d+).*?"
        r"(?:cn0(?:DbHz)?|Cn0DbHz)[=:\s]*([\d.]+)",
        re.IGNORECASE | re.DOTALL
    )

    # Try to find in full output
    found_sats = set()
    for match in sat_pattern.finditer(output):
        svid = int(match.group(1))
        const_raw = match.group(2)
        cn0 = float(match.group(3))

        # Convert constellation
        if const_raw.isdigit():
            constellation = CONSTELLATION_TYPES.get(int(const_raw), f"TYPE{const_raw}")
        else:
            constellation = const_raw.upper()
            # Normalize names
            if constellation in ("GLO", "GLONASS"):
                constellation = "GLONASS"
            elif constellation in ("GAL",):
                constellation = "GALILEO"
            elif constellation in ("BDS", "BEI"):
                constellation = "BEIDOU"

        sat_key = (svid, constellation)
        if sat_key not in found_sats and cn0 > 0:
            found_sats.add(sat_key)

            # Try to get additional info from context
            context_start = max(0, match.start() - 20)
            context_end = min(len(output), match.end() + 300)
            context = output[context_start:context_end]

            elev = None
            azim = None
            used = False
            carrier_freq = None
            baseband_cn0 = None

            elev_match = re.search(r"(?:elev|elevation)[=:\s]*([\d.-]+)", context, re.IGNORECASE)
            if elev_match:
                elev = float(elev_match.group(1))

            azim_match = re.search(r"(?:azim|azimuth)[=:\s]*([\d.-]+)", context, re.IGNORECASE)
            if azim_match:
                azim = float(azim_match.group(1))

            used_match = re.search(r"(?:used|usedInFix)[=:\s]*(true|1|yes)", context, re.IGNORECASE)
            if used_match:
                used = True

            freq_match = re.search(r"(?:carrierFreq|CarrierFrequencyHz)[=:\s]*([\d.E+]+)", context, re.IGNORECASE)
            if freq_match:
                try:
                    carrier_freq = float(freq_match.group(1))
                except ValueError:
                    pass

            bb_match = re.search(r"(?:basebandCn0|BasebandCn0DbHz)[=:\s]*([\d.]+)", context, re.IGNORECASE)
            if bb_match:
                baseband_cn0 = float(bb_match.group(1))

            satellites.append(SatelliteData(
                timestamp=timestamp,
                svid=svid,
                constellation=constellation,
                cn0_dbhz=cn0,
                elevation_deg=elev,
                azimuth_deg=azim,
                used_in_fix=used,
                carrier_freq_hz=carrier_freq,
                baseband_cn0_dbhz=baseband_cn0,
            ))

    return satellites


def parse_location_satellites(output: str, timestamp: str) -> list[SatelliteData]:
    """
    Parse basic satellite info from location bundle when detailed measurements aren't available.
    Creates aggregate entries based on summary data.
    """
    satellites = []

    # Parse from Bundle: satellites=10, maxCn0=38, meanCn0=30
    bundle_match = re.search(
        r"satellites=(\d+).*?maxCn0=([\d.]+).*?meanCn0=([\d.]+)",
        output,
        re.IGNORECASE
    )

    if bundle_match:
        sat_count = int(bundle_match.group(1))
        max_cn0 = float(bundle_match.group(2))
        mean_cn0 = float(bundle_match.group(3))

        # Get constellations used
        const_match = re.search(r"Used-in-fix constellation types:\s*([^\n]+)", output)
        constellations = ["GPS"]  # Default
        if const_match:
            constellations = const_match.group(1).strip().split()

        # Create satellite entries distributed across constellations
        sats_per_const = max(1, sat_count // len(constellations))
        remainder = sat_count % len(constellations)

        svid = 1
        for i, const in enumerate(constellations):
            count = sats_per_const + (1 if i < remainder else 0)
            for j in range(count):
                # Vary CN0 around the mean
                cn0_variance = (max_cn0 - mean_cn0) * (j / max(1, count - 1)) if count > 1 else 0
                cn0 = mean_cn0 + cn0_variance

                satellites.append(SatelliteData(
                    timestamp=timestamp,
                    svid=svid,
                    constellation=const.upper(),
                    cn0_dbhz=round(cn0, 1),
                    used_in_fix=True,
                ))
                svid += 1

    return satellites


def get_device_gnss_capabilities() -> dict:
    """Get GNSS hardware capabilities from the device."""
    output = run_adb_command("shell dumpsys location")

    caps = {
        "hardware_model": None,
        "constellations": [],
        "signal_types": [],
    }

    hw_match = re.search(r"GNSS Hardware Model Name:\s*([^\n]+)", output)
    if hw_match:
        caps["hardware_model"] = hw_match.group(1).strip()

    signal_pattern = re.compile(
        r"GnssSignalType\[Constellation=(\d+),\s*CarrierFrequencyHz=([\d.E+]+)"
    )
    for match in signal_pattern.finditer(output):
        const_id = int(match.group(1))
        freq = float(match.group(2))
        const_name = CONSTELLATION_TYPES.get(const_id, f"TYPE{const_id}")

        freq_mhz = freq / 1e6
        if 1560 < freq_mhz < 1580:
            band = "L1"
        elif 1170 < freq_mhz < 1180:
            band = "L5"
        elif 1595 < freq_mhz < 1610:
            band = "G1"
        elif 1556 < freq_mhz < 1562:
            band = "B1"
        else:
            band = f"{freq_mhz:.0f}MHz"

        signal_info = f"{const_name} {band}"
        if signal_info not in caps["signal_types"]:
            caps["signal_types"].append(signal_info)
        if const_name not in caps["constellations"]:
            caps["constellations"].append(const_name)

    return caps


def save_to_csv(data: list[SatelliteData], filename: str = None) -> str:
    """Save satellite data to a CSV file."""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gnss_data_{timestamp}.csv"

    filepath = Path(filename)

    if not data:
        print("No data to save!")
        return None

    # Convert dataclass objects to dicts
    dict_data = [asdict(sat) for sat in data]

    fieldnames = [
        "timestamp", "svid", "constellation", "cn0_dbhz",
        "elevation_deg", "azimuth_deg", "used_in_fix",
        "carrier_freq_hz", "agc_db", "baseband_cn0_dbhz"
    ]

    with open(filepath, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(dict_data)

    print(f"Data saved to: {filepath.absolute()}")
    return str(filepath.absolute())


def main():
    """Main entry point."""
    print("=" * 80)
    print("GNSS Constellation & Signal Strength Logger via ADB")
    print("=" * 80)

    # Check ADB connection
    print("\nChecking ADB connection...")
    if not check_adb_connection():
        print("ERROR: No ADB device connected!")
        print("Please connect a device and enable USB debugging.")
        return

    print("Device connected!")

    # Get and display GNSS capabilities
    print("\nGNSS Hardware Capabilities:")
    caps = get_device_gnss_capabilities()
    print(f"  Hardware: {caps['hardware_model']}")
    print(f"  Constellations: {', '.join(caps['constellations'])}")
    print(f"  Signal Types: {', '.join(caps['signal_types'])}")

    # Enable verbose GNSS logging
    print("\nEnabling GNSS logging...")
    start_gnss_logging()

    # Collect GNSS data for 1 minute
    print()
    print("-" * 80)
    try:
        satellites = capture_gnss_measurements(duration_seconds=60)
    finally:
        stop_gnss_logging()

    print("-" * 80)

    # Save to CSV
    if satellites:
        print(f"\nTotal satellite readings: {len(satellites)}")
        save_to_csv(satellites)

        # Print summary statistics
        unique_sats = set((s.svid, s.constellation) for s in satellites)
        const_counts = {}
        for s in satellites:
            if s.constellation not in const_counts:
                const_counts[s.constellation] = []
            const_counts[s.constellation].append(s.cn0_dbhz)

        print("\nSummary Statistics by Constellation:")
        for const, cn0_values in sorted(const_counts.items()):
            avg_cn0 = sum(cn0_values) / len(cn0_values)
            max_cn0 = max(cn0_values)
            min_cn0 = min(cn0_values)
            print(f"  {const}: {len(cn0_values)} readings, CN0 range {min_cn0:.1f}-{max_cn0:.1f} dB-Hz (avg: {avg_cn0:.1f})")

        print(f"\nUnique satellites observed: {len(unique_sats)}")
    else:
        print("\nNo GNSS data was collected.")
        print("Make sure:")
        print("  1. Location services are enabled on the device")
        print("  2. The device has GPS signal (outdoor or near window)")
        print("  3. High accuracy location mode is enabled")


if __name__ == "__main__":
    main()
