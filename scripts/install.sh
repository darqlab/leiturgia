#!/bin/bash
# =============================================================================
# Leiturgia Install Script
# https://github.com/darqlab/leiturgia
# Usage: curl -fsSL https://raw.githubusercontent.com/darqlab/leiturgia/main/scripts/install.sh | sudo bash
# =============================================================================

set -e

APP_NAME="leiturgia"
APP_DIR="/opt/leiturgia"
APP_USER="leiturgia"
REPO="darqlab/leiturgia"
BRANCH="main"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[Leiturgia]${NC} $1"; }
warning() { echo -e "${YELLOW}[Warning]${NC} $1"; }
error()   { echo -e "${RED}[Error]${NC} $1"; exit 1; }

if [ "$EUID" -ne 0 ]; then
  error "Please run with sudo: curl -fsSL .../install.sh | sudo bash"
fi

# Dedicated, unprivileged system account for the service (mirrors packaging/debian/postinst)
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin "${APP_USER}"
fi

info "Starting Leiturgia installation (user: ${APP_USER})..."

# -----------------------------------------------------------------------------
# 1. System dependencies
# -----------------------------------------------------------------------------
info "Installing system dependencies..."
apt-get update -qq || true
apt-get install -y \
  python3 \
  python3-pip \
  python3-venv \
  git \
  openssl

info "Note: Chromium is pre-installed on Raspberry Pi OS. If missing, run: sudo apt-get install -y chromium"

# -----------------------------------------------------------------------------
# 2. Create app directory
# -----------------------------------------------------------------------------
info "Setting up application directory at ${APP_DIR}..."
mkdir -p "${APP_DIR}"

# -----------------------------------------------------------------------------
# 3. Clone or update repository
# -----------------------------------------------------------------------------
if [ -d "${APP_DIR}/.git" ]; then
  info "Existing installation found — updating..."
  # Repo may be owned by a pre-migration user (e.g. pi/dennis); git refuses to
  # operate on a repo owned by someone other than the running user otherwise.
  git config --global --add safe.directory "${APP_DIR}"
  git -C "${APP_DIR}" pull origin "${BRANCH}"
else
  info "Cloning Leiturgia repository..."
  git clone "https://github.com/${REPO}.git" "${APP_DIR}"
fi

# -----------------------------------------------------------------------------
# 4. Python virtual environment
# -----------------------------------------------------------------------------
info "Setting up Python virtual environment..."
python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip -q
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt" -q

# -----------------------------------------------------------------------------
# 5. Data and media directories
# -----------------------------------------------------------------------------
info "Creating data and media directories..."
mkdir -p \
  "${APP_DIR}/data/media/images" \
  "${APP_DIR}/data/media/videos" \
  "${APP_DIR}/data/lyrics" \
  "${APP_DIR}/output"

# -----------------------------------------------------------------------------
# 6. program.json — seed on first install only
# -----------------------------------------------------------------------------
PROGRAM_FILE="${APP_DIR}/data/program.json"
if [ ! -f "${PROGRAM_FILE}" ]; then
  info "Creating default program.json..."
  cat > "${PROGRAM_FILE}" <<'EOF'
{
  "church": "",
  "date": "",
  "pianist": "",
  "song_leader": "",
  "service_programs": [
    {
      "id": "sample-program",
      "name": "Sample Program",
      "time": "",
      "items": [
        {"item_id": "sp-001", "type": "participant", "title": "Opening Prayer", "part": "Opening Prayer", "participant": ""},
        {"item_id": "sp-002", "type": "song",        "title": "Opening Song",   "hymn_number": ""},
        {"item_id": "sp-003", "type": "media",       "title": "Welcome",        "media_type": "image",    "url": "/media/images/leiturgia-welcome.png"},
        {"item_id": "sp-004", "type": "media",       "title": "Sample Video",   "media_type": "video",    "url": "", "autoplay": true, "loop": false, "mute": false},
        {"item_id": "sp-005", "type": "content",     "title": "Announcements",  "content": ""}
      ]
    }
  ],
  "service_team": []
}
EOF
  chown "${APP_USER}:${APP_USER}" "${PROGRAM_FILE}"
else
  info "program.json already exists — skipping."
fi

# -----------------------------------------------------------------------------
# 7. config.json — generate on first install only
# -----------------------------------------------------------------------------
CONFIG_FILE="${APP_DIR}/config.json"
if [ ! -f "${CONFIG_FILE}" ]; then
  info "Generating config.json with random session secret..."
  SECRET=$(openssl rand -hex 32)
  cat > "${CONFIG_FILE}" <<EOF
{
  "pin": "1234",
  "session_secret": "${SECRET}",
  "session_timeout_hours": 8,
  "max_login_attempts": 5,
  "cloud_enabled": false,
  "cloud_url": "",
  "cloud_token": "",
  "enable_self_update": false
}
EOF
  chown "${APP_USER}:${APP_USER}" "${CONFIG_FILE}"
  chmod 640 "${CONFIG_FILE}"
  warning "Default PIN is 1234 — change it in ${CONFIG_FILE} after install."
else
  info "config.json already exists — skipping (secrets preserved)."
fi

# -----------------------------------------------------------------------------
# 8. Desktop shortcut (for the interactive user who ran this installer, if any —
#    the leiturgia service account has no home directory to put one in)
# -----------------------------------------------------------------------------
if [ -n "${SUDO_USER:-}" ]; then
  DESKTOP_DIR="/home/${SUDO_USER}/Desktop"
  SHORTCUT="${DESKTOP_DIR}/Leiturgia.desktop"
  if [ -d "${DESKTOP_DIR}" ]; then
    info "Creating desktop shortcut..."
    cat > "${SHORTCUT}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Leiturgia
Comment=Open Leiturgia operator console
Exec=sh -c 'chromium-browser http://localhost:5000 || chromium http://localhost:5000 || xdg-open http://localhost:5000'
Icon=${APP_DIR}/static/leiturgia-icon.png
Terminal=false
Categories=Application;
EOF
    chmod +x "${SHORTCUT}"
    chown "${SUDO_USER}:${SUDO_USER}" "${SHORTCUT}"
  else
    info "No Desktop directory found — skipping shortcut (headless install)."
  fi
else
  info "No interactive sudo user detected — skipping desktop shortcut (headless install)."
fi

# -----------------------------------------------------------------------------
# 8b. Fix ownership — app files were written as root above
# -----------------------------------------------------------------------------
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

# -----------------------------------------------------------------------------
# 9. systemd services
# -----------------------------------------------------------------------------
info "Installing systemd services..."

cat > /etc/systemd/system/leiturgia.service <<EOF
[Unit]
Description=Leiturgia Projection App
After=network.target

[Service]
User=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/.venv/bin/python app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable leiturgia

# -----------------------------------------------------------------------------
# 10. Start the app
# -----------------------------------------------------------------------------
info "Starting Leiturgia service..."
systemctl start leiturgia

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
PI_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Leiturgia installed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  Operator Console : ${YELLOW}http://${PI_IP}:5000${NC}"
echo -e "  Channel 1        : ${YELLOW}http://${PI_IP}:5000/ch1${NC}"
echo -e "  Channel 2        : ${YELLOW}http://${PI_IP}:5000/ch2${NC}"
echo ""
echo -e "  Config file      : ${CONFIG_FILE}"
echo -e "  Change PIN       : edit ${CONFIG_FILE} then: sudo systemctl restart leiturgia"
echo ""
echo -e "  Manage service:"
echo -e "    sudo systemctl restart leiturgia"
echo -e "    sudo systemctl status leiturgia"
echo -e "    journalctl -u leiturgia -f"
echo ""
