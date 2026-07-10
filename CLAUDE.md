> Global preferences: see /home/dennis/CLAUDE.md
>
> **Two-file split:** this is the **code-side** `CLAUDE.md` (Forge-owned, travels via git) — build/run/test, architecture, and code-operational constants. Planning/process docs live in `~/devops/projects/leiturgia/CLAUDE.md` (Polaris-owned, synced via Nextcloud). Each file references the other; neither restates the other's content.

# Leiturgia — Project Guide

## Overview

Flask + Flask-SocketIO app for managing church service programs (the "order of service") and driving live projection on a Raspberry Pi over the LAN. Single-user/operator, LAN-only, PIN-authenticated, eventlet async backend, on-disk JSON state (no database except the bundled hymnal).

**Codebase:** `/home/dennis/Projects/Leiturgia/` (`darqlab/leiturgia`)
**Local staging dir:** `/opt/yard/leiturgia/` — has its own runtime state (`data/`, `media/`, `config.json`, `.env`) that must not be overwritten by a sync.

---

## Running the App (Test / Staging)

The app is run from the **staging directory**, not the codebase. Before running, sync source changes from the codebase:

### 1. Sync codebase → staging

```bash
git -C /home/dennis/Projects/Leiturgia ls-files | \
  rsync -av --files-from=- /home/dennis/Projects/Leiturgia/ /opt/yard/leiturgia/
```

This syncs only git-tracked files (source code, templates, static assets, `data/hymns_en.db`, `data/hymns_tl.db`).
It **does not touch** `config.json`, `.env`, `data/*.json`, `data/lyrics/`, or `media/` uploads.

### 2. Start the server

```bash
cd /opt/yard/leiturgia && bash run.sh
```

`run.sh` activates `.venv` and launches `app.py`. If the venv is missing, run `bash install.sh` first.

### Common Development Commands

```bash
# Sync and run in one step
git -C /home/dennis/Projects/Leiturgia ls-files | \
  rsync -av --files-from=- /home/dennis/Projects/Leiturgia/ /opt/yard/leiturgia/ \
  && cd /opt/yard/leiturgia && bash run.sh
```

### Production / client deploy

- `scripts/install.sh` — fresh install from a git clone (the self-update-capable path; pulls `main`).
- `deploy.sh` — pulls `main` and restarts the `leiturgia` systemd service on an existing checkout (staging/QA Pi).
- `packaging/debian/` — `.deb` build (non-self-updating channel; see REL-1/PROV-1 history in the planning-side docs).

---

## Project Structure

| Path | Purpose |
|------|---------|
| `app.py` | Flask app entry point, routes, Socket.IO handlers |
| `hymnal.py` | Hymnal routes and DB access (`hymns_en.db` / `hymns_tl.db`) |
| `order_of_service.py` | Order-of-service / program logic (formerly `rundown.py`) |
| `projection.py` | Projection engine — serves `/ch<n>` channel views |
| `media_manager.py` | Media upload and management |
| `roles.py` | Role-to-channel assignment logic |
| `timer.py` | Timer feature |
| `cloud_agent.py` | Cloud sync agent (push/pull `program.json`) |
| `jsonio.py` | Atomic JSON read/write helper (`atomic_write_json`, retrying `load_json`) |
| `version.py` | Runtime version via `git describe --tags --always --dirty` |
| `templates/` | Jinja2 HTML templates |
| `static/` | CSS, JS, image assets |
| `data/hymns_en.db`, `data/hymns_tl.db` | Bundled hymnal SQLite DBs (tracked in git, bilingual) |
| `data/` (rest) | Runtime state (`program.json`, `history.json`, `role_assignments.json`, lyrics cache) — gitignored, lives in staging only |
| `media/` | Media uploads — gitignored except `media/images/leiturgia-welcome.png` |
| `config.json` | Runtime config — gitignored, lives in staging only |
| `.env` | Secrets — gitignored, lives in staging only |
| `scripts/` | Host-side install/update/provisioning scripts (`install.sh`, `update.sh`, `provision-self-update.sh`, `uninstall.sh`) |
| `packaging/debian/` | `.deb` packaging (`control`, `postinst`, `prerm`) |

---

## Architecture Constants

- **Auth:** single shared operator PIN (`@operator_required` in `app.py`); no per-user accounts/RBAC.
- **Projection channels:** `GET /ch<n>` (`app.py` `projection_channel`) — each channel `chN` is mapped to a role via `roles.py`.
- **Async backend:** `eventlet` (monkey-patched as the very first import in `app.py`); Socket.IO runs `async_mode='eventlet'`.
- **State persistence:** all JSON state files are read/written via `jsonio.py`'s `atomic_write_json` (temp file + `fsync` + `os.replace`) to avoid the read/write races fixed in issue #80.
- **Health check:** `/api/health` (no auth, localhost-only) — used by the operator self-update auto-revert.
- **Media storage budget:** configurable cap on `media/videos` (+ minimal `media/images` cap) enforced at upload and yt-dlp ingestion, plus a hard filesystem-free reserve. Config keys (`config.json`, all optional with defaults): `media_video_budget_gb` (2), `media_image_budget_gb` (1), `media_disk_reserve_gb` (1), `media_warn_percent` (80), `media_video_dir` (unset = built-in `media/videos`; otherwise an absolute path on a mounted/writable/allowlisted drive, set via `POST /api/settings/video-dir` rather than hand-edited). All video-path logic goes through `media_manager.videos_dir()`/`videos_unavailable()` — never hard-code `media/videos`. See planning docs `api-reference.md` → "Media", `data-schemas.md` → "Media Usage" / "Config File", `ref/modules.md` → `media_manager.py`, and `development/tdd/modules/media-storage-budget.md` for the full design.

---

## Branch & Release Conventions

- **Two-branch model:** `develop` (active integration) and `main` (stable/deployable). `develop` should track `main` once features land — fast-forward `develop` → `main` after merges if it drifts.
- **Feature/fix branches:** `feat/<name>` or `fix/<name>`, branched off `main`, merged back to `main` via PR.
- **Releases:** signed annotated tags `vX.Y.Z` (`git tag -s`), verified via `git tag -v` by `scripts/update.sh` and `provision-self-update.sh`. Signing pubkey: `packaging/release-signing-pubkey.asc`.
- **Deploy paths:** `scripts/install.sh` (git-clone, self-update-capable) is the canonical client install; `.deb` (`packaging/debian/`) is a non-self-updating alternative channel.

---

## Key Rules

- **Never run the app from the codebase dir** — always sync to staging first.
- **Never overwrite `config.json` or `.env`** in staging — these are hand-maintained secrets/config.
- **`data/hymns_en.db` / `data/hymns_tl.db` are the exception** — tracked in git, synced to staging on update.
- Staging venv lives at `/opt/yard/leiturgia/.venv` — managed by `install.sh`.
- All `program.json`/state-file writes must go through `jsonio.atomic_write_json` — never `open(path, "w")` directly.
