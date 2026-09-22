# Several UEs with the same IMSI (Amarisoft ltemme 2024-09-13)

Source: `ltemme-linux-2024-09-13/doc/ltemme.html` on the callbox.

## `multi_sim`: the only feature for this

Per `ue_db` entry:

> **multi_sim**: Optional boolean (default = false). If true, allow several UEs to have the same IMSI (useful when using
> several identical test SIM cards in different UEs at the same time). They are distinguished with their IMEI.
> Note: it is only allowed with the XOR authentication algorithm.

Requirements:

| Requirement | Our setup |
|---|---|
| `sim_algo` must be `xor` | Test SIM entry has no `sim_algo`, so it uses the default `xor` ✅ |
| `imeisv_request_in_smc` must be true (the AMF/MME asks for the IMEISV in the NAS Security Mode Command) | Default `true`, not overridden in `mme-ims.cfg` ✅ |

Our `ue_db-ims.cfg` entry for `001010123456789` has `multi_sim: true, /* Experimental */`.

### Observed (2026-09-21)

The SM-S936U1 (eMBB) and the SIMCom SIM8230G (RedCap) both use test IMSI `001010123456789`, and both were registered on
5GC at the same time:

| UE | IMEISV (last 8) | Data PDU session |
|---|---|---|
| SM-S936U1 | …10021906 | 192.168.3.6 |
| SIM8230G | …00346900 | 192.168.3.2 (+ IMS 192.168.4.2) |

### Limitations

- The documentation marks it **experimental**.
- All UEs share **one subscription**: the same APN/DNN rules, AMBR, and IMS identity (`impi`/`impu`, `tel:0600000000`).
  UE-to-UE calls and SMS between them won't work properly.
- No per-UE settings in 5G (see `imei` below).

## Related parameters (none of them separate subscribers)

| Parameter | What it does | Limitation |
|---|---|---|
| `pdn_list[].imei` | PDN settings (e.g. a static IP) that only apply to the UE with that IMEI | **EPS only, not 5GS** |
| `me_db` | Whitelist, blacklist or greylist devices by IMEI/IMEISV | Access control only |
| `ue_get` API `imei` filter | Query one UE among several sharing an IMSI | Monitoring only |
| `ue_db[].count` | Create *n* entries by incrementing the IMSI and K | Needs SIMs that really have different IMSIs |

## Recommendation

For anything longer than a quick test, give each UE its **own IMSI**. `ue_db-ims.cfg` already has entries for
`001010000000001` … `001010000000008` (the Amarisoft multi-SIM test pack range). Use one of those SIMs in the second UE.
Check a SIM's IMSI with `AT+CIMI` (module) or from the phone, and confirm it matches an existing `ue_db` entry.
