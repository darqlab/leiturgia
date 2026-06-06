#!/usr/bin/env bash
# install.sh — Complete setup for Leiturgia
# Usage: bash install.sh
set -euo pipefail

VENV_DIR=".venv"

echo "==> Checking Python 3..."
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install it and re-run."
  exit 1
fi
python3 --version

# ── Virtual environment ──────────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
  echo "==> Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
else
  echo "==> Virtual environment already exists."
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ── Dependencies ─────────────────────────────────────────────────────────────
echo "==> Installing/updating Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt

# ── Data directories ─────────────────────────────────────────────────────────
echo "==> Ensuring data directories exist..."
mkdir -p media/images media/videos data/lyrics output

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "Setup complete. To start the app:"
echo "  source $VENV_DIR/bin/activate"
echo "  python app.py"
