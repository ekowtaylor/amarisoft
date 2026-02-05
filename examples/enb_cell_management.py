#!/usr/bin/env python3
"""eNB/gNB cell management example for the Amarisoft Callbox.

Demonstrates:
- System info and cell listing
- Statistics with samples and RF data
- Cell gain adjustment
- RF parameter control
- Downlink/uplink configuration
- S1 and NG interface status
"""

import argparse
from pprint import pprint

from amarisoft import Callbox, AmariError


def parse_args():
    parser = argparse.ArgumentParser(description="eNB cell management examples")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl) as cb:
            # --- System info ---
            print("=" * 60)
            print("System Info")
            print("=" * 60)
            info = cb.enb.system_info()
            pprint(info)

            # --- Cell list ---
            print("\n" + "=" * 60)
            print("Cell List")
            print("=" * 60)
            cells = cb.enb.cell_list()
            pprint(cells)

            # --- Statistics ---
            print("\n" + "=" * 60)
            print("Statistics (with samples and RF)")
            print("=" * 60)
            stats = cb.enb.stats(samples=True, rf=True)
            pprint(stats)

            # --- Cell gain ---
            # Adjust gain on cell 1 (use with caution on live systems)
            print("\n" + "=" * 60)
            print("Cell Gain — set cell 1 to -10 dB")
            print("=" * 60)
            try:
                result = cb.enb.cell_gain(cell_id=1, gain=-10)
                pprint(result)
            except AmariError as e:
                print(f"cell_gain error: {e}")

            # --- RF parameters ---
            print("\n" + "=" * 60)
            print("RF Parameters — query current settings")
            print("=" * 60)
            rf = cb.enb.rf()
            pprint(rf)

            # Set specific TX/RX gains (uncomment to use)
            # rf_set = cb.enb.rf(tx_gain=60.0, rx_gain=60.0)
            # pprint(rf_set)

            # --- DL/UL config ---
            print("\n" + "=" * 60)
            print("Downlink Config — set PDSCH MCS on cell 1")
            print("=" * 60)
            try:
                dl = cb.enb.set_dl_config(cell_id=1, pdsch_mcs=15)
                pprint(dl)
            except AmariError as e:
                print(f"set_dl_config error: {e}")

            print("\n" + "=" * 60)
            print("Uplink Config — set PUSCH MCS on cell 1")
            print("=" * 60)
            try:
                ul = cb.enb.set_ul_config(cell_id=1, pusch_mcs=10)
                pprint(ul)
            except AmariError as e:
                print(f"set_ul_config error: {e}")

            # --- Interface status ---
            print("\n" + "=" * 60)
            print("S1 Interface Status")
            print("=" * 60)
            try:
                s1 = cb.enb.s1_status()
                pprint(s1)
            except AmariError as e:
                print(f"s1_status error: {e}")

            print("\n" + "=" * 60)
            print("NG Interface Status")
            print("=" * 60)
            try:
                ng = cb.enb.ng_status()
                pprint(ng)
            except AmariError as e:
                print(f"ng_status error: {e}")

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
