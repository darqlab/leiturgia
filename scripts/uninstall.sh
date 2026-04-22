#!/bin/bash
# =============================================================================
# Leiturgia Uninstall Script
# https://github.com/darqlab/leiturgia
# Usage: sudo bash uninstall.sh
# =============================================================================

set -e

APP_NAME="leiturgia"
APP_DIR="/opt/leiturgia"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[Leiturgia]${NC} $1"; }
warning() { echo -e "${YELLOW}[Warning]${NC} $1"; }
error()   { echo -e "${RED}[Error]${NC} $1"; exit 1; }

if [ "$EUID" -ne 0 ]; then
  error "Please run with sudo: sudo bash uninstall.sh"
fi

echo ""
echo -e "${RED}========================================${NC}"
echo -e "${RED}  Leiturgia Uninstaller${NC}"
echo -e "${RED}========================================${NC}"
echo ""
warning "This will stop and remove the Leiturgia service."
echo ""

# -----------------------------------------------------------------------------
# Confirm uninstall
# -----------------------------------------------------------------------------
read -r -p "Are you sure you want to uninstall Leiturgia? [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "Uninstall cancelled."
  exit 0
fi

echo ""

# -----------------------------------------------------------------------------
# Ask whether to keep program data and media
# -----------------------------------------------------------------------------
read -r -p "Keep your program data, media files, and config? [Y/n] " KEEP_DATA
KEEP_DATA="${KEEP_DATA:-Y}"

BACKUP_DIR=""
if [[ "$KEEP_DATA" =~ ^[Yy]$ ]]; then
  BACKUP_DIR="/home/${SUDO_USER:-root}/leiturgia-backup-$(date +%Y%m%d%H%M%S)"
  info "Data will be backed up to: ${BACKUP_DIR}"
fi

echo ""

# -----------------------------------------------------------------------------
# 1. Stop and disable services
# -----------------------------------------------------------------------------
info "Stopping Leiturgia service..."
systemctl stop "${APP_NAME}" 2>/dev/null || true
systemctl disable "${APP_NAME}" 2>/dev/null || true

# -----------------------------------------------------------------------------
# 2. Remove systemd unit files
# -----------------------------------------------------------------------------
info "Removing systemd service..."
rm -f "/etc/systemd/system/${APP_NAME}.service"
systemctl daemon-reload

# -----------------------------------------------------------------------------
# 3. Back up data if requested
# -----------------------------------------------------------------------------
if [[ "$KEEP_DATA" =~ ^[Yy]$ ]] && [ -d "${APP_DIR}" ]; then
  info "Backing up data to ${BACKUP_DIR}..."
  mkdir -p "${BACKUP_DIR}"

  [ -f "${APP_DIR}/config.json" ]    && cp "${APP_DIR}/config.json"    "${BACKUP_DIR}/"
  [ -d "${APP_DIR}/data" ]           && cp -r "${APP_DIR}/data"        "${BACKUP_DIR}/"
  [ -d "${APP_DIR}/media" ]          && cp -r "${APP_DIR}/media"       "${BACKUP_DIR}/"

  if [ -n "$SUDO_USER" ]; then
    chown -R "${SUDO_USER}:${SUDO_USER}" "${BACKUP_DIR}"
  fi

  info "Backup complete."
fi

# -----------------------------------------------------------------------------
# 4. Remove application directory
# -----------------------------------------------------------------------------
info "Removing application files..."
rm -rf "${APP_DIR}"

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Leiturgia uninstalled successfully.${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [[ "$KEEP_DATA" =~ ^[Yy]$ ]] && [ -n "${BACKUP_DIR}" ]; then
  echo -e "  Your data was saved to: ${YELLOW}${BACKUP_DIR}${NC}"
  echo ""
fi
