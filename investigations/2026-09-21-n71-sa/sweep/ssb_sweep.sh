#!/bin/bash
# n71 SA SSB sweep: for each GSCN, pin the SSB on the callbox, restart, kick the phone, poll gNB for a UE.
# Usage: CALLBOX_PASS=... [CALLBOX=192.168.1.80] [WAIT=50] [CSV=./sweep.csv] ./ssb_sweep.sh <gscn> [<gscn> ...]
# Needs: adb-connected phone; /root/enb/config/gnb-sa-n71.cfg on the callbox (its "dl_nr_arfcn: 126900" line is
# rewritten per GSCN into gnb-sa-n71-sweep.cfg); ws.js from the lteots package on the callbox.
: "${CALLBOX_PASS:?set CALLBOX_PASS}"
CALLBOX=${CALLBOX:-192.168.1.80}; CSV=${CSV:-./sweep.csv}; WAIT=${WAIT:-45}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
printf '#!/bin/sh\necho "$CALLBOX_PASS"\n' > $T/ap.sh; chmod 700 $T/ap.sh; export CALLBOX_PASS
[ -s $CSV ] || echo "gscn,ssb_mhz,dl_nr_arfcn,gnb_ssb_arfcn,result,seconds" > $CSV
cb() { perl -e "alarm shift; exec @ARGV" ${CBT:-90} env SSH_ASKPASS=$T/ap.sh SSH_ASKPASS_REQUIRE=force DISPLAY=x ssh -o ConnectTimeout=5 -o PubkeyAuthentication=no root@$CALLBOX "$@"; }

for G in "$@"; do
  # GSCN -> SS_ref (TS 38.104 5.4.3.1, FR1 < 3 GHz): GSCN = 3N + (M-3)/2, SS_ref = N*1200 kHz + M*50 kHz
  r=$(( G % 3 )); case $r in 0) M=3; N=$(( G/3 ));; 1) M=5; N=$(( (G-1)/3 ));; 2) M=1; N=$(( (G+1)/3 ));; esac
  KHZ=$(( N*1200 + M*50 )); MHZ=$(echo "scale=2; $KHZ/1000" | bc)
  # 20 MHz carrier placement covering the SSB (SSB is 3.6 MHz wide)
  if [ $KHZ -le 634000 ]; then ARFCN=125400; else ARFCN=128400; fi   # 627 / 642 MHz centers
  out=$(cb "cd /root/enb/config
    sed -e 's#dl_nr_arfcn: 126900,.*#dl_nr_arfcn: $ARFCN,\n    gscn: $G,#' gnb-sa-n71.cfg > gnb-sa-n71-sweep.cfg
    ln -sfn gnb-sa-n71-sweep.cfg enb.cfg; systemctl restart lte
    for i in \$(seq 1 30); do sleep 2; ss -lnt | grep -q ':9001 ' && break; done
    grep -oE 'ssb_arfcn=[0-9]+' /tmp/gnb0.log | head -1" 2>&1)
  SSBA=$(echo "$out" | grep -oE '[0-9]+$')
  if [ -z "$SSBA" ]; then echo "$G,$MHZ,$ARFCN,,gnb_start_fail,0" >> $CSV; echo "GSCN $G ($MHZ MHz): gNB failed to start"; continue; fi
  adb shell cmd connectivity airplane-mode enable; adb shell cmd connectivity airplane-mode disable
  res=no_ue; t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt $WAIT ]; do
    n=$(CBT=15 cb "cd /root/lteots-linux-2024-09-13; timeout 5 node ws.js 127.0.0.1:9001 '{\"message\":\"ue_get\"}' 2>/dev/null | grep -c '\"rnti\"'" 2>/dev/null)
    [ "${n:-0}" -gt 0 ] && { res=UE_ATTACHED; break; }
    sleep 3
  done
  echo "$G,$MHZ,$ARFCN,$SSBA,$res,$(( $(date +%s) - t0 ))" >> $CSV
  echo "GSCN $G ($MHZ MHz, ssb_arfcn=$SSBA): $res"
done
