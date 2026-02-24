#!/usr/bin/env python3
"""Cell configuration example for the Amarisoft Callbox (HTTP).

Demonstrates:
- Listing and inspecting cell configurations
- Adjusting cell gain and RF parameters
- Setting cell-level parameters (MCS, timers, etc.)
- Carrier aggregation (activating/deactivating secondary cells)
- Neighbor cell management
- Noise level and SNR monitoring
"""

import argparse

from client.http import Callbox, APIError


def parse_args():
    parser = argparse.ArgumentParser(
        description="Cell configuration examples (HTTP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List cells and show configuration
  python cell_config_example.py --url http://192.168.1.80:9010

  # Adjust cell gain
  python cell_config_example.py --url http://192.168.1.80:9010 --cell-id 1 --gain -3

  # Set fixed MCS
  python cell_config_example.py --url http://192.168.1.80:9010 --cell-id 1 --dl-mcs 15 --ul-mcs 10
        """,
    )
    parser.add_argument("--url", default="http://127.0.0.1:9010", help="REST API URL")
    parser.add_argument("--api-key", default=None, help="API key for authentication")
    parser.add_argument(
        "--cell-id", type=int, default=None,
        help="Target cell ID for configuration changes",
    )
    parser.add_argument(
        "--gain", type=float, default=None,
        help="Set cell gain in dB (can be negative)",
    )
    parser.add_argument(
        "--dl-mcs", type=int, default=None,
        help="Set fixed downlink MCS (0-28 for LTE, 0-27 for NR)",
    )
    parser.add_argument(
        "--ul-mcs", type=int, default=None,
        help="Set fixed uplink MCS (0-28 for LTE, 0-27 for NR)",
    )
    parser.add_argument(
        "--tx-gain", type=float, default=None,
        help="Set TX gain in dB",
    )
    parser.add_argument(
        "--rx-gain", type=float, default=None,
        help="Set RX gain in dB",
    )
    return parser.parse_args()


def example_list_cells(cb):
    """List all configured cells."""
    print("\n" + "=" * 60)
    print("Cell List")
    print("=" * 60)

    try:
        # Get cell list from stats
        stats = cb.enb.stats()
        cells_dict = stats.get("cells", {})

        if not cells_dict:
            print("\nNo cells found in stats response.")
            return {}

        print(f"\nFound {len(cells_dict)} cell(s):\n")
        print(f"{'Cell ID':>8} {'DL Bitrate':>12} {'UL Bitrate':>12} {'UE Count':>10}")
        print("-" * 50)

        # cells is a dict with cell_id as key
        for cell_id, cell_data in cells_dict.items():
            dl_bitrate = format_bps(cell_data.get("dl_bitrate", 0))
            ul_bitrate = format_bps(cell_data.get("ul_bitrate", 0))
            ue_count = cell_data.get("ue_count_avg", cell_data.get("ue_count", 0))

            print(f"{cell_id:>8} {dl_bitrate:>12} {ul_bitrate:>12} {ue_count:>10.0f}")

        return cells_dict

    except APIError as e:
        print(f"Error listing cells: {e}")
        return {}


def example_cell_stats(cb, cell_id=None):
    """Get detailed statistics for cells."""
    print("\n" + "=" * 60)
    print("Cell Statistics")
    print("=" * 60)

    try:
        stats = cb.enb.stats()
        cells_dict = stats.get("cells", {})

        for cid, cell_data in cells_dict.items():
            if cell_id is not None and int(cid) != cell_id:
                continue

            print(f"\nCell {cid}:")
            print(f"  DL Bitrate: {format_bps(cell_data.get('dl_bitrate', 0))}")
            print(f"  UL Bitrate: {format_bps(cell_data.get('ul_bitrate', 0))}")
            print(f"  DL TX: {cell_data.get('dl_tx', 0)}")
            print(f"  UL TX: {cell_data.get('ul_tx', 0)}")
            print(f"  DL Errors: {cell_data.get('dl_err', 0)}")
            print(f"  UL Errors: {cell_data.get('ul_err', 0)}")
            print(f"  UE Count (avg): {cell_data.get('ue_count_avg', 0):.1f}")
            print(f"  DL Usage (avg): {cell_data.get('dl_use_avg', 0):.1%}")
            print(f"  UL Usage (avg): {cell_data.get('ul_use_avg', 0):.1%}")

    except APIError as e:
        print(f"Error getting cell stats: {e}")


def example_get_config(cb, cell_id=None):
    """Get current cell configuration."""
    print("\n" + "=" * 60)
    print("Cell Configuration")
    print("=" * 60)

    try:
        config = cb.enb.config_get()

        # Extract cell configurations
        cells_config = config.get("cells", {})

        if not cells_config:
            print("\nNo cell configuration found.")
            return

        for cid, cell_cfg in cells_config.items():
            if cell_id is not None and int(cid) != cell_id:
                continue

            print(f"\nCell {cid} Configuration:")

            # Common parameters
            common_params = [
                ("dl_earfcn", "DL EARFCN"),
                ("ul_earfcn", "UL EARFCN"),
                ("n_rb_dl", "DL RBs"),
                ("n_rb_ul", "UL RBs"),
                ("pci", "PCI"),
                ("tac", "TAC"),
                ("root_sequence_index", "Root Seq Index"),
                ("pdsch_mcs", "PDSCH MCS (fixed)"),
                ("pusch_mcs", "PUSCH MCS (fixed)"),
                ("inactivity_timer", "Inactivity Timer"),
            ]

            for key, label in common_params:
                if key in cell_cfg:
                    print(f"  {label}: {cell_cfg[key]}")

    except APIError as e:
        print(f"Error getting config: {e}")


def example_set_cell_gain(cb, cell_id, gain):
    """Adjust cell gain."""
    print("\n" + "=" * 60)
    print(f"Setting Cell {cell_id} Gain to {gain} dB")
    print("=" * 60)

    try:
        result = cb.enb.cell_gain(cell_id=cell_id, gain=gain)
        print(f"\n✓ Cell gain set successfully")
        print(f"  Response: {result.get('message', 'OK')}")
    except APIError as e:
        print(f"\n✗ Failed to set cell gain: {e}")


def example_set_rf_gain(cb, tx_gain=None, rx_gain=None):
    """Set RF TX/RX gain."""
    print("\n" + "=" * 60)
    print("Setting RF Gain")
    print("=" * 60)

    try:
        # First get current values
        current = cb.enb.rf_gain()
        print(f"\nCurrent RF Gain:")
        print(f"  TX Gain: {current.get('tx_gain', 'N/A')} dB")
        print(f"  RX Gain: {current.get('rx_gain', 'N/A')} dB")

        # Set new values
        if tx_gain is not None or rx_gain is not None:
            result = cb.enb.rf_gain(tx_gain=tx_gain, rx_gain=rx_gain)
            print(f"\nNew RF Gain:")
            if tx_gain is not None:
                print(f"  TX Gain: {tx_gain} dB ✓")
            if rx_gain is not None:
                print(f"  RX Gain: {rx_gain} dB ✓")

    except APIError as e:
        print(f"\n✗ Failed to set RF gain: {e}")


def example_set_mcs(cb, cell_id, dl_mcs=None, ul_mcs=None):
    """Set fixed MCS for a cell."""
    print("\n" + "=" * 60)
    print(f"Setting Fixed MCS for Cell {cell_id}")
    print("=" * 60)

    params = {}
    if dl_mcs is not None:
        params["pdsch_mcs"] = dl_mcs
        print(f"\n  Setting DL MCS (PDSCH): {dl_mcs}")
    if ul_mcs is not None:
        params["pusch_mcs"] = ul_mcs
        print(f"  Setting UL MCS (PUSCH): {ul_mcs}")

    if not params:
        print("\nNo MCS values specified.")
        return

    try:
        result = cb.enb.config_set_cell(cell_id, **params)
        print(f"\n✓ MCS configuration applied")
    except APIError as e:
        print(f"\n✗ Failed to set MCS: {e}")


def example_carrier_aggregation(cb):
    """Demonstrate carrier aggregation commands."""
    print("\n" + "=" * 60)
    print("Carrier Aggregation Info")
    print("=" * 60)

    try:
        # Get UEs to check for CA capability
        ues = cb.enb.ue_get()
        ue_list = ues.get("ue_list", [])

        if not ue_list:
            print("\nNo UEs connected. CA examples require connected UEs.")
            print("\nCA API functions available:")
            print("  cb.enb.scells_act_deact(enb_ue_id, scell_ids, activate)")
            print("  cb.enb.nr_pscell_change(enb_ue_id, target_cell_id)")
            return

        print(f"\nConnected UEs ({len(ue_list)}):")
        for ue in ue_list:
            enb_ue_id = ue.get("enb_ue_id")
            pcell = ue.get("cell_id", "N/A")
            scells = ue.get("scell_list", [])

            print(f"\n  UE {enb_ue_id}:")
            print(f"    PCell: {pcell}")
            if scells:
                print(f"    SCells: {scells}")
            else:
                print(f"    SCells: None (no CA active)")

    except APIError as e:
        print(f"Error: {e}")


def format_bps(bps):
    """Format bits-per-second as human-readable string."""
    if bps >= 1_000_000_000:
        return f"{bps / 1_000_000_000:.2f} Gbps"
    if bps >= 1_000_000:
        return f"{bps / 1_000_000:.2f} Mbps"
    if bps >= 1_000:
        return f"{bps / 1_000:.2f} kbps"
    return f"{bps:.0f} bps"


def main():
    args = parse_args()

    print("=" * 60)
    print("Cell Configuration Examples (HTTP)")
    print("=" * 60)
    print(f"REST API URL: {args.url}")

    try:
        with Callbox(args.url, api_key=args.api_key) as cb:

            # Example 1: List all cells
            cells = example_list_cells(cb)

            # Example 2: Cell statistics
            example_cell_stats(cb, args.cell_id)

            # Example 3: Get current configuration
            example_get_config(cb, args.cell_id)

            # Example 4: Carrier Aggregation
            example_carrier_aggregation(cb)

            # Apply configuration changes if requested
            if args.cell_id is not None:
                # Set cell gain
                if args.gain is not None:
                    example_set_cell_gain(cb, args.cell_id, args.gain)

                # Set MCS
                if args.dl_mcs is not None or args.ul_mcs is not None:
                    example_set_mcs(cb, args.cell_id, args.dl_mcs, args.ul_mcs)

            # Set RF gain (applies globally)
            if args.tx_gain is not None or args.rx_gain is not None:
                example_set_rf_gain(cb, args.tx_gain, args.rx_gain)

            # Summary
            print("\n" + "=" * 60)
            print("Configuration Complete")
            print("=" * 60)
            print("\nCell configuration functions demonstrated.")

    except APIError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
