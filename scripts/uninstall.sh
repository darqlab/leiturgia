#!/bin/bash
# =============================================================================
# Leiturgia Uninstall Script
# =============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run with sudo: sudo bash uninstall.sh"
  exit 1
fi

echo "Removing Leiturgia..."

systemctl stop leiturgia leiturgia-display 2>/dev/null || true
systemctl disable leiturgia leiturgia-display 2>/dev/null || true

rm -f /etc/systemd/system/leiturgia.service
rm -f /etc/systemd/system/leiturgia-display.service
systemctl daemon-reload

rm -rf /opt/leiturgia

echo "Leiturgia removed."
