# Amarisoft Callbox Setup Notes

**Date**: 2026-02-17 (Updated)
**Author**: Ekow Taylor (ekowtaylor@meta.com)
**Callbox IP**: 192.168.1.80
**SSH Credentials**: root / toor

---

## Current Status ✅ WORKING

| Component | Port | Status | Notes |
|-----------|------|--------|-------|
| Network Connectivity | - | ✅ Working | Ping successful, ~1ms latency |
| SSH Access | 22 | ✅ Working | root/toor credentials confirmed |
| HTTP Web Interface | 80 | ✅ Open | Port 80 accessible |
| WebSocket Remote API | - | ✅ **WORKING** | All services running via license server |
| eNB/gNB | 9001 | ✅ **Running** | Connected and responding |
| MME/AMF | 9000 | ✅ **Running** | Connected and responding |
| IMS | 9003 | ✅ **Running** | Note: Port 9003, not 9002 |
| MBMS GW | 9004 | ✅ **Running** | Connected |
| UE Sim | - | ❌ Not running | Not configured |

---

## Working License Configuration ✅

The Callbox is now using an **internet-based license server** for license validation.

### License Server Configuration

**File**: `/root/.amarisoft/license_server.cfg`

```json
{
  "license_server": {
    "server_addr": "35.155.227.91",
    "tag": "NISCBM02_FRE6530"
  }
}
```

| Setting | Value |
|---------|-------|
| Server Address | `35.155.227.91` |
| Tag | `NISCBM02_FRE6530` |

This configuration allows the Callbox to obtain valid licenses from the remote license server over the internet.

### Verified Service Status (2026-02-17)

```bash
root@CBM-2024121101:~# ss -tlnp | grep 900
LISTEN 0  5  *:9000  *:*  users:(("ltemme",pid=1459,fd=6))
LISTEN 0  5  *:9001  *:*  users:(("lteenb-avx2",pid=1717,fd=7))
LISTEN 0  5  *:9003  *:*  users:(("lteims",pid=1785,fd=6))
LISTEN 0  5  *:9004  *:*  users:(("ltembmsgw",pid=1547,fd=8))
```

### Log Confirmation

```
2026-02-17 16:51:31 [OTS] - MBMSGW: Event 'started':
2026-02-17 16:51:32 [OTS] - ENB: Event 'started':
2026-02-17 16:51:32 [OTS] - IMS: Event 'started':
```

---

## API Connectivity Confirmed ✅

### Python Library Test Results

```python
from amarisoft import Callbox

# Note: IMS is on port 9003, not default 9002
cb = Callbox('192.168.1.80', timeout=5.0, ims_port=9003)
cb.connect_enb()   # ✅ Connected
cb.connect_mme()   # ✅ Connected
cb.connect_ims()   # ✅ Connected

# Connection status
{'enb': True, 'mme': True, 'ims': True, 'ue': False}

# eNB stats - 1 cell configured
# MME ue_get - 0 UEs connected
```

### Quick Connection Test

```bash
cd /Users/ekowtaylor/Documents/Personal/Github/amarisoft
python3 -c "
from amarisoft import Callbox

cb = Callbox('192.168.1.80', timeout=5.0, ims_port=9003)
try:
    cb.connect_enb()
    cb.connect_mme()
    cb.connect_ims()
    print('Status:', cb.status)
    print('eNB stats:', cb.enb.stats())
    print('MME UEs:', cb.mme.ue_get())
finally:
    cb.close()
"
```

### Important: IMS Port Configuration

The IMS service runs on **port 9003** (not the default 9002). When using the Python library:

```python
# Correct - specify IMS port
cb = Callbox('192.168.1.80', ims_port=9003)

# Or connect individually
cb = Callbox('192.168.1.80')
cb.connect_enb()  # Port 9001
cb.connect_mme()  # Port 9000
cb._ims_client = WebSocketClient('192.168.1.80', port=9003)
cb._ims_client.connect()
```

---

## System Information

- **Hostname**: CBM-2024121101
- **OS**: Fedora Linux 39, Kernel 6.11.9-100.fc39.x86_64
- **Amarisoft Version**: 2024-09-13
- **SDR Hardware**: SDR50 (Serial: 202405001019)

### User Accounts

| User | Password | Notes |
|------|----------|-------|
| root | toor | Admin account, Amarisoft software runs here |
| user | resu | Standard user account |

### Directory Structure

```
/root/
├── enb -> /root/lteenb-linux-2024-09-13      # eNB/gNB software
├── mme -> /root/ltemme-linux-2024-09-13      # MME/AMF + IMS software
├── mbms -> /root/ltembmsgw-linux-2024-09-13  # MBMS gateway
├── ots -> /root/lteots-linux-2024-09-13      # Orchestration/startup scripts
├── trx_sdr -> /root/trx_sdr-linux-2024-09-13 # SDR driver
├── .amarisoft/                                # License configuration
│   └── license_server.cfg                     # Points to 35.155.227.91
├── floating/                                  # Floating licenses (dongle-based)
├── lteenb.key                                 # Local eNB license (expired)
└── ltemme.key                                 # Local MME license (expired)
```

---

## License Information

### Active License Method: Remote License Server ✅

The Callbox obtains licenses from the remote server at `35.155.227.91` with tag `NISCBM02_FRE6530`.

### Backup: Local License Files (Expired)

| File | Location | User | Valid Until | Status |
|------|----------|------|-------------|--------|
| ltemme.key | /root/.amarisoft/ | Facebook | 2025-02-15 | ❌ EXPIRED |
| lteenb.key | /root/.amarisoft/ | Facebook | 2025-02-15 | ❌ EXPIRED |

### Backup: Floating Licenses (Expired + No Dongle)

| File | Location | User | Valid Until | Dongle ID | Status |
|------|----------|------|-------------|-----------|--------|
| lteenb.key | /root/floating/ | Meta Platforms | 2024-11-09 | f4-4b-e1-4d-50-b5-88-0c | ❌ EXPIRED |
| ltemme.key | /root/floating/ | Meta Platforms | 2024-11-09 | f4-4b-e1-4d-50-b5-88-0c | ❌ EXPIRED |

### System IDs (For License Renewal Requests)

- **Host ID**: `6e-61-c9-29-20-7f-7c-c4`
- **Local ID**: `e9-ee-1c-3c-f5-01-05-fd`
- **Dongle ID** (floating): `f4-4b-e1-4d-50-b5-88-0c`
- **Contact**: https://support.amarisoft.com or delivery@amarisoft.com

---

## Configuration Files

### Remote API Ports

| Service | Config File | com_addr Setting | Actual Port |
|---------|-------------|------------------|-------------|
| eNB/gNB | /root/enb/config/enb.cfg | `com_addr: "[::]:9001"` | 9001 |
| MME/AMF | /root/mme/config/mme.cfg | `com_addr: "[::]:9000"` | 9000 |
| IMS | /root/mme/config/ims.cfg | `com_addr: "[::]:9003"` | 9003 |
| MBMS GW | /root/mbms/config/mbmsgw.cfg | - | 9004 |

### OTS Configuration

**File**: `/root/ots/config/ots.cfg`

```bash
# Components configured
COMPONENTS=" MME IMS ENB MBMSGW"

# MME
MME_TYPE="MME"
MME_WIN="0"
MME_PATH="/root/mme"
MME_CONFIG_FILE="config/mme.cfg"

# IMS
IMS_TYPE="IMS"
IMS_WIN="3"
IMS_PATH="/root/mme"
IMS_CONFIG_FILE="config/ims.cfg"

# eNB
ENB_TYPE="ENB"
ENB_WIN="1"
ENB_PATH="/root/enb"
ENB_CONFIG_FILE="config/enb.cfg"

# MBMS GW
MBMSGW_TYPE="MBMSGW"
MBMSGW_WIN="4"
MBMSGW_PATH="/root/mbms"
MBMSGW_CONFIG_FILE="config/mbmsgw.cfg"
```

---

## Service Management

### Start/Stop/Restart Services

```bash
ssh root@192.168.1.80
# Password: toor

# Restart all services
systemctl restart lte.service

# Stop all services
systemctl stop lte.service

# Start all services
systemctl start lte.service

# Check status
systemctl status lte.service
```

### Verify Services Are Running

```bash
# Check processes
ps aux | grep -E "ltemme|lteenb|lteims|ltembms" | grep -v grep

# Check listening ports
ss -tlnp | grep 900

# Expected output:
# LISTEN *:9000 ltemme
# LISTEN *:9001 lteenb-avx2
# LISTEN *:9003 lteims
# LISTEN *:9004 ltembmsgw
```

### View Logs

```bash
# Real-time service log
tail -f /var/log/lte/ots.log

# Alternative log location
tail -f /tmp/lte.log

# Component-specific logs
cat /tmp/enb0.log      # eNB log
cat /tmp/gnb0.log      # gNB log (5G NR)
cat /tmp/mme0.log      # MME log
cat /tmp/ims.log       # IMS log
```

### Enable Debug Logging

To enable PHY layer debug traces (recommended for troubleshooting):

Edit `/root/enb/config/enb.cfg` and add:
```javascript
log_options: "phy.level=debug",
```

Then restart:
```bash
service lte restart
```

---

## License Status Commands

### Check License Configuration

```bash
# View current license server config
cat /root/.amarisoft/license_server.cfg

# View local license file details
strings /root/.amarisoft/lteenb.key | grep -E "version|product|user|license"
strings /root/.amarisoft/ltemme.key | grep -E "version|product|user|license"

# View floating license details
strings /root/floating/lteenb.key | grep -E "version|product|user|dongle"
strings /root/floating/ltemme.key | grep -E "version|product|user|dongle"
```

### Check License Errors in Logs

```bash
# Search for license-related messages
cat /var/log/lte/ots.log | grep -i license | tail -30

# Get system IDs from error messages
cat /var/log/lte/ots.log | grep -A5 "License error" | grep -E "Host ID|Local ID"
```

### Check USB Dongle (For Floating Licenses)

```bash
lsusb
dmesg | grep -i dongle
```

---

## Troubleshooting

### If Services Won't Start

1. **Check license server connectivity**:
   ```bash
   ping 35.155.227.91
   nc -zv 35.155.227.91 443
   ```

2. **Verify license_server.cfg exists and is correct**:
   ```bash
   cat /root/.amarisoft/license_server.cfg
   ```

3. **Check logs for errors**:
   ```bash
   tail -50 /var/log/lte/ots.log | grep -i error
   ```

4. **Restart the service**:
   ```bash
   systemctl restart lte.service
   sleep 15
   ss -tlnp | grep 900
   ```

### Common License Errors

| Error Code | Meaning | Solution |
|------------|---------|----------|
| 0xb | License validation failed | Check license server connectivity or renew local licenses |
| 66 | License error | License expired or invalid |

### If License Server is Unreachable

Fall back to local license files (requires valid/renewed licenses):

```bash
# Remove license server config
rm /root/.amarisoft/license_server.cfg

# Copy valid license files
cp /path/to/new/ltemme.key /root/.amarisoft/
cp /path/to/new/lteenb.key /root/.amarisoft/

# Restart
systemctl restart lte.service
```

---

## Python Library Usage

### Installation

```bash
pip install websocket-client

cd /Users/ekowtaylor/Documents/Personal/Github/amarisoft
pip install -e .
```

### Basic Usage

```python
from amarisoft import Callbox

# Connect with correct IMS port
cb = Callbox('192.168.1.80', ims_port=9003, timeout=5.0)

try:
    cb.connect_all()

    # eNB operations
    stats = cb.enb.stats()
    ues = cb.enb.ue_get()
    cb.enb.cell_gain(cell_id=1, gain=-10)

    # MME operations
    cb.mme.ue_get()
    cb.mme.ue_detach(imsi="001010123456789")

    # IMS operations
    cb.ims.send_sms(impu="sip:user@ims.local", text="Hello")

finally:
    cb.close()
```

### Run Example Scripts

```bash
cd /Users/ekowtaylor/Documents/Personal/Github/amarisoft

# Basic connection test
python3 examples/basic_connection.py --host 192.168.1.80

# Other examples
python3 examples/ue_management.py --host 192.168.1.80
python3 examples/enb_cell_management.py --host 192.168.1.80
```

---

## Quick Reference

| Item | Value |
|------|-------|
| Callbox IP | 192.168.1.80 |
| SSH | root / toor |
| eNB Port | 9001 |
| MME Port | 9000 |
| IMS Port | **9003** (not 9002) |
| MBMS GW Port | 9004 |
| License Server | 35.155.227.91 |
| License Tag | NISCBM02_FRE6530 |
| Host ID | 6e-61-c9-29-20-7f-7c-c4 |
| SDR Serial | 202405001019 |

---

---

## Interactive Monitor (Screen)

Access the component monitors using `screen`:

```bash
ssh root@192.168.1.80
screen -x lte
```

### Screen Window Navigation

| Window | Component | Navigate |
|--------|-----------|----------|
| 0 | MME | `Ctrl+a 0` |
| 1 | eNB | `Ctrl+a 1` |
| 2 | MBMSGW | `Ctrl+a 2` |
| 3 | IMS | `Ctrl+a 3` |

**Commands:**
- `Ctrl+a <space>` - Next window
- `Ctrl+a d` - Detach from screen (exit without closing)
- `help` - List available commands in current component

### Useful Monitor Commands (eNB)

```bash
# UE throughput stats (DL/UL bitrate, MCS, CQI, SNR)
t

# Signal power levels (TX/RX RMS, saturation check)
t spl

# CPU load monitoring
t cpu

# List all commands
help
```

### Understanding `t` Command Output

**Downlink columns:**
- `cqi` - Channel Quality Indicator (0-15, higher=better)
- `ri` - Rank Indicator (MIMO layers)
- `mcs` - Modulation Coding Scheme
- `retx` - Retransmissions (lower=better)
- `brate` - Bitrate in bps

**Uplink columns:**
- `snr` - Signal to Noise Ratio (dB)
- `phr` - Power Headroom (dB, negative=UE power limited)
- `pl` - Path Loss (dB)

### Understanding `t spl` Command Output

```
--P0/TX 1-- --P1/TX 2-- dBFS --P0/RX 1-- --P1/RX 2--
  RMS   MAX   RMS   MAX  SAT   RMS   MAX   RMS   MAX
-24.6  -7.7 -24.6  -8.3    0 -42.7 -30.4 -42.7 -30.4
```

- **TX SAT = 0** is good (no saturation)
- **RX MAX = 0** means saturation - reduce `rx_gain`
- Adjust `tx_gain` / `rx_gain` in RF config if needed

---

## TX/RX Gain Settings

**File**: `/root/enb/config/rf_driver/config.cfg`

### Wired Test (RF Cables)
```javascript
tx_gain: 60.0,  /* TX gain (in dB) */
rx_gain: 0.0,   /* RX gain (in dB) */
```

### Wireless Test (Antennas)
```javascript
tx_gain: 90.0,  /* TX gain (in dB) */
rx_gain: 60.0,  /* RX gain (in dB) */
```

**Note:** Max SDR input is -10 dBm, max output is 5 dBm.

---

## Test SIM Card (Included with Callbox)

| Parameter | Value |
|-----------|-------|
| IMSI | `001010123456789` |
| K | `00112233445566778899aabbccddeeff` |
| Algorithm | XOR |

This SIM is pre-provisioned in the EPC/5GC database - no configuration needed.

### Adding Custom SIM Cards

Edit `/root/mme/config/ue_db-ims.cfg`:

```javascript
{
    sim_algo: "milenage",
    imsi: "001010000000001",
    opc: "000102030405060708090A0B0C0D0E0F",
    amf: 0x9001,
    sqn: "000000000000",
    K: "00112233445566778899AABBCCDDEEFF",
},
```

### Commercial SIM Card Workarounds

If you don't have the secret key (K/OPC) for a commercial SIM:

**Method 1**: Skip authentication (requires UE support for EIA0):
```javascript
// In mme.cfg:
authentication_mode: "skip",
```

**Method 2**: Skip both authentication and security mode:
```javascript
// In mme.cfg:
authentication_mode: "skip",
skip_smc_proc: true,

// In enb.cfg (eNB object, not cell object):
skip_smc_proc: true,
```

**Note**: These workarounds don't comply with 3GPP specs and require UE-side support.

---

## APN Configuration

### Pre-configured APNs

| APN Name | Purpose |
|----------|---------|
| default | Generic default APN |
| internet | Data/internet traffic |
| ims | VoLTE/IMS services |
| sos | Emergency services |

### UE APN Settings (Example: Samsung)

1. Settings → More networks → Mobile networks
2. Enable "Data roaming"
3. Add APN:
   - Name: `Internet`
   - APN: `internet`
   - APN type: `internet,default`

---

## eNB/gNB Configuration

### Configuration File

**File**: `/root/enb/config/enb.cfg` (symlink to actual config)

### Common Configuration Defines

```c
#define TDD                 0   // 0=FDD, 1=TDD
#define NR_TDD              1   // 0=NR FDD, 1=NR TDD
#define N_RB_DL             100 // 6=1.4MHz, 25=5MHz, 50=10MHz, 75=15MHz, 100=20MHz
#define N_ANTENNA_DL        2   // 1=SISO, 2=MIMO 2x2, 4=MIMO 4x4
#define NR_BANDWIDTH        40  // NR cell bandwidth in MHz
```

### Switching Configurations

```bash
cd /root/enb/config

# List available configs
ls *.cfg

# Switch to NSA mode
ln -sfn gnb-nsa.cfg enb.cfg

# Switch to 2CC carrier aggregation
ln -sfn enb-2cc.cfg enb.cfg

# Restart to apply
service lte restart
```

### SDR Card Mapping

| Config | rf_port | SDR Device |
|--------|---------|------------|
| 1 cell 2x2 MIMO | 0 | SDR0 |
| 2 cells 2x2 MIMO | 0, 1 | SDR0, SDR1 |
| 1 cell 4x4 MIMO | 0 | SDR0 + SDR1 |
| NSA (LTE + NR) | 0, 1 | SDR0 (LTE), SDR1 (NR) |

---

## Web GUI

Access the web interface at:
```
http://192.168.1.80/
```

Features:
- Real-time log viewing
- System status monitoring
- Cell information display

### Setting Web GUI Password

```bash
# Edit Apache config
vi /etc/httpd/conf/httpd.conf
# Add AuthConfig to AllowOverride in <Directory "/var/www/html"> section

# Restart Apache
service httpd restart

# Create .htaccess
cat > /var/www/html/lte/.htaccess << 'EOF'
AuthType Basic
AuthName "Amarisoft Web GUI"
AuthUserFile /etc/httpd/.htpasswd
Require valid-user
EOF

# Add user
htpasswd -c /etc/httpd/.htpasswd admin
```

---

## Software Upgrade

### Install New Release

```bash
# Download from extranet.amarisoft.com
# Transfer to Callbox

# Extract
tar xzf amarisoft.YYYY-MM-DD.tar.gz
cd YYYY-MM-DD

# Install with defaults
./install.sh /root --default

# Restart
service lte restart
```

### Rollback Release

Components are symlinks to versioned directories:
```bash
ls -la /root/enb
# enb -> /root/lteenb-linux-2024-09-13

# To rollback, update symlink to previous version
ln -sfn /root/lteenb-linux-YYYY-MM-DD /root/enb
service lte restart
```

---

## Hardware Information

### SDR Card Specs (SDR50/SDR100)

- **Ports per card**: 4 TX + 4 RX SMA connectors
- **Each physical card**: 2 logical SDR devices
- **Bandwidth**: Up to 100 MHz per logical device
- **MIMO**: Up to 4x4 per physical card

### RF Connection Guidelines

- **FDD 2x2 MIMO**: Connect TX1, TX2, RX1, RX2
- **TDD 2x2 MIMO**: Only TX1, TX2 needed (or use `rx_antenna: "rx"` for separate RX)
- **Unused combiner ports**: Terminate with RF terminator (especially >2.5 GHz)

---

## Documentation References

### Local Documentation (on Callbox)

```bash
# PDF documents
ls /root/ots/doc/*.pdf
ls /root/enb/doc/*.pdf
ls /root/mme/doc/*.pdf

# HTML API docs
ls /root/enb/doc/*.html
ls /root/mme/doc/*.html
```

### Key Documents

| Document | Description |
|----------|-------------|
| lteenb.pdf | eNB/gNB configuration reference |
| ltemme.pdf | MME/AMF/5GC configuration reference |
| lteims.pdf | IMS server configuration |
| appnote_ims.pdf | VoLTE/IMS testing guide |
| appnote_throughput.pdf | Throughput testing guide |

### Online Resources

- **Extranet**: https://extranet.amarisoft.com/
- **Wiki**: https://extranet.amarisoft.com/wiki
- **Support**: https://support.amarisoft.com
- **Tech Academy**: https://tech-academy.amarisoft.com/

---

## Revision History

| Date | Changes |
|------|---------|
| 2026-02-13 | Initial troubleshooting - discovered expired licenses |
| 2026-02-17 | License server configured at 35.155.227.91 - all services now working |
| 2026-02-17 | Added comprehensive reference from Amarisoft User Guide (screen commands, TX/RX gain, SIM config, APN, SDR mapping, etc.)
| 2026-02-17 | Added Python capabilities/constraints system for parameter validation |

---

## Python Capabilities & Constraints System

The Python library includes a comprehensive capabilities and constraints system that:
- Discovers device capabilities from the connected Callbox
- Validates parameters before sending commands
- Prevents operations that would fail due to hardware/license limits

### Capability Discovery

```python
from amarisoft import Callbox

# Connect and discover capabilities
cb = Callbox('192.168.1.80', ims_port=9003)
cb.connect_all()

# Discover and cache capabilities
caps = cb.discover_capabilities()
print(caps.summary())

# Export to dict for storage
import json
print(json.dumps(caps.to_dict(), indent=2))
```

### Using Validation

```python
from amarisoft import Callbox
from amarisoft.capabilities import ValidationContext

# Method 1: ValidationContext (recommended)
with Callbox("192.168.1.80", ims_port=9003) as cb:
    with ValidationContext(cb) as ctx:
        # These operations are validated against device capabilities
        ctx.checker.validate_rf_gain(tx_gain=60, mode="wired")
        ctx.checker.validate_cell_config(bandwidth_mhz=100)
        ctx.checker.validate_mcs(15)

        # Operations that would fail
        try:
            ctx.checker.validate_cell_config(bandwidth_mhz=500)  # Exceeds license
        except InvalidParameterError as e:
            print(f"Validation failed: {e}")

# Method 2: Enable validation on Callbox
cb = Callbox("192.168.1.80", ims_port=9003)
cb.connect_all()
checker = cb.enable_validation()  # Discovers capabilities automatically

# Now API calls can be validated
checker.validate_rf_gain(tx_gain=90, mode="wired")  # Raises if invalid

cb.disable_validation()  # Turn off validation
cb.close()
```

### Default Capabilities (CBM-2024121101)

```python
from amarisoft import get_default_capabilities

caps = get_default_capabilities()

# Device: CBM-2024121101
# SDR: SDR50 (Serial: 202405001019)
# License: Meta Platforms / NISCBM02_FRE6530
# Max Bandwidth: 120 MHz
# Max MIMO: 4 layers
# Supported RATs: LTE, NR
```

### Constraint Definitions

| Category | Constraint | Valid Range |
|----------|------------|-------------|
| **RF Gain (Wired)** | TX gain | 50-70 dB |
| | RX gain | 0-20 dB |
| **RF Gain (Wireless)** | TX gain | 80-95 dB |
| | RX gain | 50-70 dB |
| **LTE MCS** | Value | 0-28 |
| **NR MCS** | Value | 0-31 |
| **QCI** | Value | 1-9 (standard) |
| **MIMO** | Layers | 1, 2, 4, 8 |
| **Bandwidth** | License max | 120 MHz |
| **Cells** | License max | 1 |

### QCI Reference

| QCI | Type | Name | Delay | Priority |
|-----|------|------|-------|----------|
| 1 | GBR | Conversational Voice | 100ms | 2 |
| 2 | GBR | Conversational Video | 150ms | 4 |
| 3 | GBR | Real Time Gaming | 50ms | 3 |
| 4 | GBR | Non-Conv Video | 300ms | 5 |
| 5 | Non-GBR | IMS Signaling | 100ms | 1 |
| 6 | Non-GBR | Video (Buffered) | 300ms | 6 |
| 7 | Non-GBR | Voice/Video/Gaming | 100ms | 7 |
| 8 | Non-GBR | Video (Buffered) | 300ms | 8 |
| 9 | Non-GBR | Video/TCP | 300ms | 9 |

### Validation Decorators

Apply validation decorators to custom functions:

```python
from amarisoft.capabilities import (
    validate_rf_params,
    validate_mcs_param,
    validate_qci_param,
    require_service,
    require_feature,
)

class MyController:
    def __init__(self, callbox):
        self._callbox = callbox

    @validate_rf_params(mode="wired")
    def configure_rf(self, tx_gain=None, rx_gain=None):
        # Parameters validated before this runs
        return self._callbox.enb.rf(tx_gain=tx_gain, rx_gain=rx_gain)

    @require_service("ims")
    @require_feature("volte")
    def setup_volte(self):
        # Only runs if IMS is connected and VoLTE is enabled
        pass
```

### Testing Capabilities

```bash
# Run quick check without device
cd /Users/ekowtaylor/Documents/Personal/Github/amarisoft
python tests/integration/test_capabilities.py

# Run unit tests (no device)
pytest tests/integration/test_capabilities.py -v -m "not integration"

# Run all tests (device required)
pytest tests/integration/test_capabilities.py -v
```

---

## Test Logging & Diagnostics

The Python library includes comprehensive logging and diagnostics collection for end-to-end test runs.

### TestSession Context Manager

The `TestSession` class provides automatic log collection, step tracking, and diagnostics export:

```python
from amarisoft import Callbox, TestSession

with Callbox("192.168.1.80", ims_port=9003) as cb:
    cb.connect_all()

    with TestSession(cb, name="e2e_connectivity_test", output_dir="./logs") as session:

        with session.add_step("Verify Service Connectivity"):
            assert cb.status["enb"], "eNB not connected"
            assert cb.status["mme"], "MME not connected"

        with session.add_step("Configure RF Parameters"):
            cb.enb.rf(tx_gain=60, rx_gain=0)

        with session.add_step("Wait for UE Attachment"):
            import time
            time.sleep(10)
            ues = cb.enb.ue_get()
            assert len(ues.get("ue_list", [])) > 0, "No UE attached"

# Session automatically exports to:
# ./logs/e2e_connectivity_test_20260217_163000/
#   ├── session_info.json    # Session metadata, timing, step results
#   ├── logs_enb.txt         # eNB logs (human-readable)
#   ├── logs_mme.txt         # MME logs
#   ├── logs_all.txt         # Combined chronological logs
#   ├── logs_all.json        # Logs as JSON (for parsing)
#   ├── config_initial.json  # Config snapshot at start
#   ├── stats_initial.json   # Stats at start
#   ├── stats_final.json     # Stats at end
#   └── summary.txt          # Human-readable summary
```

### TestSession Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `name` | `"test_session"` | Session name (for logging and identification) |
| `output_dir` | `"./logs"` | Base directory for diagnostics |
| `folder_prefix` | `None` | Optional folder name prefix. If not provided, uses `name`. Timestamp always appended. |
| `collect_interval` | `1.0` | Log polling interval (seconds) |
| `auto_export` | `True` | Auto-export diagnostics on session end |
| `collect_on_error` | `True` | Collect extra diagnostics on failure |

**Folder naming:**
- `folder_prefix="volte_e2e"` → `./logs/volte_e2e_20260217_163000/`
- No `folder_prefix` set, `name="my_test"` → `./logs/my_test_20260217_163000/`

### LogCollector for Custom Collection

For more control, use `LogCollector` directly:

```python
from amarisoft import Callbox, LogCollector

cb = Callbox("192.168.1.80", ims_port=9003)
cb.connect_all()

collector = LogCollector(cb)

# One-time collection
entries = collector.collect_once(services=["enb", "mme"])
for entry in entries:
    print(entry)  # [timestamp] [service:layer] level: message

# Continuous collection in background
def on_log(entry):
    if entry.level == "ERROR":
        print(f"ERROR: {entry.message}")

collector.start_continuous(interval=0.5, callback=on_log)

# ... run your tests ...

collector.stop_continuous()

# Filter collected logs
errors = collector.filter_logs(level="ERROR")
rrc_logs = collector.filter_logs(layer="RRC")
attach_logs = collector.filter_logs(contains="attach")

cb.close()
```

### Filtering Logs

| Filter | Description | Example |
|--------|-------------|---------|
| `service` | Filter by service name | `"enb"`, `"mme"`, `"ims"` |
| `layer` | Filter by protocol layer | `"PHY"`, `"MAC"`, `"RRC"`, `"NAS"`, `"S1AP"` |
| `level` | Filter by log level | `"ERROR"`, `"WARNING"`, `"INFO"` |
| `contains` | Filter by message content | `"attach"`, `"bearer"`, `"failure"` |

### File Logging

Enable file logging for the entire amarisoft package:

```python
from amarisoft.logging import enable_file_logging

# Enable debug logging to file
enable_file_logging("amarisoft_debug.log", level=logging.DEBUG)

# Now all amarisoft operations are logged to file
cb = Callbox("192.168.1.80", ims_port=9003)
cb.connect_all()
# ... operations ...
```

### Analyzing Test Results

After a test run, analyze the diagnostics:

```python
import json

# Load session info
with open("./logs/e2e_test_20260217_163000/session_info.json") as f:
    session = json.load(f)

print(f"Status: {session['status']}")
print(f"Duration: {session['duration_s']:.2f}s")

for step in session['steps']:
    icon = "✓" if step['status'] == 'passed' else "✗"
    print(f"  [{icon}] {step['name']} ({step['duration_s']:.2f}s)")
    if step.get('error'):
        print(f"      Error: {step['error']}")

# Load and analyze logs
with open("./logs/e2e_test_20260217_163000/logs_all.json") as f:
    logs = json.load(f)

errors = [l for l in logs if l['level'] == 'ERROR']
print(f"\nTotal logs: {len(logs)}, Errors: {len(errors)}")
```

### Example Test Structure

```python
#!/usr/bin/env python3
"""End-to-end test example with full logging."""

from amarisoft import Callbox, TestSession
from amarisoft.capabilities import ValidationContext

def run_test():
    with Callbox("192.168.1.80", ims_port=9003) as cb:
        cb.connect_all()

        with TestSession(cb, name="full_e2e_test") as session:

            # Step 1: Validate capabilities
            with session.add_step("Capability Validation"):
                with ValidationContext(cb) as ctx:
                    ctx.checker.validate_rf_gain(tx_gain=60, mode="wired")

            # Step 2: Configure cell
            with session.add_step("Cell Configuration"):
                cb.enb.rf(tx_gain=60, rx_gain=0)

            # Step 3: Wait for UE
            with session.add_step("UE Attachment"):
                import time
                for _ in range(30):
                    ues = cb.enb.ue_get()
                    if ues.get("ue_list"):
                        break
                    time.sleep(1)
                else:
                    raise TimeoutError("UE did not attach within 30s")

            # Step 4: Run throughput
            with session.add_step("Throughput Test"):
                stats = cb.enb.stats()
                print(f"DL: {stats.get('dl_bitrate', 0)/1e6:.1f} Mbps")

            # Check for errors
            errors = session.get_errors()
            if errors:
                print(f"Warning: {len(errors)} errors during test")
                for e in errors[:5]:
                    print(f"  - {e.message}")

if __name__ == "__main__":
    run_test()
```

---
