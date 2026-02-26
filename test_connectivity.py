#!/usr/bin/env python3
"""Test script to verify HTTPOverSSHClient connectivity to Amarisoft box."""

import sys

sys.path.insert(0, ".")

from client.http_ssh import HTTPOverSSHClient

# Configuration - Update these values for your Amarisoft box
SSH_HOST = "2620:10d:c052:12a:aaa1:59ff:fe88:d39"  # IPv6 address of Amarisoft box
SSH_USERNAME = "root"
SSH_PASSWORD = "toor"
SSH_KEY_PATH = None
REMOTE_PORT = 9010  # Default Amarisoft REST API port


def main():
    print("=" * 60)
    print("HTTPOverSSHClient Connectivity Test")
    print("=" * 60)

    client = HTTPOverSSHClient(
        ssh_host=SSH_HOST,
        ssh_username=SSH_USERNAME,
        ssh_password=SSH_PASSWORD,
        ssh_key_path=SSH_KEY_PATH,
        remote_port=REMOTE_PORT,
    )

    print(f"\nTarget: {SSH_USERNAME}@{SSH_HOST}")
    print(f"Remote API port: {REMOTE_PORT}")
    print(f"Local tunnel port: {client.local_port}")

    # Step 1: Check if SSH service is reachable
    print("\n[1] Checking SSH service reachability...")
    if client.is_listening():
        print("    ✓ SSH service is reachable")
    else:
        print("    ✗ SSH service is NOT reachable")
        print(f"    Make sure {SSH_HOST}:22 is accessible from this machine")
        return 1

    # Step 2: Establish SSH tunnel
    print("\n[2] Establishing SSH tunnel...")
    try:
        client.connect()
        print(f"    ✓ SSH tunnel established")
        print(f"    Tunnel: localhost:{client.local_port} -> {SSH_HOST}:{REMOTE_PORT}")
    except Exception as e:
        print(f"    ✗ Failed to establish tunnel: {e}")
        return 1

    # Step 3: Check tunnel is active
    print("\n[3] Verifying tunnel is active...")
    if client.is_tunnel_active():
        print("    ✓ Tunnel is active")
    else:
        print("    ✗ Tunnel is NOT active")
        client.close()
        return 1

    # Step 4: Test REST API health check
    print("\n[4] Testing REST API health check...")
    try:
        health = client.health_check()
        print(f"    ✓ REST API is healthy")
        print(f"    Response: {health}")
    except Exception as e:
        print(f"    ✗ Health check failed: {e}")
        print("    The SSH tunnel works, but REST API may not be running")

    # Step 5: Try to get some stats
    print("\n[5] Fetching eNB/gNB stats...")
    try:
        stats = client.get("/")
        print(f"    ✓ Got response from REST API")
        print(f"    Response: {stats}")
    except Exception as e:
        print(f"    ✗ Failed to get stats: {e}")

    # Cleanup
    print("\n[6] Closing tunnel...")
    client.close()
    print("    ✓ Tunnel closed")

    print("\n" + "=" * 60)
    print("Connectivity test completed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
