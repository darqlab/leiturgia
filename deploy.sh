#!/usr/bin/env bash
# deploy.sh — Pull latest changes and restart the Leiturgia service
# Usage: bash deploy.sh
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Pulling latest changes..."
git pull origin main

echo "==> Updating Python dependencies..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

echo "==> Restarting service..."
sudo systemctl restart leiturgia

echo "==> Waiting for service to come up..."
sleep 2
sudo systemctl status leiturgia --no-pager
