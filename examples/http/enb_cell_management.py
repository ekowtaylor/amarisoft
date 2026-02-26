#!/usr/bin/env python3
"""eNB/gNB cell management example for the Amarisoft Callbox (HTTP).

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

from client.http import APIError, Callbox


def parse_args():
    parser = argparse.ArgumentParser(description="eNB cell management examples (HTTP)")
    parser.add_argument("--url", default="http://127.0.0.1:9010", help="REST API URL")
    parser.add_argument("--api-key", default=None, help="API key for authentication")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        with Callbox(args.url, api_key=args.api_key) as cb:
            # --- Config info (replaces system_info which is not supported) ---
            print("=" * 60)
            print("Configuration Info")
            print("=" * 60)
            config = cb.enb.config_get()
            pprint(config)

            # --- Cell list from config ---
            print("\n" + "=" * 60)
            print("Cell List (from config)")
            print("=" * 60)
            cells = cb.enb.cells_get()
            pprint(cells)

            # --- Statistics ---
            print("\n" + "=" * 60)
            print("Statistics (with samples and RF)")
            print("=" * 60)
            stats = cb.enb.stats(samples=True, rf=True)
            pprint(stats)

            # --- Cell gain ---
            print("\n" + "=" * 60)
            print("Cell Gain — set cell 1 to -10 dB")
            print("=" * 60)
            try:
                result = cb.enb.cell_gain(cell_id=1, gain=-10)
                pprint(result)
            except APIError as e:
                print(f"cell_gain error: {e}")

            # --- RF parameters ---
            print("\n" + "=" * 60)
            print("RF Parameters — query current settings")
            print("=" * 60)
            rf = cb.enb.rf()
            pprint(rf)

            # --- DL/UL config ---
            print("\n" + "=" * 60)
            print("Downlink Config — set PDSCH MCS on cell 1")
            print("=" * 60)
            try:
                dl = cb.enb.set_dl_config(cell_id=1, pdsch_mcs=15)
                pprint(dl)
            except APIError as e:
                print(f"set_dl_config error: {e}")

            print("\n" + "=" * 60)
            print("Uplink Config — set PUSCH MCS on cell 1")
            print("=" * 60)
            try:
                ul = cb.enb.set_ul_config(cell_id=1, pusch_mcs=10)
                pprint(ul)
            except APIError as e:
                print(f"set_ul_config error: {e}")

            # --- Interface status ---
            print("\n" + "=" * 60)
            print("S1 Interface Status")
            print("=" * 60)
            try:
                s1 = cb.enb.s1_status()
                pprint(s1)
            except APIError as e:
                print(f"s1_status error: {e}")

            print("\n" + "=" * 60)
            print("NG Interface Status")
            print("=" * 60)
            try:
                ng = cb.enb.ng_status()
                pprint(ng)
            except APIError as e:
                print(f"ng_status error: {e}")

    except APIError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
