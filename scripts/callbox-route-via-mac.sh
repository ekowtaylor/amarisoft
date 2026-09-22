#!/bin/sh
# Run ON THE CALLBOX (as root): send its internet traffic through the Mac (192.168.1.20) and set DNS.
# Runtime only: nothing is written to NetworkManager, so a reboot or reconnect restores the saved gateway (192.168.1.1).
# The saved default route is kept; ours wins because of its lower metric (10 vs 100).
#
# Usage: ./callbox-route-via-mac.sh up|down|status   [MAC_IP=192.168.1.20] [IFACE=eno1]
MAC_IP=${MAC_IP:-192.168.1.20}; IFACE=${IFACE:-eno1}
case "$1" in
  up)
    ip route replace default via "$MAC_IP" dev "$IFACE" metric 10
    resolvectl dns "$IFACE" 8.8.8.8 1.1.1.1
    ping -c2 -W3 8.8.8.8 >/dev/null && echo "internet OK" || echo "internet FAILED (is the Mac NAT up?)"
    getent hosts google.com >/dev/null && echo "DNS OK" || echo "DNS FAILED" ;;
  down)
    ip route del default via "$MAC_IP" dev "$IFACE" metric 10 2>/dev/null || true
    resolvectl revert "$IFACE" ;;
  status)
    ip route show default; resolvectl dns "$IFACE"
    ss -tn | grep -q ':9050 ' && echo "license server: connected" || echo "license server: NOT connected" ;;
  *) echo "usage: $0 up|down|status"; exit 1 ;;
esac
