#!/usr/bin/env bash
# =============================================================================
# Leiturgia In-Place Updater
#
# Cantor host artifact — installed by Castellan/Dennis as part of host
# provisioning. It is NOT part of the app's import path or runtime; it ships
# in the repo as a template/example and is inert until placed on a host.
#
# Runs as root, out-of-process from the `leiturgia` service, via the
# `leiturgia-update.service` oneshot unit (started on demand by the web layer
# through the sudoers-gated `systemctl start leiturgia-update.service`).
# Because it runs out-of-process, it survives the `leiturgia` service restart
# that happens mid-update — which is what lets it health-check the new version
# and auto-revert if the health check fails (TDD §6.2).
#
# Logs: journalctl -u leiturgia-update
# =============================================================================

set -euo pipefail

cd /opt/leiturgia

# Defensive, not a substitute for provisioning: normally set once by
# provision-self-update.sh, but this runs as root against a repo owned by the
# `leiturgia` service user, and any host where that step was skipped, redone
# manually, or had root's gitconfig reset would otherwise hard-fail every git
# command below with "detected dubious ownership".
git config --global --add safe.directory /opt/leiturgia

# Release the update lock on any exit — including early failures (invalid-tag,
# unknown-tag, bad-signature) that would otherwise leave the lock permanently.
trap 'rm -f data/update/lock' EXIT

REQ=data/update/request.json
ST=data/update/status.json

# -----------------------------------------------------------------------------
# write_status <status> [current] [target_tag]
#
# Builds a JSON status object and writes it atomically to $ST (temp file in
# the same directory, then `mv` into place) so a concurrent reader — the
# Flask app's `GET /api/update/status` — never observes a half-written file.
# Mirrors the app's `atomic_write_json` pattern (jsonio.py).
#
# Every call also echoes a human-readable line to stdout, which systemd routes
# to journald (journalctl -u leiturgia-update), per the spec.
# -----------------------------------------------------------------------------
write_status() {
  local status="$1"
  local current="${2:-}"
  local target_tag="${3:-}"
  local ts
  ts=$(date +%s)

  local tmp
  tmp=$(mktemp "$(dirname "$ST")/.tmp-status-XXXXXX.json")

  jq -n \
    --arg status "$status" \
    --arg current "$current" \
    --arg target_tag "$target_tag" \
    --argjson ts "$ts" \
    '{status: $status, current: $current, target_tag: $target_tag, ts: $ts}' \
    > "$tmp"

  mv -f "$tmp" "$ST"

  echo "[leiturgia-update] status=${status} current=${current} target_tag=${target_tag}"
}

TAG=$(jq -r .target_tag "$REQ")

[[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { write_status invalid-tag; exit 1; }

CURRENT=$(git describe --tags --always)
write_status updating "$CURRENT" "$TAG"

# Backstop only — the web layer's connectivity preflight (TDD §6.4, D5)
# normally catches an offline box before this script ever starts.
git fetch --tags --force || { write_status offline; exit 1; }

git rev-parse "refs/tags/$TAG" >/dev/null 2>&1 || { write_status unknown-tag; exit 1; }

# OQ-2 (REQUIRED): release tags are GPG-signed; `git tag -v` verifies the tag's
# signature against the signer's public key in the keyring on this host. If
# verification fails (or no signature is present), reject the update — do not
# check out an unsigned/unverifiable tag.
git tag -v "$TAG" >/dev/null 2>&1 || { write_status bad-signature; exit 1; }

git checkout -q "tags/$TAG"
.venv/bin/pip install --quiet -r requirements.txt
systemctl restart leiturgia

# Health poll: 15 attempts, 2 seconds apart.
for i in $(seq 1 15); do
  sleep 2
  if curl -fsS http://127.0.0.1:5000/api/health | jq -e '.status=="ok"' >/dev/null; then
    write_status success "$TAG"
    exit 0
  fi
done

# Auto-revert: health check never passed — roll back to the previous version.
git checkout -q "$CURRENT"
.venv/bin/pip install --quiet -r requirements.txt
systemctl restart leiturgia

if curl -fsS http://127.0.0.1:5000/api/health >/dev/null; then
  write_status reverted "$CURRENT"
else
  write_status revert-failed "$CURRENT"
fi
