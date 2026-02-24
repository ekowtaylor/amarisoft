#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Amarisoft REST API - One-Line Installer
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/ekowtaylor/amarisoft/main/install.sh | bash
#
# Or with custom options:
#   curl -sSL https://raw.githubusercontent.com/ekowtaylor/amarisoft/main/install.sh | bash -s -- --port 9010
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

REPO_URL="https://github.com/ekowtaylor/amarisoft.git"
REPO_BRANCH="main"
INSTALL_DIR="/opt/amarisoft-rest-api"
SERVICE_NAME="amarisoft-rest-api"
SERVICE_PORT="9010"
SERVICE_HOST="0.0.0.0"
CALLBOX_HOST="127.0.0.1"
ENB_PORT="9001"
MME_PORT="9000"
IMS_PORT="9002"
UE_PORT="9003"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

log_info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "${CYAN}[STEP]${NC} $1"; }

log_section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
}

show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
    _                         _           __ _
   / \   _ __ ___   __ _ _ __(_)___  ___ / _| |_
  / _ \ | '_ ` _ \ / _` | '__| / __|/ _ \ |_| __|
 / ___ \| | | | | | (_| | |  | \__ \  __/  _| |_
/_/   \_\_| |_| |_|\__,_|_|  |_|___/\___|_|  \__|

         REST API Service Installer
EOF
    echo -e "${NC}"
}

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
  --port PORT           Service port (default: 9010)
  --host HOST           Service bind host (default: 0.0.0.0)
  --callbox-host HOST   Callbox host for WebSocket (default: 127.0.0.1)
  --install-dir DIR     Installation directory (default: /opt/amarisoft-rest-api)
  --branch BRANCH       Git branch to install (default: main)
  --uninstall           Remove the service and all files
  --help                Show this help message

Examples:
  # Standard installation
  curl -sSL https://raw.githubusercontent.com/ekowtaylor/amarisoft/main/install.sh | bash

  # Custom port
  curl -sSL https://raw.githubusercontent.com/ekowtaylor/amarisoft/main/install.sh | bash -s -- --port 8080

  # Uninstall
  curl -sSL https://raw.githubusercontent.com/ekowtaylor/amarisoft/main/install.sh | bash -s -- --uninstall
EOF
}

# ═══════════════════════════════════════════════════════════════════════════════
# PARSE ARGUMENTS
# ═══════════════════════════════════════════════════════════════════════════════

UNINSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            SERVICE_PORT="$2"
            shift 2
            ;;
        --host)
            SERVICE_HOST="$2"
            shift 2
            ;;
        --callbox-host)
            CALLBOX_HOST="$2"
            shift 2
            ;;
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --branch)
            REPO_BRANCH="$2"
            shift 2
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# ═══════════════════════════════════════════════════════════════════════════════
# UNINSTALL
# ═══════════════════════════════════════════════════════════════════════════════

if [ "$UNINSTALL" = true ]; then
    log_section "Uninstalling Amarisoft REST API"

    log_step "Stopping service..."
    systemctl stop ${SERVICE_NAME} 2>/dev/null || true

    log_step "Disabling service..."
    systemctl disable ${SERVICE_NAME} 2>/dev/null || true

    log_step "Removing service file..."
    rm -f /etc/systemd/system/${SERVICE_NAME}.service
    systemctl daemon-reload

    log_step "Removing installation directory..."
    rm -rf "${INSTALL_DIR}"

    log_info "Uninstall complete!"
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════════════════
# PRE-FLIGHT CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

show_banner

log_section "Pre-flight Checks"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root"
    echo "  Run with: sudo bash install.sh"
    exit 1
fi

# Detect OS type
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        OS_NAME=$PRETTY_NAME
    elif [ -f /etc/redhat-release ]; then
        OS="rhel"
        OS_NAME=$(cat /etc/redhat-release)
    elif [ -f /etc/debian_version ]; then
        OS="debian"
        OS_NAME="Debian $(cat /etc/debian_version)"
    else
        OS="unknown"
        OS_NAME="Unknown"
    fi
}

detect_os
log_info "Detected OS: ${OS_NAME}"

# Determine package manager
if command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    PKG_INSTALL="dnf install -y"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    PKG_INSTALL="yum install -y"
elif command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
    PKG_INSTALL="apt-get install -y"
else
    log_error "No supported package manager found (dnf, yum, or apt)"
    exit 1
fi

log_info "Package manager: ${PKG_MANAGER}"

# Check for systemd
if ! command -v systemctl &> /dev/null; then
    log_error "systemd is required but not found"
    exit 1
fi
log_info "systemd: available"

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALL DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════

log_section "Installing Dependencies"

log_step "Updating package index..."
if [ "$PKG_MANAGER" = "apt" ]; then
    apt-get update -qq
fi

# Install Python 3 and pip
log_step "Installing Python 3..."
case $PKG_MANAGER in
    dnf|yum)
        $PKG_INSTALL python3 python3-pip python3-venv git curl
        ;;
    apt)
        $PKG_INSTALL python3 python3-pip python3-venv git curl
        ;;
esac

# Verify Python installation
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 installation failed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
log_info "Python: ${PYTHON_VERSION}"

# ═══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD AND INSTALL
# ═══════════════════════════════════════════════════════════════════════════════

log_section "Downloading Amarisoft REST API"

# Stop existing service if running
if systemctl is-active --quiet ${SERVICE_NAME}; then
    log_step "Stopping existing service..."
    systemctl stop ${SERVICE_NAME}
fi

# Backup existing installation if present
if [ -d "${INSTALL_DIR}" ]; then
    BACKUP_DIR="${INSTALL_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
    log_step "Backing up existing installation to ${BACKUP_DIR}..."
    mv "${INSTALL_DIR}" "${BACKUP_DIR}"
fi

# Clone the repository
log_step "Cloning repository..."
git clone --depth 1 --branch "${REPO_BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"

cd "${INSTALL_DIR}"

# ═══════════════════════════════════════════════════════════════════════════════
# SETUP PYTHON ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════════

log_section "Setting Up Python Environment"

log_step "Creating virtual environment..."
python3 -m venv venv

log_step "Activating virtual environment..."
source venv/bin/activate

log_step "Upgrading pip..."
pip install --upgrade pip -q

log_step "Installing dependencies..."
pip install -r requirements.txt -q

log_info "Dependencies installed successfully"

# Verify installation
if python -c "import fastapi; import uvicorn; import websocket" 2>/dev/null; then
    log_info "All Python packages verified"
else
    log_error "Package verification failed"
    exit 1
fi

deactivate

# ═══════════════════════════════════════════════════════════════════════════════
# CREATE SYSTEMD SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

log_section "Creating Systemd Service"

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

log_step "Creating service file..."
cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=Amarisoft REST API Service
Documentation=https://github.com/ekowtaylor/amarisoft
After=network.target lte.service
Wants=lte.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/venv/bin"
Environment="PYTHONPATH=${INSTALL_DIR}"
Environment="AMARISOFT_HOST=${SERVICE_HOST}"
Environment="AMARISOFT_PORT=${SERVICE_PORT}"
Environment="AMARISOFT_CALLBOX_HOST=${CALLBOX_HOST}"
Environment="AMARISOFT_ENB_PORT=${ENB_PORT}"
Environment="AMARISOFT_MME_PORT=${MME_PORT}"
Environment="AMARISOFT_IMS_PORT=${IMS_PORT}"
Environment="AMARISOFT_UE_PORT=${UE_PORT}"

ExecStart=${INSTALL_DIR}/venv/bin/python -m service.main \\
    --host ${SERVICE_HOST} \\
    --port ${SERVICE_PORT} \\
    --callbox-host ${CALLBOX_HOST}

Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${INSTALL_DIR}

[Install]
WantedBy=multi-user.target
EOF

log_step "Reloading systemd..."
systemctl daemon-reload

log_step "Enabling service..."
systemctl enable ${SERVICE_NAME}

log_step "Starting service..."
systemctl start ${SERVICE_NAME}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURE FIREWALL (if applicable)
# ═══════════════════════════════════════════════════════════════════════════════

log_section "Configuring Firewall"

# Check for firewalld (RHEL/CentOS/Fedora)
if command -v firewall-cmd &> /dev/null && systemctl is-active --quiet firewalld; then
    log_step "Opening port ${SERVICE_PORT} in firewalld..."
    firewall-cmd --permanent --add-port=${SERVICE_PORT}/tcp
    firewall-cmd --reload
    log_info "Firewall rule added"
# Check for ufw (Ubuntu/Debian)
elif command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
    log_step "Opening port ${SERVICE_PORT} in ufw..."
    ufw allow ${SERVICE_PORT}/tcp
    log_info "Firewall rule added"
else
    log_warn "No active firewall detected, skipping firewall configuration"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

log_section "Verification"

log_step "Waiting for service to start..."
sleep 3

# Check service status
if systemctl is-active --quiet ${SERVICE_NAME}; then
    log_info "Service is running"
else
    log_error "Service failed to start"
    log_step "Checking logs..."
    journalctl -u ${SERVICE_NAME} -n 20 --no-pager
    exit 1
fi

# Test health endpoint
log_step "Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s "http://127.0.0.1:${SERVICE_PORT}/health" 2>/dev/null || echo "FAILED")

if echo "$HEALTH_RESPONSE" | grep -q "healthy\|status"; then
    log_info "Health check passed!"
else
    log_warn "Health check returned: ${HEALTH_RESPONSE}"
    log_info "Service may still be initializing..."
fi

# ═══════════════════════════════════════════════════════════════════════════════
# COMPLETION
# ═══════════════════════════════════════════════════════════════════════════════

log_section "Installation Complete!"

# Get local IP
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo -e "${GREEN}  ✓ Amarisoft REST API is now running!${NC}"
echo ""
echo -e "  ${BOLD}Service Endpoints:${NC}"
echo "    Local:   http://127.0.0.1:${SERVICE_PORT}"
echo "    Remote:  http://${LOCAL_IP}:${SERVICE_PORT}"
echo ""
echo -e "  ${BOLD}API Documentation:${NC}"
echo "    Swagger: http://${LOCAL_IP}:${SERVICE_PORT}/docs"
echo "    ReDoc:   http://${LOCAL_IP}:${SERVICE_PORT}/redoc"
echo ""
echo -e "  ${BOLD}Quick Commands:${NC}"
echo "    Status:   systemctl status ${SERVICE_NAME}"
echo "    Logs:     journalctl -u ${SERVICE_NAME} -f"
echo "    Restart:  systemctl restart ${SERVICE_NAME}"
echo "    Stop:     systemctl stop ${SERVICE_NAME}"
echo ""
echo -e "  ${BOLD}Test Commands:${NC}"
echo "    curl http://127.0.0.1:${SERVICE_PORT}/health"
echo "    curl http://127.0.0.1:${SERVICE_PORT}/version"
echo "    curl http://127.0.0.1:${SERVICE_PORT}/enb/stats"
echo ""
echo -e "  ${BOLD}Uninstall:${NC}"
echo "    curl -sSL https://raw.githubusercontent.com/ekowtaylor/amarisoft/main/install.sh | bash -s -- --uninstall"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
