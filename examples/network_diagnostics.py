#!/usr/bin/env python3
"""Network diagnostics example for the Amarisoft Callbox.

Demonstrates:
- Collecting version info from all services
- Checking cell status and interface connectivity
- Enumerating connected eNBs/gNBs, UEs, sessions, and bearers
- Quick health-check summary
"""

import argparse
from pprint import pprint

from amarisoft import Callbox, AmariError, CommandError


def parse_args():
    parser = argparse.ArgumentParser(description="Callbox network diagnostics")
    parser.add_argument("--host", default="127.0.0.1", help="Callbox IP address")
    parser.add_argument("--password", default=None, help="Authentication password")
    parser.add_argument("--ssl", action="store_true", help="Use WSS (TLS)")
    parser.add_argument(
        "--ssl-verify", action="store_true",
        help="Verify TLS certificates (default: no verification)",
    )
    return parser.parse_args()


def section(title):
    print(f"\n{'=' * 60}")
    print(title)
    print("=" * 60)


def safe_call(fn, *args, **kwargs):
    """Call fn and return result, or print error and return None."""
    try:
        return fn(*args, **kwargs)
    except (AmariError, CommandError) as e:
        print(f"  Error: {e}")
        return None


def main():
    args = parse_args()

    try:
        with Callbox(args.host, password=args.password, ssl=args.ssl,
                     ssl_verify=args.ssl_verify) as cb:

            # --- Connection status ---
            section("Connection Status")
            pprint(cb.status)

            # --- Versions ---
            section("Service Versions")
            for name, api in [("eNB", cb.enb), ("MME", cb.mme),
                              ("IMS", cb.ims), ("UE Sim", cb.ue)]:
                ver = safe_call(api.version)
                if ver:
                    print(f"  {name}: {ver.get('version', 'unknown')}")

            # --- eNB system info ---
            section("eNB System Info")
            info = safe_call(cb.enb.system_info)
            if info:
                pprint(info)

            # --- Cell list ---
            section("Cell List")
            cells = safe_call(cb.enb.cell_list)
            if cells:
                cell_list = cells.get("cell_list", [])
                for cell in cell_list:
                    cid = cell.get("cell_id", "?")
                    state = cell.get("state", "?")
                    print(f"  Cell {cid}: {state}")
                if not cell_list:
                    print("  (no cells)")

            # --- Interface status ---
            section("S1 Interface Status")
            s1 = safe_call(cb.enb.s1_status)
            if s1:
                pprint(s1)

            section("NG Interface Status")
            ng = safe_call(cb.enb.ng_status)
            if ng:
                pprint(ng)

            # --- Connected base stations (from MME) ---
            section("MME — Connected eNBs")
            enbs = safe_call(cb.mme.enb_get)
            if enbs:
                enb_list = enbs.get("enb_list", [])
                print(f"  Count: {len(enb_list)}")
                for e in enb_list:
                    print(f"    {e}")

            section("MME — Connected gNBs")
            gnbs = safe_call(cb.mme.gnb_get)
            if gnbs:
                gnb_list = gnbs.get("gnb_list", [])
                print(f"  Count: {len(gnb_list)}")
                for g in gnb_list:
                    print(f"    {g}")

            # --- UEs ---
            section("eNB — Connected UEs")
            enb_ues = safe_call(cb.enb.ue_get)
            enb_ue_count = len(enb_ues.get("ue_list", [])) if enb_ues else 0
            print(f"  Count: {enb_ue_count}")

            section("MME — Registered UEs")
            mme_ues = safe_call(cb.mme.ue_get)
            mme_ue_count = len(mme_ues.get("ue_list", [])) if mme_ues else 0
            print(f"  Count: {mme_ue_count}")

            # --- Sessions and bearers ---
            section("MME — Active Sessions")
            sessions = safe_call(cb.mme.session_get)
            if sessions:
                sess_list = sessions.get("session_list", [])
                print(f"  Count: {len(sess_list)}")

            section("MME — Active Bearers")
            bearers = safe_call(cb.mme.bearer_get)
            if bearers:
                bearer_list = bearers.get("bearer_list", [])
                print(f"  Count: {len(bearer_list)}")

            # --- IMS ---
            section("IMS — Registered Users")
            ims_users = safe_call(cb.ims.users_get, registered_only=True)
            if ims_users:
                user_list = ims_users.get("user_list", [])
                print(f"  Count: {len(user_list)}")
                for u in user_list:
                    print(f"    {u.get('impu', '?')}")

            # --- RF stats ---
            section("eNB — RF Status")
            rf = safe_call(cb.enb.rf)
            if rf:
                pprint(rf)

            # --- Summary ---
            section("Health Summary")
            status = cb.status
            all_ok = all(status.values())
            print(f"  All services connected: {'YES' if all_ok else 'NO'}")
            for svc, connected in status.items():
                print(f"    {svc}: {'OK' if connected else 'DISCONNECTED'}")
            print(f"  eNB UEs: {enb_ue_count}  MME UEs: {mme_ue_count}")

    except AmariError as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
