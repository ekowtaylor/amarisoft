#!/bin/bash
# Amarisoft REST API Deployment Script
# Deploys and configures the REST API service on an Amarisoft callbox

set -e  # Exit on error

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════

CALLBOX_HOST="${1:-192.168.1.80}"
CALLBOX_USER="${2:-root}"
INSTALL_DIR="/opt/amarisoft-rest-api"
SERVICE_NAME="amarisoft-rest-api"
SERVICE_PORT="9010"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ══════════════════════════════════════════════════════════════
# FUNCTIONS
# ══════════════════════════════════════════════════════════════

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  $1"
    echo "════════════════════════════════════════════════════════════"
}

# ══════════════════════════════════════════════════════════════
# MAIN DEPLOYMENT
# ══════════════════════════════════════════════════════════════

log_section "Amarisoft REST API Deployment"
echo "  Target: ${CALLBOX_USER}@${CALLBOX_HOST}"
echo "  Install Dir: ${INSTALL_DIR}"
echo "  Service Port: ${SERVICE_PORT}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# ──────────────────────────────────────────────
# Phase 1: Create deployment archive
# ──────────────────────────────────────────────
log_section "Phase 1: Creating Deployment Archive"

ARCHIVE_NAME="amarisoft-rest-api.tar.gz"

log_info "Creating archive: ${ARCHIVE_NAME}"
tar -czvf "/tmp/${ARCHIVE_NAME}" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='*.egg-info' \
    --exclude='.git' \
    service/ \
    client/ \
    requirements.txt

log_info "Archive created successfully"

# ──────────────────────────────────────────────
# Phase 2: Copy to callbox
# ──────────────────────────────────────────────
log_section "Phase 2: Copying Files to Callbox"

log_info "Copying archive to ${CALLBOX_HOST}..."
scp "/tmp/${ARCHIVE_NAME}" "${CALLBOX_USER}@${CALLBOX_HOST}:/tmp/"

log_info "Files copied successfully"

# ──────────────────────────────────────────────
# Phase 3: Install on callbox
# ──────────────────────────────────────────────
log_section "Phase 3: Installing on Callbox"

ssh "${CALLBOX_USER}@${CALLBOX_HOST}" << 'REMOTE_SCRIPT'
set -e

INSTALL_DIR="/opt/amarisoft-rest-api"
SERVICE_NAME="amarisoft-rest-api"

echo "[INFO] Creating installation directory..."
mkdir -p "${INSTALL_DIR}"

echo "[INFO] Extracting archive..."
cd "${INSTALL_DIR}"
tar -xzvf /tmp/amarisoft-rest-api.tar.gz

echo "[INFO] Setting up Python virtual environment..."
python3 -m venv venv

echo "[INFO] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[INFO] Dependencies installed successfully"
REMOTE_SCRIPT

log_info "Installation completed"

# ──────────────────────────────────────────────
# Phase 4: Create systemd service
# ──────────────────────────────────────────────
log_section "Phase 4: Creating Systemd Service"

ssh "${CALLBOX_USER}@${CALLBOX_HOST}" << 'REMOTE_SERVICE'
set -e

SERVICE_FILE="/etc/systemd/system/amarisoft-rest-api.service"

echo "[INFO] Creating service file..."
cat > "${SERVICE_FILE}" << 'EOF'
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
EOF

echo "[INFO] Reloading systemd..."
systemctl daemon-reload

echo "[INFO] Enabling service..."
systemctl enable amarisoft-rest-api

echo "[INFO] Starting service..."
systemctl restart amarisoft-rest-api

echo "[INFO] Service status:"
systemctl status amarisoft-rest-api --no-pager || true

REMOTE_SERVICE

log_info "Service created and started"

# ──────────────────────────────────────────────
# Phase 5: Verification
# ──────────────────────────────────────────────
log_section "Phase 5: Verification"

log_info "Waiting for service to start..."
sleep 3

log_info "Testing health endpoint..."
HEALTH_RESPONSE=$(ssh "${CALLBOX_USER}@${CALLBOX_HOST}" "curl -s http://127.0.0.1:9010/health" 2>/dev/null || echo "FAILED")

if echo "$HEALTH_RESPONSE" | grep -q "healthy\|status"; then
    log_info "Health check passed!"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"
else
    log_warn "Health check returned unexpected response: ${HEALTH_RESPONSE}"
    log_info "Checking service logs..."
    ssh "${CALLBOX_USER}@${CALLBOX_HOST}" "journalctl -u amarisoft-rest-api -n 20 --no-pager" || true
fi

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────
log_section "Deployment Complete"

echo ""
echo "  REST API Service is now running on:"
echo "    - Local:  http://127.0.0.1:${SERVICE_PORT}"
echo "    - Remote: http://${CALLBOX_HOST}:${SERVICE_PORT}"
echo ""
echo "  Quick Commands:"
echo "    - Status:  ssh ${CALLBOX_USER}@${CALLBOX_HOST} 'systemctl status ${SERVICE_NAME}'"
echo "    - Logs:    ssh ${CALLBOX_USER}@${CALLBOX_HOST} 'journalctl -u ${SERVICE_NAME} -f'"
echo "    - Restart: ssh ${CALLBOX_USER}@${CALLBOX_HOST} 'systemctl restart ${SERVICE_NAME}'"
echo ""
echo "  Test Endpoints:"
echo "    curl http://${CALLBOX_HOST}:${SERVICE_PORT}/health"
echo "    curl http://${CALLBOX_HOST}:${SERVICE_PORT}/version"
echo "    curl http://${CALLBOX_HOST}:${SERVICE_PORT}/enb/stats"
echo ""

# Cleanup
rm -f "/tmp/${ARCHIVE_NAME}"

log_info "Done!"
