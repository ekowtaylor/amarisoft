# n71 5G SA investigation — Galaxy S25+ (SM-S936U1) on Amarisoft Callbox Mini (2026-09-21)

**Goal:** NR SA, band n71, 20 MHz FDD, 2x2 MIMO on the callbox, with a US Samsung phone attached.

**Result:** Working, but only when the SSB is kept out of **~625–635 MHz**. With the SSB there, the phone never
attempts access to the cell (no PRACH), although n71 is supported (UE capability) and allowed for SA (modem policy).
Working config: [`configs/gnb-sa-n71-working.cfg`](configs/gnb-sa-n71-working.cfg) (carrier 632–652 MHz, `gscn: 1602` → SSB 640.95 MHz).
**Recommended:** [`configs/gnb-sa-n71-tuned.cfg`](configs/gnb-sa-n71-tuned.cfg), the same config with closed-loop UL power control
(`dpc_snr_target` PUSCH 20 / PUCCH 15). It fixes UL SNR (≈0 → 11–17 dB) and DL HARQ/CQI loss. iperf3: DL 63.7 / UL 11.4 Mbit/s.
See [`perf/RESULTS.md`](perf/RESULTS.md).
Alternative: [`configs/gnb-sa-n71-ulmimo.cfg`](configs/gnb-sa-n71-ulmimo.cfg) (+SRS). UL MIMO does not engage because the UE is
limited to 1 UL layer, but UL throughput rises to ~18 Mbit/s at the cost of ~90 % UL HARQ retransmissions.

## Setup

| Item | Value |
|---|---|
| Callbox | Amarisoft Callbox Mini, 1× PCIe SDR (2 TX / 2 RX), lteenb/ltemme 2024-09-13 |
| Core | ltemme `mme-ims.cfg`, PLMN 001-01, test USIM IMSI 001010123456789 |
| UE | Samsung Galaxy S25+ SM-S936U1 (US unlocked), firmware S936U1OYM6BYIF, OMC/CSC **TMB**, rooted (Magisk) |
| UE modem | Snapdragon 8 Elite, `MPSS.DE.7.0-02170.5-PAKALA_GEN_PACK-1.85011.547` |
| Base config | Amarisoft `gnb-sa.cfg` template ([`configs/gnb-sa.cfg`](configs/gnb-sa.cfg)) |

## Test matrix (all NR SA unless noted)

| Config | Duplex / SCS | SSB | Result |
|---|---|---|---|
| [`gnb-sa-n71.cfg`](configs/gnb-sa-n71.cfg) n71 20 MHz 2x2 | FDD / 15 kHz | 633.75 MHz (auto) | ❌ no PRACH |
| [`gnb-sa-n71-1x1.cfg`](configs/gnb-sa-n71-1x1.cfg) n71 20 MHz 1x1 | FDD / 15 kHz | 633.75 MHz | ❌ |
| [`gnb-sa-n71-cs48.cfg`](configs/gnb-sa-n71-cs48.cfg) n71, CORESET0 48 RB | FDD / 15 kHz | 628.95 MHz | ❌ |
| [`gnb-sa-n7.cfg`](configs/gnb-sa-n7.cfg) n7 20 MHz 2x2 | FDD / 15 kHz | 2654.55 MHz | ❌ — **blocked by modem carrier policy** (see below) |
| [`gnb-sa-n66.cfg`](configs/gnb-sa-n66.cfg) n66 20 MHz 2x2 | FDD / 15 kHz | 2160.15 MHz | ✅ 10 s |
| [`gnb-sa-n77.cfg`](configs/gnb-sa-n77.cfg) n77 40 MHz 1x1 (stock template, band 78→77) | TDD / 30 kHz | 3479.52 MHz | ✅ 24 s |
| [`enb-b71.cfg`](configs/enb-b71.cfg) **LTE** B71 5 MHz @ 634.5 MHz | FDD | — | ✅ RSRP −62 dBm, SNR 29 dB |
| [`gnb-sa-n71-working.cfg`](configs/gnb-sa-n71-working.cfg) n71 20 MHz 2x2, `gscn: 1602` | FDD / 15 kHz | 640.95 MHz | ✅ 24 s, RI=2, data OK |
| [`gnb-sa-n71-tuned.cfg`](configs/gnb-sa-n71-tuned.cfg) as above + closed-loop UL PC | FDD / 15 kHz | 640.95 MHz | ✅ 15 s; UL SNR 11–17 dB, DL MCS ~20, retx ~10 % |

## n71 SSB sweep ([`sweep/sweep.csv`](sweep/sweep.csv), script [`sweep/ssb_sweep.sh`](sweep/ssb_sweep.sh))

Same 20 MHz 2x2 cell; only `gscn` changed (carrier fixed per row group). 50 s per position, airplane-mode toggle to trigger search.

| Carrier (DL / UL) | SSB attached ✅ | SSB never accessed ❌ |
|---|---|---|
| NR-ARFCN 125400: 617–637 / 663–683 MHz | 619.35, 620.55, 621.75, 622.95, 624.15 | 625.35, 626.55, 627.75, 628.95, 630.15, 631.35, 632.55 |
| NR-ARFCN 128400: 632–652 / 678–698 MHz | 640.95 | 634.95 |

- UL frequency and DL carrier are identical for passing and failing rows within a carrier → they are **not** the cause.
- The failing band is the same on both carriers → it depends on **absolute SSB frequency**, not SSB position within the carrier.
- Moving the SSB also moves CORESET#0/SIB1, so the dead zone is strictly the SSB+CORESET#0 region.
- Only GSCNs with M=3 start on these carriers (`gnb_start_fail` rows are raster/grid-misaligned, expected).
- Not swept (stopped early): 641–650 MHz beyond GSCN 1602.

## Ruled out

- **Band not supported:** UE-NR-Capability ([`logs/ue_capability_nr.txt`](logs/ue_capability_nr.txt)) lists n71 with 15 kHz 5/10/15/20 MHz, n7 up to 40 MHz.
- **SA disabled on UE:** LTE Attach shows `N1mode=1, DCNR=1` ([`logs/lte_attach_request_ue_network_capability.txt`](logs/lte_attach_request_ue_network_capability.txt)); n66/n77 SA register.
- **Band menu:** `*#2263#` NR5G band preference shows `71-NSA-SA-NRDC` enabled (read only, not changed).
- **Callbox RF at 600 MHz / interference:** LTE B71 at 634.5 MHz attaches with SNR 29 dB.
- **2x2 MIMO, CORESET#0 size (96 vs 48 RB), FDD/15 kHz in general:** n66 FDD 15 kHz 2x2 with 96-RB CORESET#0 works.

## Modem carrier policy (explains n7)

`NA/TMO/Commercial/mcfg_sw.mbn` → `/policyman/carrier_policy.xml` (excerpt):

```xml
<!-- SEC: Added 001 For the TEST -->
<mcc_list name="us_mccs"> 001 310 311 312 313 314 315 316 </mcc_list>
<rf_band_list name="rf_bands_home">
  <nr5g_sa_bands base="none"> <include> 24 40 65 70 76 </include> </nr5g_sa_bands>   <!-- 0-based: n25 n41 n66 n71 n77 -->
```

Samsung maps test MCC 001 into the US "home" list, restricting SA to n25/n41/n66/n71/n77. n7 SA is therefore never
searched. n71 **is** allowed, so this does not explain the n71 dead zone.

## Open question: why 625–635 MHz?

Unproven hypotheses:
1. **UE modem behaviour** — the phone's cell list recorded our cell at NR-ARFCN 126750 (PCI 500, band 71), i.e. it detected
   the SSB, but never sent PRACH. Could be an ARFCN-based restriction / treatment of that range as the live T-Mobile channel
   (a live T-Mobile n71 SSB is documented at 631.35 MHz / NR-ARFCN 126270).
2. **Local live n71 occupancy** in ~625–635 MHz degrading SSB/SIB1 decode. Counter-evidence: LTE B71 at 634.5 MHz had SNR 29 dB.

Next steps to close it: repeat the sweep cabled / in a shield box; check with a spectrum analyzer; decode NR ML1 logs
with QXDM/QualiPoc (SCAT did not decode NR RRC on this modem build); try a non-US UE.

## Other notes

- LTE attach initially failed with `ESM cause 0x1b (Missing or unknown APN)`: UE requested APN `anritsu` (IPv6).
  Fixed on the UE by adding APN `internet` (IPv4v6) ([`logs/lte_attach_reject_apn.txt`](logs/lte_attach_reject_apn.txt)).
- The callbox uses a floating license (server over the internet); the stack does not start without internet access.
- n71/n7 are licensed carrier spectrum in the US — use a shielded/cabled setup for OTA tests.
