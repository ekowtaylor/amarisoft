#!/bin/bash
# Measure the NR link under UL+DL load: phone (root, adb) pings 8.8.8.8 over rmnet_data0 (1200 B, 100/s, 30 s)
# while gNB per-UE stats are sampled every 5 s via the remote API.
# Usage: CALLBOX_PASS=... [CALLBOX=192.168.1.80] ./linkmeas.sh
: "${CALLBOX_PASS:?set CALLBOX_PASS}"; CALLBOX=${CALLBOX:-192.168.1.80}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
printf '#!/bin/sh\necho "$CALLBOX_PASS"\n' > $T/ap.sh; chmod 700 $T/ap.sh; export CALLBOX_PASS
cb(){ SSH_ASKPASS=$T/ap.sh SSH_ASKPASS_REQUIRE=force DISPLAY=x ssh -o ConnectTimeout=5 -o PubkeyAuthentication=no root@$CALLBOX "$@"; }
adb shell 'su -c "ping -I rmnet_data0 -i 0.01 -s 1200 -w 30 -q 8.8.8.8"' > $T/ping.txt 2>&1 &
cb 'cd /root/lteots-linux-2024-09-13
for i in 1 2 3 4 5; do sleep 5; timeout 5 node ws.js 127.0.0.1:9001 "{\"message\":\"ue_get\",\"stats\":true}" 2>/dev/null | sed -n "/^{/,\$p" | python3 -c "
import json,sys
for u in json.load(sys.stdin).get(\"ue_list\",[]):
  for c in u.get(\"cells\",[]):
    tx=c.get(\"ul_tx\",0) or 0; rt=c.get(\"ul_retx\",0) or 0; dt=c.get(\"dl_tx\",0) or 0; dr=c.get(\"dl_retx\",0) or 0
    print(\"pusch_snr=%5s ul_mcs=%5s ul_retx=%3d%% ul_phr=%s | cqi=%s ri=%s dl_mcs=%5s dl_retx=%3d%% | pl=%s epre=%s\" % (c.get(\"pusch_snr\"),c.get(\"ul_mcs\"),100*rt//max(tx,1),c.get(\"ul_phr\"),c.get(\"cqi\"),c.get(\"ri\"),c.get(\"dl_mcs\"),100*dr//max(dt,1),c.get(\"ul_path_loss\"),c.get(\"epre\")))
"; done'
wait; tail -2 $T/ping.txt
adb shell 'dumpsys telephony.registry 2>/dev/null | grep -m1 -oE "ssRsrp = -?[0-9]+ ssRsrq = -?[0-9]+ ssSinr = -?[0-9]+"'
