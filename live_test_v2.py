#!/usr/bin/env python3
"""Simple live test for Amarisoft Callbox."""

import json
from websocket import create_connection

# Configuration
HOST = "192.168.1.80"
ENB_PORT = 9001
MME_PORT = 9000


def send_msg(ws, method: str, params: dict | None = None) -> dict:
    """Send a message and return the response."""
    msg = {"message": method, "message_id": 1}
    if params:
        msg.update(params)
    ws.send(json.dumps(msg))
    return json.loads(ws.recv())


def main() -> None:
    """Run simple callbox tests."""
    print(f"Testing Amarisoft Callbox at {HOST}\n")

    # Test eNB
    print("--- eNB ---")
    try:
        ws = create_connection(f"ws://{HOST}:{ENB_PORT}", timeout=10)

        config = send_msg(ws, "config_get")
        print(f"Version: {config.get('version', 'unknown')}")

        stats = send_msg(ws, "stats")
        cells = stats.get("cells", {})
        print(f"Cells: {len(cells)}")

        ws.close()
        print("eNB: OK")
    except Exception as e:
        print(f"eNB: FAILED - {e}")

    # Test MME
    print("\n--- MME ---")
    try:
        ws = create_connection(f"ws://{HOST}:{MME_PORT}", timeout=10)

        ue_info = send_msg(ws, "ue_get")
        ue_list = ue_info.get("ue_list", [])
        print(f"UEs attached: {len(ue_list)}")
        for ue in ue_list:
            print(f"  IMSI: {ue.get('imsi', 'N/A')}")

        ws.close()
        print("MME: OK")
    except Exception as e:
        print(f"MME: FAILED - {e}")


if __name__ == "__main__":
    main()
