# Golden configs

Validated reference configs for the Amarisoft Callbox Mini (lteenb/ltemme 2024-09-13, 1× PCIe SDR 2T2R).

## [`gnb-sa-n71.cfg`](gnb-sa-n71.cfg): NR SA n71, 20 MHz FDD, 2x2, closed-loop UL PC, RedCap enabled

| Setting | Value | Why |
|---|---|---|
| Band / duplex / SCS | n71 FDD, 15 kHz | |
| Bandwidth / MIMO | 20 MHz, DL 2x2, UL 1 layer | UE reaches DL rank 2 |
| Carrier | `dl_nr_arfcn: 128400` (DL 632–652, UL 678–698 MHz) | |
| **SSB** | **`gscn: 1602` → 640.95 MHz** | **Required.** SSBs at ~625–635 MHz are never accessed by the SM-S936U1 ([#2](https://github.com/ekowtaylor/amarisoft/issues/2)). The automatic SSB lands at 633.75 MHz. |
| **UL power control** | **closed loop: `pusch.dpc_snr_target: 20`, `pucch.dpc_snr_target: 15`** | **Required.** Open loop leaves UL SNR ≈ 0 dB, and DL CQI/HARQ feedback is lost ([#5](https://github.com/ekowtaylor/amarisoft/issues/5)). |
| SRS | off (`USE_SRS 0`) | The SM-S936U1 supports 1 UL layer only; SRS only makes UL link adaptation aggressive (~90 % retx). |
| **RedCap** | **`redcap_ue: { half_duplex: {} }`** | RedCap UEs (1Rx and 2Rx, FD-FDD and HD-FDD) allowed. At 20 MHz they use the initial BWP. |
| MCS tables | qam256 DL and UL | |

### Validation (2026-09-21, SM-S936U1 US/TMB, over the air)

| Check | Result |
|---|---|
| Attach / 5G registration + PDU session | ✅ 12 s |
| Under load: PUSCH SNR, UL MCS, UL retx | 13–20 dB, ~9.5, 7–13 % |
| Under load: CQI, RI, DL MCS, DL retx | 11–12, 2, ~19, 6–10 % |
| RTT avg / max (1200 B @100/s) | 54 / 138 ms, 0 % loss |
| iperf3 TCP 4 streams DL / UL | 59.8 / 11.2 Mbit/s (tuned.cfg without RedCap: 63.7 / 11.4, same within variance) |
| RedCap advertised | gNB `config_get`: `cell_barred_redcap_1rx: false`, `cell_barred_redcap_2rx: false` |
| RedCap UE attach | ⚠️ **not yet validated**: no RedCap UE available |

Enabling `redcap_ue` showed no regression for a regular (non-RedCap) UE.

### Deploy

```sh
scp gnb-sa-n71.cfg root@<callbox>:/root/enb/config/gnb-sa-n71-golden.cfg
ssh root@<callbox> 'ln -sfn gnb-sa-n71-golden.cfg /root/enb/config/enb.cfg && systemctl restart lte'
```

### Known limits and open items

- UL MCS stays well below what the measured SNR supports; suspected live T-Mobile n71 UL interference over the air ([#5](https://github.com/ekowtaylor/amarisoft/issues/5)). Re-validate cabled or in a shield box.
- n71 is licensed US carrier spectrum. Use a shielded or cabled setup.
- Validated with one UE model only. Re-validate with other UEs and with a RedCap device.
- Full investigation: [`investigations/2026-09-21-n71-sa/`](../../investigations/2026-09-21-n71-sa/)
