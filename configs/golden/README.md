# Golden configs

Validated reference configs for the Amarisoft Callbox Mini (lteenb/ltemme 2024-09-13, 1× PCIe SDR 2T2R).

## [`gnb-sa-n71.cfg`](gnb-sa-n71.cfg): NR SA n71, 20 MHz FDD, 2x2, closed-loop UL PC, RedCap enabled

| Setting | Value | Why |
|---|---|---|
| Band / duplex / SCS | n71 FDD, 15 kHz | |
| Bandwidth / MIMO | 20 MHz, DL 2x2, UL 1 layer | UE reaches DL rank 2 |
| Carrier | `dl_nr_arfcn: 128400` (DL 632–652, UL 678–698 MHz) | |
| **SSB** | **`ssb_nr_arfcn: 128190` → 640.95 MHz** (== GSCN 1602) | **Required.** SSBs at ~625–635 MHz are never accessed by the SM-S936U1 ([#2](https://github.com/ekowtaylor/amarisoft/issues/2)). The automatic SSB lands at 633.75 MHz. **Spell it `ssb_nr_arfcn`, not `gscn`** — see the release note below. |
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
| RedCap UE attach | ✅ SIMCom SIM8230G, see below |

Enabling `redcap_ue` showed no regression for a regular (non-RedCap) UE.

### RedCap validation (2026-09-21, SIMCom SIM8230G, over the air)

UE: SIMCom **SIM8230G** 5G RedCap module (Qualcomm X35, firmware `2310B04X35M22A-M2`), connected to a Mac over USB. macOS has no
driver for its vendor-class ports, so AT commands went directly to USB interface 2 (`CDEV Serial`) with
[`simcom_at.py`](../../investigations/2026-09-21-n71-sa/redcap/simcom_at.py) (pyusb + libusb).

| Check | Result |
|---|---|
| UE declares RedCap | UE-NR-Capability: `redCapParameters-r17 { supportOfRedCap-r17 supported }`, `longSN-RedCap-r17`, `am-WithLongSN-RedCap-r17` |
| RedCap type | 2Rx (`maxNumberMIMO-LayersPDSCH twoLayers`), 1 UL layer, full-duplex FDD (no HD-FDD capability) |
| n71 support | 15 kHz, 5–20 MHz, PC3, 256QAM DL/UL |
| Attach | ✅ NR SA n71 in ~6 s. `+CPSI: NR5G_SA,Online,001-01,0x64,…,500,NR5G_BAND71,128190,-520,-110,40` (RSRP −52.0 dBm, RSRQ −11.0 dB, SINR 40 dB) |
| gNB → AMF | NGAP `id-RedCapIndication` = `redcap`; AMF `registered: true` |
| Data PDU session | APN `internet` (`AT+CGDCONT=1,"IPV4V6","internet"`, `AT+CGACT=1,1`) → 192.168.3.2; IMS → 192.168.4.2 |
| Ping to core GW 192.168.3.1 (`AT+CPING`) | 10/10, RTT 30 / 30 / 50 ms (min/avg/max) |
| Ping to 8.8.8.8 | 10/10, RTT 45 / 49 / 85 ms |
| gNB link stats during traffic | CQI 15, DL MCS 21–27, UL MCS 12–15, PUSCH SNR 14–19 dB, PHR 38 dB |
| Coexistence with the S25+ | ✅ both registered with PDU sessions at the same time (192.168.3.6 and 192.168.3.2) |

Notes:
- The module's default context had an empty APN, which gave an IMS-only session. It needs `internet` for data.
- Both test UEs share test IMSI 001010123456789. The `ue_db` entry has `multi_sim: true` (experimental). Separate IMSIs are safer.
  See [`docs/multi-sim-same-imsi.md`](../../docs/multi-sim-same-imsi.md).
- Not tested: RedCap throughput (iperf3 needs a host with a `qmi_wwan`/RmNet driver, e.g. Linux), HD-FDD RedCap UEs, 1Rx RedCap UEs.

### Release note: `gscn` vs `ssb_nr_arfcn`

This config was validated on **lteenb 2024-09-13**, where the SSB can be pinned with `gscn: 1602`.
**`gscn` does not exist on the 2025 releases.** It appears 0 times in the reference configs of both
2025-06-13 and 2025-09-19, against 3–11 occurrences of `ssb_nr_arfcn`. A config carrying `gscn`
therefore fails at config parse on those releases, and since the deploy below restarts the stack,
**the cell does not come back up**.

`ssb_nr_arfcn: 128190` == GSCN 1602 == 640.95 MHz, and is what this config now uses. Verified on
lteenb 2025-09-19 on four callboxes (2026-09-22). Not re-verified on 2024-09-13 — if you are still
on that release and it rejects `ssb_nr_arfcn`, `gscn: 1602` is the equivalent.

Stock configs of the 2025 releases also ship a commented hook, which is the least invasive way to
pin the SSB in an existing config without editing the cell block:

```c
//#define SSB_NR_ARFCN       0     ->    #define SSB_NR_ARFCN       128190
```

### Deploy

**Check the release first**, and keep a rollback. `lteenb -d` (dry-run config validator) **cannot be
used on a running box** — it needs a license seat and each box's seat is held by its own running
instance, so it fails on the license before it ever parses the config.

```sh
# 0. release check: expect ssb_nr_arfcn to be the supported spelling on 2025.x
ssh root@<callbox> 'grep -rc ssb_nr_arfcn /root/enb/config/*.cfg | grep -v :0 | head -1'

# 1. back up whatever is live now (follow the symlink -- on some boxes enb.cfg IS a symlink)
ssh root@<callbox> 'f=$(readlink -f /root/enb/config/enb.cfg); cp -a "$f" "$f.bak-$(date +%Y%m%d)"'

# 2. install and restart
scp gnb-sa-n71.cfg root@<callbox>:/root/enb/config/gnb-sa-n71-golden.cfg
ssh root@<callbox> 'ln -sfn gnb-sa-n71-golden.cfg /root/enb/config/enb.cfg && systemctl restart lte'

# 3. verify the cell actually came up with the intended carrier and SSB
ssh root@<callbox> 'grep -m1 "^# Cell 0x01" /tmp/gnb0.log'
#   expect: nr_arfcn=128400 ... ssb_arfcn=128190
```

If step 3 prints nothing, the ENB did not start — restore the backup from step 1 and restart.

### Known limits and open items

- UL MCS stays well below what the measured SNR supports; suspected live T-Mobile n71 UL interference over the air ([#5](https://github.com/ekowtaylor/amarisoft/issues/5)). Re-validate cabled or in a shield box.
- n71 is licensed US carrier spectrum. Use a shielded or cabled setup.
- The callbox needs internet for its floating license (the stack won't start without it) and for UE data. See
  [`docs/host-network-setup.md`](../../docs/host-network-setup.md) for sharing the Mac's internet.
- Validated with the SM-S936U1 (eMBB) and the SIM8230G (RedCap, 2Rx FD-FDD). Re-validate with other UEs.
- Full investigation: [`investigations/2026-09-21-n71-sa/`](../../investigations/2026-09-21-n71-sa/)
