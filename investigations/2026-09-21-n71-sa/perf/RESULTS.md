# n71 SA link tuning and throughput (SM-S936U1, 2026-09-21)

Cell: n71 20 MHz FDD 2x2, 15 kHz, DL 632–652 / UL 678–698 MHz, SSB 640.95 MHz (GSCN 1602), PDSCH/PUSCH `qam256`.
Setup: over the air, phone near the callbox; `tx_gain 90` (89.75 dB applied), `rx_gain 60`.

## 1. Closed-loop UL power control

[`gnb-sa-n71-working.cfg`](../configs/gnb-sa-n71-working.cfg) has no `dpc_snr_target`, so the UE stays at open-loop power
(`p0_nominal_with_grant: -84`) and transmits at ~−17 dBm. [`gnb-sa-n71-tuned.cfg`](../configs/gnb-sa-n71-tuned.cfg) adds:

```
pucch: { ... dpc_snr_target: 15, }   /* closed-loop PUCCH power control */
pusch: { ... dpc_snr_target: 20, }   /* closed-loop PUSCH power control */
```

Measured with [`linkmeas.sh`](linkmeas.sh) (1200 B ping @100/s over rmnet for 30 s, gNB stats every 5 s):

| Under load | working.cfg (open loop) | tuned.cfg (closed loop) |
|---|---|---|
| PUSCH SNR | −0.9 … +4.5 dB | 11 … 17 dB |
| UL MCS / UL retx | 0 / 22–59 % | ~10 / 8–11 % |
| DL CQI | jumps 0 … 15 (CQI reports lost) | stable 12 |
| DL rank | 1 / 2 | stable 2 |
| DL MCS / DL retx | 4–13 / 43–118 % (HARQ ACKs lost) | ~20 / 8–10 % |
| RTT avg / max | 99 / 1391 ms | 58 / 163 ms |
| gNB UL EPRE | −113 dBm | −95 dBm |
| UE SS-RSRP / SS-SINR | −66 dBm / 34 dB | −71 dBm / 36 dB |

A weak UL (PUCCH) also broke the DL: CQI reports and HARQ ACK/NACKs were lost.

## 2. iperf3 throughput (tuned.cfg)

Server `iperf3 -s -B 192.168.3.1` on the callbox (core side, no internet in the path); client iperf3 3.21 static arm64
([userdocs/iperf3-static](https://github.com/userdocs/iperf3-static), sha256 `2ce83dce…562c8e`) on the phone,
`--bind-dev rmnet_data0`, TCP, 4 streams, 20 s.

| Direction | Throughput | gNB during the test |
|---|---|---|
| DL (`-R`) | **63.7 Mbit/s** | RI 2, CQI 12, DL MCS 17–18, DL retx 22–28 % |
| UL | **11.4 Mbit/s** (13.1 Mbit/s on a repeat) | PUSCH SNR 13–16 dB, **UL MCS 2.7–3.4**, UL retx 11–12 %, **UE PHR 26 dB**, UL rank 1 |

Rough ceiling for this cell: ~190 Mbit/s DL (2 layers, 256QAM), ~90 Mbit/s UL (1 layer).

## 3. UL MIMO attempt: SRS enabled ([`gnb-sa-n71-ulmimo.cfg`](../configs/gnb-sa-n71-ulmimo.cfg))

Same as tuned.cfg with `#define USE_SRS 1`. This adds periodic codebook SRS (80 slots), sets PUCCH format 1 `n_symb: 12`,
and sets PUSCH `max_rank: N_ANTENNA_UL` (2).

**UL MIMO cannot engage with this UE.** UE-NR-Capability ([`../logs/ue_capability_nr.txt`](../logs/ue_capability_nr.txt)):
```
maxNumberMIMO-LayersCB-PUSCH oneLayer
maxNumberSRS-Ports-PerResource n1
maxNumberSRS-ResourcePerSet 1
pusch-TransCoherence nonCoherent
```
The gNB correctly kept UL rank 1 / 1 layer in every sample.

iperf3 (same method as section 2):

| | tuned.cfg (no SRS) | ulmimo.cfg (SRS on) |
|---|---|---|
| **UL throughput** | 11.4 / 13.1 Mbit/s | **18.1 / 18.3 Mbit/s** |
| UL rank / layers | 1 / 1 | 1 / 1 |
| PUSCH SNR | 13–16 dB | 11–17 dB |
| UL MCS | 2.7–3.4 | 8–10 |
| UL retx / tx | 11–12 % | **80–98 %** |
| UE PHR | 26 dB | 24–32 dB |
| DL throughput | 63.7 Mbit/s | 56.9 Mbit/s (DL retx 14–26 %) |

With SRS on, UL link adaptation runs at a much higher MCS. That gives +50 % UL throughput, but it comes from HARQ
retransmissions (almost every UL TB is retransmitted), not from clean first transmissions. The underlying UL impairment
(see below) remains. The DL difference is within over-the-air run-to-run variance.

Trade-off: use `ulmimo.cfg` for peak UL throughput, or `tuned.cfg` for a cleaner UL (≈10 % retx).

## Open findings

- **UL MCS far below what the measured SNR supports.** The UE has 26 dB power headroom and PUSCH SNR is ~15 dB, but link
  adaptation settles at MCS ~3 to hold ~10 % BLER. Something the SNR estimate does not capture is corrupting PUSCH. Candidate:
  bursty in-band interference, because the UL (678–698 MHz) lies in the live T-Mobile n71 UL band. Verify cabled / in a shield box.
- **DL retx 22–28 % under full load**, above the 10 % target. This also points at interference or over-the-air fading.
- ~~UL MIMO disabled~~ Tested (section 3). Not possible with the SM-S936U1: it supports only 1-layer codebook PUSCH and 1 SRS port.
- Not changed: `rx_gain` (60 dB) and `tx_gain` (at maximum).
