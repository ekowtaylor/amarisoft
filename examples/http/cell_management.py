#!/usr/bin/env python3
"""Cell Management via HTTP REST API.

Demonstrates cell management operations using the REST API.

Requirements:
    pip install requests

Usage:
    python cell_management.py
"""

import requests
import time

# Configuration
BASE_URL = "http://192.168.1.80:9010"


def list_cells():
    """List all configured cells."""
    print("=" * 60)
    print("Listing Cells")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/enb/cells")

    if response.status_code == 200:
        data = response.json()
        cells = data.get("cells", data.get("cell_list", []))

        if isinstance(cells, dict):
            for cell_id, cell_data in cells.items():
                print(f"  Cell {cell_id}:")
                print(f"    RAT: {cell_data.get('rat', 'N/A')}")
                print(f"    Band: {cell_data.get('band', 'N/A')}")
                print(f"    Active: {cell_data.get('active', 'N/A')}")
        elif isinstance(cells, list):
            for cell in cells:
                print(f"  Cell {cell.get('cell_id', 'N/A')}: {cell}")
        else:
            print(f"  Raw data: {data}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
    print()


def set_cell_gain(cell_id: int, gain: float):
    """Set gain for a specific cell.

    Args:
        cell_id: The cell ID to modify.
        gain: The gain value in dB (between -140 and 0).
    """
    print("=" * 60)
    print(f"Setting Cell {cell_id} Gain to {gain} dB")
    print("=" * 60)

    response = requests.post(
        f"{BASE_URL}/enb/cells/{cell_id}/gain",
        json={"gain": gain},
    )

    if response.status_code == 200:
        print("✓ Gain set successfully")
        print(f"  Response: {response.json()}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.json()}")
    print()


def activate_cell(cell_id: int):
    """Activate a cell."""
    print("=" * 60)
    print(f"Activating Cell {cell_id}")
    print("=" * 60)

    response = requests.post(f"{BASE_URL}/enb/cells/{cell_id}/activate")

    if response.status_code == 200:
        print("✓ Cell activated")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.json()}")
    print()


def deactivate_cell(cell_id: int):
    """Deactivate a cell."""
    print("=" * 60)
    print(f"Deactivating Cell {cell_id}")
    print("=" * 60)

    response = requests.post(f"{BASE_URL}/enb/cells/{cell_id}/deactivate")

    if response.status_code == 200:
        print("✓ Cell deactivated")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.json()}")
    print()


def attenuation_sweep(cell_id: int, start_gain: float, end_gain: float, step: float, delay: float = 2.0):
    """Perform an attenuation sweep on a cell.

    Args:
        cell_id: The cell ID to sweep.
        start_gain: Starting gain in dB.
        end_gain: Ending gain in dB.
        step: Step size in dB.
        delay: Delay between steps in seconds.
    """
    print("=" * 60)
    print(f"Attenuation Sweep on Cell {cell_id}")
    print(f"  From {start_gain} dB to {end_gain} dB, Step: {step} dB")
    print("=" * 60)

    current = start_gain
    direction = 1 if end_gain > start_gain else -1

    while (direction > 0 and current <= end_gain) or (direction < 0 and current >= end_gain):
        response = requests.post(
            f"{BASE_URL}/enb/cells/{cell_id}/gain",
            json={"gain": current},
        )

        if response.status_code == 200:
            print(f"  ✓ Gain: {current:6.1f} dB")
        else:
            print(f"  ✗ Failed at {current} dB: {response.json()}")

        current += step * direction
        time.sleep(delay)

    print("\n✓ Sweep complete")
    print()


def main():
    """Run cell management examples."""
    print("\n" + "=" * 60)
    print("  AMARISOFT REST API - Cell Management Examples")
    print("=" * 60)
    print(f"  Target: {BASE_URL}")
    print()

    try:
        # List all cells
        list_cells()

        # Example: Set cell gain (uncomment to use)
        # set_cell_gain(cell_id=1, gain=-30.0)

        # Example: Attenuation sweep (uncomment to use)
        # attenuation_sweep(cell_id=1, start_gain=-20, end_gain=-40, step=5, delay=1.0)

        # Example: Deactivate/reactivate cell (uncomment to use)
        # deactivate_cell(cell_id=1)
        # time.sleep(2)
        # activate_cell(cell_id=1)

    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to {BASE_URL}")
        print("Make sure the REST API service is running on the callbox.")


if __name__ == "__main__":
    main()
