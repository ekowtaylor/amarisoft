# amarisoft

Python client for the [Amarisoft Callbox Remote API](https://tech-academy.amarisoft.com/RemoteAPI.html).

Communicates with eNB/gNB, MME/AMF, IMS, and UE Simulator services over WebSocket using JSON messages.

## Installation

### REST API Service (One-Line Install)

Deploy the HTTP REST API service directly on your Amarisoft Callbox:

```bash
curl -sSL https://raw.githubusercontent.com/ekowtaylor/amarisoft/main/install.sh | sudo bash
```

This works on both **RPM-based** (RHEL, CentOS, Fedora) and **Debian-based** (Ubuntu, Debian) Linux distributions.

**With custom options:**
```bash
# Custom port
curl -sSL https://raw.githubusercontent.com/ekowtaylor/amarisoft/main/install.sh | sudo bash -s -- --port 8080

# Uninstall
curl -sSL https://raw.githubusercontent.com/ekowtaylor/amarisoft/main/install.sh | sudo bash -s -- --uninstall
```

**Available options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--port PORT` | 9010 | Service port |
| `--host HOST` | 0.0.0.0 | Bind address |
| `--callbox-host HOST` | 127.0.0.1 | Callbox WebSocket host |
| `--install-dir DIR` | /opt/amarisoft-rest-api | Installation directory |
| `--branch BRANCH` | main | Git branch to install |
| `--uninstall` | - | Remove service and files |

**After installation:**
```bash
# Check status
systemctl status amarisoft-rest-api

# View logs
journalctl -u amarisoft-rest-api -f

# Test endpoints
curl http://localhost:9010/health
curl http://localhost:9010/docs  # Swagger UI
```

### Python Client Library

```bash
pip install websocket-client
```

Then add the `amarisoft` package to your project (or install it in editable mode):

```bash
pip install -e .
```

## Quick Start

```python
from amarisoft import Callbox

# Connect to all four services on the Callbox
with Callbox("192.168.1.100") as cb:
    # eNB: get stats and connected UEs
    stats = cb.enb.stats()
    ues = cb.enb.ue_get()

    # Adjust cell gain
    cb.enb.cell_gain(cell_id=1, gain=-10)

    # MME: detach a UE
    cb.mme.ue_detach(imsi="001010123456789")

    # IMS: send an SMS
    cb.ims.send_sms(impu="sip:user@ims.local", text="Hello")

    # UE Sim: power-cycle a simulated UE
    cb.ue.power_off(ue_id=1)
    cb.ue.power_on(ue_id=1)
```

## Connecting to Individual Services

If you only need one service, connect to it directly:

```python
from amarisoft import Callbox

cb = Callbox("192.168.1.100")
cb.connect_enb()

cb.enb.stats()
cb.enb.cell_gain(cell_id=1, gain=-20)

cb.close()
```

Or use a `WebSocketClient` on its own:

```python
from amarisoft import WebSocketClient, ENBApi

client = WebSocketClient("192.168.1.100", port=9001)
client.connect()

enb = ENBApi(client)
enb.config_get()

client.close()
```

## Default Ports

| Service   | Port | Class    |
|-----------|------|----------|
| MME / AMF | 9000 | `MMEApi` |
| eNB / gNB | 9001 | `ENBApi` |
| IMS       | 9002 | `IMSApi` |
| UE Sim    | 9003 | `UEApi`  |

Ports are configurable via `Callbox(host, enb_port=..., mme_port=..., ...)`.

## Authentication & TLS

If `com_auth` is enabled on the Callbox, pass the password:

```python
cb = Callbox("192.168.1.100", password="secret")
```

For TLS (`wss://`), including self-signed certificates:

```python
import ssl

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.load_verify_locations("/path/to/ca.pem")
# Or to skip verification (development only):
# ctx.check_hostname = False
# ctx.verify_mode = ssl.CERT_NONE

cb = Callbox("192.168.1.100", ssl=True, ssl_context=ctx)
```

## Auto-Reconnect

Enable automatic reconnection when a send fails due to a dropped connection:

```python
cb = Callbox("192.168.1.100", auto_reconnect=True)
```

## API Reference

### Shared Methods (all services)

Every service API (`ENBApi`, `MMEApi`, `IMSApi`, `UEApi`) inherits these methods:

| Method | Description |
|--------|-------------|
| `config_get()` | Retrieve current configuration |
| `config_set(**params)` | Set configuration parameters |
| `stats(**params)` | Retrieve service statistics |
| `ue_get(**filters)` | Query connected/simulated UEs |
| `log_get(min_, max_, timeout, layer)` | Retrieve log entries from memory |
| `log_set(layers, **params)` | Set logging configuration |
| `version()` | Get software version |
| `help()` | List available API messages and events |

### ENBApi (eNB/gNB) — port 9001

| Method | Description |
|--------|-------------|
| `system_info()` | Overall eNB/gNB system status |
| `config_set_cell(cell_id, **params)` | Per-cell configuration |
| `cell_gain(cell_id, gain)` | Adjust cell gain (dB) |
| `cell_list()` | List configured cells |
| `rf(tx_gain, rx_gain, rx_agc)` | RF parameter control |
| `set_dl_config(cell_id, ...)` | DL PHY/MAC parameters (MCS, RB alloc) |
| `set_ul_config(cell_id, ...)` | UL PHY/MAC parameters (MCS, RB alloc) |
| `erab_get(**filters)` | Query E-RABs |
| `qos_flow_get(**filters)` | Query QoS flows (5G NR) |
| `rrc_cnx_release(enb_ue_id)` | Release RRC connection |
| `rrc_cnx_reconf(enb_ue_id, **params)` | RRC reconfiguration |
| `rrc_ue_info_req(enb_ue_id, req_mask)` | Request UE info |
| `rrc_ue_cap_enquiry(enb_ue_id)` | Query UE capabilities |
| `rrc_procedure_filter(**params)` | RRC procedure rejection filters |
| `page_ue(cell_ids, imsi, ...)` | UE paging |
| `sib_set(cell_id, sib_data)` | Configure SIB parameters |
| `dci_bwp_switch(enb_ue_id, ...)` | BWP switching via DCI (5G NR) |
| `s1_connect()` / `s1_disconnect()` | S1 interface control |
| `ng_connect()` / `ng_disconnect()` | NG interface control (5G) |
| `s1_status()` / `ng_status()` / `x2_status()` | Interface status queries |
| `trx_iq_dump(duration, ...)` | Capture IQ samples |
| `register_channel(channel)` | Subscribe to constellation data |
| `unregister_channel(channel)` | Unsubscribe from constellation data |
| `pdcch_order_prach(enb_ue_id)` | PDCCH order for PRACH |
| `ue_activate_dedicated_bearer(enb_ue_id, qci, ...)` | Activate dedicated bearer |

### MMEApi (MME/AMF) — port 9000

| Method | Description |
|--------|-------------|
| `enb_get(**filters)` | Query connected eNodeBs |
| `gnb_get(**filters)` | Query connected gNodeBs |
| `session_get(**filters)` | Query PDN/PDU sessions |
| `bearer_get(**filters)` | Query EPS bearers / QoS flows |
| `ue_detach(imsi, imei)` | Detach UE from network |
| `ue_deactivate_bearer(erab_id, ...)` | Deactivate a bearer |
| `ue_modify_bearer(imsi, erab_id, qci, ...)` | Modify bearer QoS |
| `mt_cs_paging(imsi)` | Circuit-switched paging |
| `attach_reject_filter(imsi, emm_cause)` | Set attach reject filter |
| `attach_reject_filter_clear()` | Clear all reject filters |
| `registration_reject_filter(imsi, cause)` | 5G registration reject filter |
| `set_t3512(value)` | Set T3512 timer |
| `pdn_list(apn, **params)` | Configure PDN settings |

### IMSApi — port 9002

| Method | Description |
|--------|-------------|
| `users_get(registered_only)` | Query IMS users |
| `users_add(**params)` | Add users to IMS database |
| `user_set(**params)` | Configure existing user |
| `unregister(impu)` | Force user deregistration |
| `impu_set(impu, **params)` | Configure an IMPU |
| `impu_add(impu, **params)` | Add IMPU to user |
| `impu_del(impu)` | Remove IMPU from user |
| `mt_cs_paging(imsi)` | Circuit-switched paging |
| `mt_call(impu, **params)` | Initiate mobile-terminated call |
| `dialog_get(session_id)` | List pending dialogs |
| `dialog_set(session_id, action, ...)` | Control dialog (stop/answer/hold/...) |
| `send_sms(impu, text, binary_hex)` | Send SMS |
| `sms_flush()` | Flush pending SMS |
| `send_mms(impu, filename, ...)` | Send MMS |
| `mms_server()` | Get MMS server address |
| `license()` | Retrieve license info |
| `ipsec()` | IPsec security association details |
| `register_events(*event_types)` | Subscribe to events (sms, dialog, ...) |

### UEApi (UE Simulator) — port 9003

| Method | Description |
|--------|-------------|
| `power_on(ue_id)` | Power on simulated UE |
| `power_off(ue_id)` | Power off simulated UE |
| `ue_activate_dedicated_bearer(ue_id, ...)` | Activate dedicated bearer |
| `ue_assistance_information(ue_id, ...)` | Send UE Assistance Info (5G NR) |

### Raw Messages

For commands not yet wrapped, use `send_raw`:

```python
cb.send_raw("enb", {"message": "some_new_command", "param": "value"})
```

### Batch Messages

Send multiple commands in a single WebSocket frame:

```python
responses = cb._enb_client.send_batch([
    {"message": "config_get"},
    {"message": "stats"},
])
```

### Event Listening

Listen for unsolicited messages (logs, constellation data, etc.):

```python
cb.connect_enb()
cb.enb.register_channel("pusch")

def on_data(msg):
    print(msg)
    return True  # return False to stop

cb._enb_client.listen(on_data, duration=10.0)
```

## Error Handling

```python
from amarisoft import (
    AmariError,
    AmariConnectionError,
    AmariTimeoutError,
    AuthenticationError,
    CommandError,
)

try:
    cb.enb.cell_gain(cell_id=99, gain=-10)
except CommandError as e:
    print(f"Command failed: {e} (code: {e.error_code})")
except AmariConnectionError:
    print("Connection lost")
except AmariTimeoutError:
    print("Request timed out")
```

## Architecture

```
amarisoft/
├── __init__.py      # Package exports
├── base.py          # ServiceApi base class (shared methods)
├── callbox.py       # Callbox orchestrator (4 services)
├── client.py        # WebSocketClient (transport layer)
├── enb.py           # ENBApi — eNB/gNB commands
├── mme.py           # MMEApi — MME/AMF commands
├── ims.py           # IMSApi — IMS commands
├── ue.py            # UEApi — UE Simulator commands
└── exceptions.py    # Exception hierarchy
```

## Requirements

- Python 3.10+
- `websocket-client >= 1.5.0`

## License

See [LICENSE](LICENSE) for details.
