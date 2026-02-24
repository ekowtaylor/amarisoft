# REST API Service Deployment Plan

## Target System
- **Callbox IP**: `192.168.1.80`
- **OS**: Ubuntu (typical Amarisoft callbox)
- **Service Port**: `9010`

---

## Phase 1: Prepare Deployment Package

### 1.1 Files to Deploy
```
/opt/amarisoft-rest-api/
├── service/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── exceptions.py
│   ├── main.py
│   ├── manager.py
│   ├── models.py
│   └── routers/
│       ├── __init__.py
│       ├── enb.py
│       ├── ims.py
│       ├── mme.py
│       ├── system.py
│       └── ue.py
├── client/                  # Client libraries
│   ├── __init__.py
│   └── websocket/           # WebSocket client (required by service)
│       ├── __init__.py
│       ├── base.py
│       ├── callbox.py
│       ├── capabilities.py
│       ├── client.py
│       ├── enb.py
│       ├── exceptions.py
│       ├── ims.py
│       ├── logging.py
│       ├── mme.py
│       ├── ssh.py
│       └── ue.py
├── requirements.txt
└── amarisoft-rest-api.service
```

### 1.2 Create Local Archive
```bash
# Create deployment archive locally
tar -czvf amarisoft-rest-api.tar.gz \
    service/ \
    client/ \
    requirements.txt
```

---

## Phase 2: Deploy to Callbox

### 2.1 Copy Files to Callbox
```bash
# Copy archive to callbox
scp amarisoft-rest-api.tar.gz root@192.168.1.80:/tmp/

# SSH into callbox
ssh root@192.168.1.80
```

### 2.2 Install on Callbox
```bash
# Create installation directory
mkdir -p /opt/amarisoft-rest-api

# Extract archive
cd /opt/amarisoft-rest-api
tar -xzvf /tmp/amarisoft-rest-api.tar.gz

# Create virtual environment
python3 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Phase 3: Create Systemd Service

### 3.1 Service File: `/etc/systemd/system/amarisoft-rest-api.service`
```ini
[Unit]
Description=Amarisoft REST API Service
Documentation=https://github.com/ekowtaylor/amarisoft
After=network.target lte.service
Wants=lte.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/amarisoft-rest-api
Environment="PATH=/opt/amarisoft-rest-api/venv/bin"
Environment="PYTHONPATH=/opt/amarisoft-rest-api"
Environment="AMARISOFT_HOST=0.0.0.0"
Environment="AMARISOFT_PORT=9010"
Environment="AMARISOFT_CALLBOX_HOST=127.0.0.1"
Environment="AMARISOFT_ENB_PORT=9001"
Environment="AMARISOFT_MME_PORT=9000"
Environment="AMARISOFT_IMS_PORT=9002"
Environment="AMARISOFT_UE_PORT=9003"

ExecStart=/opt/amarisoft-rest-api/venv/bin/python -m service.main \
    --host 0.0.0.0 \
    --port 9010 \
    --callbox-host 127.0.0.1

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/amarisoft-rest-api

[Install]
WantedBy=multi-user.target
```

### 3.2 Enable and Start Service
```bash
# Reload systemd
systemctl daemon-reload

# Enable service to start on boot
systemctl enable amarisoft-rest-api

# Start the service
systemctl start amarisoft-rest-api

# Check status
systemctl status amarisoft-rest-api

# View logs
journalctl -u amarisoft-rest-api -f
```

---

## Phase 4: Verification

### 4.1 Health Check
```bash
# From callbox (localhost)
curl http://127.0.0.1:9010/health

# From remote machine
curl http://192.168.1.80:9010/health
```

### 4.2 Test Endpoints
```bash
# Get version
curl http://192.168.1.80:9010/version

# Get eNB status
curl http://192.168.1.80:9010/enb/stats

# List connected UEs
curl http://192.168.1.80:9010/mme/ue
```

---

## Phase 5: Firewall Configuration (if needed)

```bash
# Allow port 9010 through firewall
ufw allow 9010/tcp

# Or with iptables
iptables -A INPUT -p tcp --dport 9010 -j ACCEPT
```

---

## Quick Commands Reference

| Action | Command |
|--------|---------|
| Start service | `systemctl start amarisoft-rest-api` |
| Stop service | `systemctl stop amarisoft-rest-api` |
| Restart service | `systemctl restart amarisoft-rest-api` |
| View status | `systemctl status amarisoft-rest-api` |
| View logs | `journalctl -u amarisoft-rest-api -f` |
| Enable on boot | `systemctl enable amarisoft-rest-api` |
| Disable on boot | `systemctl disable amarisoft-rest-api` |

---

## Rollback Procedure

```bash
# Stop and disable service
systemctl stop amarisoft-rest-api
systemctl disable amarisoft-rest-api

# Remove service file
rm /etc/systemd/system/amarisoft-rest-api.service
systemctl daemon-reload

# Remove installation
rm -rf /opt/amarisoft-rest-api
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AMARISOFT_HOST` | `0.0.0.0` | REST API listen address |
| `AMARISOFT_PORT` | `9010` | REST API listen port |
| `AMARISOFT_CALLBOX_HOST` | `127.0.0.1` | Callbox WebSocket host |
| `AMARISOFT_ENB_PORT` | `9001` | eNB WebSocket port |
| `AMARISOFT_MME_PORT` | `9000` | MME WebSocket port |
| `AMARISOFT_IMS_PORT` | `9002` | IMS WebSocket port |
| `AMARISOFT_UE_PORT` | `9003` | UE Simulator port |
| `AMARISOFT_WS_TIMEOUT` | `10.0` | WebSocket timeout (seconds) |
