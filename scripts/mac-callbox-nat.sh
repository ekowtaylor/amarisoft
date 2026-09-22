#!/bin/sh
# Share the Mac's internet with the Amarisoft callbox (and, through it, the UEs) using pf NAT.
# Temporary: IP forwarding and the pf rules are lost on reboot, and NordVPN connect/disconnect resets them.
#
# Usage: sudo ./mac-callbox-nat.sh up|down|status
#   CALLBOX_IF (default en5)  Mac USB-Ethernet interface to the callbox
#   LAN        (default 192.168.1.0/24)  callbox subnet
#   WAN_IFS    (default: default-route interface + en0)  egress interfaces to NAT on. The default-route
#              interface covers a VPN tunnel (e.g. NordVPN utunN) when one is up. Re-run "up" after a VPN change.
set -e
CALLBOX_IF=${CALLBOX_IF:-en5}; LAN=${LAN:-192.168.1.0/24}
WAN_IFS=${WAN_IFS:-$(echo "$(route -n get default 2>/dev/null | awk '/interface:/{print $2}') en0" | tr ' ' '\n' | awk 'NF && !s[$0]++' | tr '\n' ' ')}
TOKEN=/var/run/callbox-nat.token

# The main pf ruleset only evaluates anchors under its own root: com.apple/* (stock macOS) or main/*
# (NordVPN kill switch replaces the main ruleset). Load into whichever root is active.
root() { pfctl -s nat 2>/dev/null | grep -q 'nat-anchor "main/\*"' && echo main || echo com.apple; }

rules() {
  for w in $WAN_IFS; do
    for i in $(ifconfig -l); do case $i in $w) echo "nat on $i from $LAN to any -> ($i)";; esac; done
  done
  # needed when a VPN kill switch ruleset ends in "block drop all"; harmless otherwise
  echo "pass in quick on $CALLBOX_IF from $LAN to any keep state"
  echo "pass out quick on $CALLBOX_IF to $LAN keep state"
}

case "$1" in
  up)
    sysctl -w net.inet.ip.forwarding=1
    R=$(root); for o in com.apple main; do [ "$o" = "$R" ] || pfctl -a "$o/callbox-nat" -F all 2>/dev/null || true; done
    rules | pfctl -a "$R/callbox-nat" -f -
    pfctl -E 2>&1 | awk '/[Tt]oken/{print $NF}' > $TOKEN
    echo "loaded into anchor $R/callbox-nat:"; pfctl -a "$R/callbox-nat" -s nat ;;
  down)
    for R in com.apple main; do pfctl -a "$R/callbox-nat" -F all 2>/dev/null || true; done
    [ -s $TOKEN ] && pfctl -X "$(cat $TOKEN)" 2>/dev/null || true; rm -f $TOKEN
    sysctl -w net.inet.ip.forwarding=0 ;;
  status)
    sysctl net.inet.ip.forwarding; echo "active anchor root: $(root)"
    for R in com.apple main; do echo "-- $R/callbox-nat"; pfctl -a "$R/callbox-nat" -s nat 2>/dev/null; done ;;
  *) echo "usage: sudo $0 up|down|status"; exit 1 ;;
esac
