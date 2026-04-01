#!/usr/bin/env bash
# run.sh — Start the Leiturgia Flask server
set -euo pipefail

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found. Run: bash install.sh"
  exit 1
fi

source "$VENV_DIR/bin/activate"
python app.py
