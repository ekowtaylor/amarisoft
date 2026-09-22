# Host network setup: Mac ↔ callbox ↔ UEs, sharing the Mac's internet

How the Mac is connected to the Amarisoft callbox, and how the Mac's internet is shared with the callbox and, through it,
the UEs. Validated 2026-09-21 on a MacBook (macOS 26) with a USB 10/100/1000 LAN adapter (Realtek) and a Callbox Mini.

## Why the callbox needs internet

| Need | Without internet |
|---|---|
| **Floating license** (the license server is on the internet, TCP 9050) | The OTS log shows `License error: ... ltemme.key error 0xb`; **ENB/MME never start** and the remote API ports stay closed |
| NTP (chrony) | The clock drifts; we saw a −586 s step as soon as the callbox got internet |
| UE data (internet PDU sessions) | The UEs register, but data to the internet fails |

## Topology

```
 UE (S25+ / SIM8230G)                 Callbox (Amarisoft)                          Mac                       Internet
 192.168.3.x  internet DNN   ──NR──►  tun1 192.168.3.1                                                       
 192.168.4.x  ims DNN                 tun2 192.168.4.1                                                      
                                        │  NAT #1: lte_init.sh                                              
                                        │  MASQUERADE -o eno1                                               
                                      eno1 192.168.1.80/24 ──USB-Eth──► en5 192.168.1.20/24 (no router)    
                                        default via 192.168.1.20 metric 10    │  NAT #2: pf anchor          
                                        (saved GW 192.168.1.1, metric 100)    │  <root>/callbox-nat         
                                                                              en0 Wi-Fi (default route) ──► 🌐
```

Two NAT stages: the callbox masquerades UE traffic to its own `192.168.1.80` (Amarisoft `lte_init.sh`, installed by
the `lte` service), then the Mac's pf masquerades `192.168.1.0/24` onto Wi-Fi (or onto the VPN tunnel if it is the default route).

## Setup

### 1. Mac: USB-Ethernet adapter (once, persistent)

- **Static IP, no router:** System Settings → Network → *USB 10/100/1000 LAN* → Details → TCP/IP → Manually,
  `192.168.1.20` / `255.255.255.0`, Router empty. Equivalent: `networksetup -setmanual "USB 10/100/1000 LAN" 192.168.1.20 255.255.255.0`.
  With no router, the adapter never becomes the Mac's default route, so the Mac's own internet stays on Wi-Fi.
- **Service order:** Wi-Fi above the USB adapter (Network → ⋯ → Set Service Order). Otherwise a DHCP-configured adapter
  can take the default route and cut the Mac's internet.
- Check: `route -n get default` shows `interface: en0`, and `ping 192.168.1.80` works.

### 2. Mac: NAT (each boot, and after any VPN change)

```sh
sudo scripts/mac-callbox-nat.sh up       # forwarding on + pf NAT; also: status | down
```
From a non-interactive shell (e.g. an agent), use the macOS password dialog:
`osascript -e 'do shell script "sh scripts/mac-callbox-nat.sh up" with administrator privileges'`.

- Rules live in a pf **anchor**, and the system `/etc/pf.conf` is not modified. The script loads into `com.apple/callbox-nat` on stock
  macOS, or `main/callbox-nat` when a NordVPN kill switch owns the main ruleset. It detects which one applies.
- NAT egress = the default-route interface + `en0`.

### 3. Callbox: route and DNS through the Mac (each callbox boot)

```sh
ssh root@192.168.1.80 'sh -s up' < scripts/callbox-route-via-mac.sh     # also: status | down
```
Adds `default via 192.168.1.20 dev eno1 metric 10` (the saved `192.168.1.1` default stays at metric 100) and runtime DNS
`8.8.8.8 1.1.1.1` via `resolvectl`. NetworkManager config is untouched.

### 4. Verify

| Where | Check | Expect |
|---|---|---|
| Mac | `sudo scripts/mac-callbox-nat.sh status` | forwarding 1, one `nat on en0 … 192.168.1.0/24` rule |
| Callbox | `sh callbox-route-via-mac.sh status` | default via 192.168.1.20 metric 10, `license server: connected` |
| Callbox | `ping 8.8.8.8`, `getent hosts google.com` | replies, and DNS resolves |
| UE | ping 8.8.8.8 over the cellular interface | replies |

## What persists

| Item | Persistent? | Lost when |
|---|---|---|
| Mac adapter static IP / service order | ✅ | never (macOS network settings) |
| Mac IP forwarding + pf NAT | ❌ | Mac reboot; **NordVPN connect/disconnect resets both** |
| Callbox default route via Mac + DNS | ❌ | callbox reboot, NetworkManager reconnect |
| Callbox UE NAT (`lte_init.sh` MASQUERADE) | ✅ | re-applied by the `lte` service |

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Mac loses internet when the adapter is plugged in | The adapter got a router/default route (DHCP or service order). Set it to Manual with no router; put Wi-Fi first |
| Callbox ping to 8.8.8.8 fails, packets reach en5 but never leave | **NordVPN kill switch**: its pf ruleset ends in `block drop all` and ignores `com.apple/*` anchors. Disconnect the VPN or turn off the kill switch, then `mac-callbox-nat.sh up` again |
| It worked, then stopped after connecting or disconnecting the VPN | The VPN reset forwarding and pf. Run `mac-callbox-nat.sh up` again |
| ENB/MME not running, ports 9000/9001 closed, OTS `License error … 0xb` | The callbox has no internet: check the Mac NAT and the callbox route, then `systemctl restart lte` |
| Log timestamps jump by minutes | chrony stepped the clock when NTP became reachable. Harmless |
| UEs registered but no internet | Check the callbox route and the Mac NAT; check that the UE's DNN is `internet` (not only `ims`) |

## Teardown

```sh
ssh root@192.168.1.80 'sh -s down' < scripts/callbox-route-via-mac.sh
sudo scripts/mac-callbox-nat.sh down
```
