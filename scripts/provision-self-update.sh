#!/usr/bin/env bash
# =============================================================================
# Leiturgia Self-Update Host Provisioning (PROV-1 / ADR-0002 D6, Path A)
#
# Idempotent, root-run script that provisions the host-side plumbing for the
# operator self-update feature on a git-clone (Path A) install of
# /opt/leiturgia: trusts the release-signing key in root's GPG keyring,
# installs the leiturgia-update oneshot unit, and installs the sudoers rule
# (retargeted to the live service user). It NEVER touches `enable_self_update`
# in config.json — enabling the feature stays a manual per-host decision.
#
# Safe to call unconditionally from packaging/debian/postinst: on a non-git
# (.deb) tree it is a clean no-op (exit 0), since the .deb channel remains
# non-self-updating.
#
# Usage: sudo APP_DIR=/opt/leiturgia bash scripts/provision-self-update.sh
# =============================================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/leiturgia}"
KEY_FPR="9D4B268CB2B47D8AD82123B5D1697B79BA58D268"

# -----------------------------------------------------------------------------
# Guard: self-update is GIT-based. On a non-checkout (e.g. a plain .deb tree)
# there is nothing to provision — print an informational note and exit 0 so
# this is safe to call from .deb postinst without affecting non-self-update
# installs.
# -----------------------------------------------------------------------------
if ! git -C "$APP_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "INFO: $APP_DIR is not a git checkout — self-update provisioning skipped; this host uses the .deb non-self-update channel."
  exit 0
fi

# Live service user (auto-handles the pi -> dennis drift).
SVC_USER="$(systemctl show leiturgia -p User --value 2>/dev/null || true)"
if [ -z "$SVC_USER" ]; then
  MAIN_PID="$(systemctl show leiturgia -p MainPID --value 2>/dev/null || true)"
  SVC_USER="$(ps -o user= -p "$MAIN_PID" 2>/dev/null || echo pi)"
  SVC_USER="$(echo "$SVC_USER" | tr -d '[:space:]')"
  [ -n "$SVC_USER" ] || SVC_USER="pi"
fi
echo "INFO: provisioning for service user '$SVC_USER'"

# -----------------------------------------------------------------------------
# S2 — trust the signer key in ROOT's keyring.
#
# `gpg --import` of an already-present key is a harmless no-op (idempotent),
# and re-running `gpg --import-ownertrust` for the same fingerprint/level just
# re-asserts the same trust value, so neither needs a pre-check guard.
# -----------------------------------------------------------------------------
gpg --import "$APP_DIR/packaging/release-signing-pubkey.asc"
echo "${KEY_FPR}:6:" | gpg --import-ownertrust

git config --global --add safe.directory "$APP_DIR"

# Verify the most recent annotated release tag reachable from HEAD, rather
# than hardcoding a specific version (which would go stale). Don't abort the
# whole script if no signed tag is checked out yet or verification fails —
# the keyring/units/sudoers are still useful to provision ahead of the first
# signed checkout.
if TAG="$(git -C "$APP_DIR" describe --tags --abbrev=0 --match 'v[0-9]*.[0-9]*.[0-9]*' 2>/dev/null)"; then
  if git -C "$APP_DIR" tag -v "$TAG" >/dev/null 2>&1; then
    echo "INFO: verified signature on tag '$TAG'."
  else
    echo "WARNING: signature verification of tag '$TAG' failed — check the signer key and tag signature."
  fi
else
  echo "WARNING: no annotated release tag (vX.Y.Z) found reachable from HEAD — skipping signature verification."
fi

# -----------------------------------------------------------------------------
# P1 — oneshot unit.
# -----------------------------------------------------------------------------
install -m 0644 "$APP_DIR/packaging/leiturgia-update.service" /etc/systemd/system/leiturgia-update.service
systemctl daemon-reload

# -----------------------------------------------------------------------------
# P1 — sudoers, retargeted to the live service user.
#
# Always render + syntax-check before installing, even if a file already
# exists at the destination — overwriting with identical content is harmless,
# and this guarantees the rule stays correct if SVC_USER ever changes.
# -----------------------------------------------------------------------------
TMP_SUDOERS="$(mktemp)"
trap 'rm -f "$TMP_SUDOERS"' EXIT
sed "s/^pi /$SVC_USER /" "$APP_DIR/packaging/leiturgia-update.sudoers" > "$TMP_SUDOERS"
visudo -cf "$TMP_SUDOERS"
install -m 0440 "$TMP_SUDOERS" /etc/sudoers.d/leiturgia-update
visudo -c >/dev/null

mkdir -p "$APP_DIR/data/update"
chown -R "$SVC_USER" "$APP_DIR/data/update" 2>/dev/null || true

echo "OK — self-update plumbing provisioned for '$SVC_USER'. Gate stays OFF (enable_self_update untouched)."
