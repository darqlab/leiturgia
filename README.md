# Leiturgia

A Flask web app for managing church service programs — live editing, real-time projection
to external displays, mobile remote control, and PowerPoint/LibreOffice slide generation.
Runs on a Raspberry Pi and is accessible from any device on the same network.

---

## Features

- **Program editor** — build and edit multi-program service orders (Sabbath School, Divine Service, AY, etc.)
- **Live projection** — send slides, songs, media, announcements, and timers to a projector/TV in real time via WebSockets
- **Mobile remote** — control the projection from any phone or tablet on the local network
- **Timer display** — dedicated countdown/elapsed timer view for service flow
- **Rundown view** — at-a-glance program order for worship leaders
- **Announcement display** — full-screen announcement channel
- **Slide generation** — export programs as `.pptx` (PowerPoint) or `.odp` (LibreOffice) files
- **Hymn lyrics** — fetch and cache lyrics by hymn number or title; offline SQLite fallback (695 hymns)
- **10 projection themes** — switchable color themes for the projection display
- **Media support** — upload images/videos or paste URLs; send directly to projection
- **PIN authentication** — operator console protected by a configurable PIN
- **Program history** — rolling view of the last 6 saved programs

---

## Install

### One-line installer (Raspberry Pi)

```bash
curl -fsSL https://raw.githubusercontent.com/darqlab/leiturgia/main/scripts/install.sh | sudo bash
```

The script installs dependencies, clones the repo to `/opt/leiturgia`, sets up a Python
virtualenv, seeds an initial program, and starts the `leiturgia` systemd service.

After install, open on any device on the same network:

```
http://<pi-ip>:5000          Operator console
http://<pi-ip>:5000/ch1      Projection channel 1
http://<pi-ip>:5000/remote   Mobile remote
```

> **Default PIN is `1234`** — change it in `/opt/leiturgia/config.json`, then restart:
> ```bash
> sudo systemctl restart leiturgia
> ```

### Debian package (.deb)

Pre-built `.deb` packages for `armhf` are available on the
[Releases](https://github.com/darqlab/leiturgia/releases) page.

```bash
# Download the latest release and install
wget https://github.com/darqlab/leiturgia/releases/latest/download/leiturgia_<version>_armhf.deb
sudo dpkg -i leiturgia_<version>_armhf.deb
```

### Manual setup (development)

```bash
git clone https://github.com/darqlab/leiturgia.git
cd leiturgia
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

---

## Update

Re-run the installer — it detects the existing installation, pulls the latest, reinstalls
dependencies, and restarts the service. Config and data are preserved.

```bash
curl -fsSL https://raw.githubusercontent.com/darqlab/leiturgia/main/scripts/install.sh | sudo bash
```

---

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/darqlab/leiturgia/main/scripts/uninstall.sh | sudo bash
```

The script prompts before removing anything and offers to back up your program data,
media files, and config before deletion.

---

## Service management

```bash
sudo systemctl status leiturgia       # Check status
sudo systemctl restart leiturgia      # Restart
sudo systemctl stop leiturgia         # Stop
journalctl -u leiturgia -f            # Live logs
```

---

## Distribution packaging

Releases are built automatically by the GitHub Actions workflow
(`.github/workflows/release.yml`) when a version tag is pushed:

```bash
git tag v1.2.3
git push origin v1.2.3
```

The workflow builds a `.deb` package (`leiturgia_<version>_armhf.deb`) and publishes it
as a GitHub Release. The package includes all app files, the hymnal database, and the
bundled welcome image. The `postinst` script handles virtualenv setup, directory creation,
program seeding, and service activation on the target Pi.

### Build a package locally

```bash
VERSION=1.2.3
PKG_DIR="leiturgia_${VERSION}_armhf"

mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/opt/leiturgia/data"
mkdir -p "${PKG_DIR}/etc/systemd/system"

cp app.py projection.py timer.py media_manager.py \
   scraper.py hymnal.py claude_helpers.py roles.py rundown.py \
   requirements.txt config.example.json "${PKG_DIR}/opt/leiturgia/"
cp -r templates static "${PKG_DIR}/opt/leiturgia/"
cp data/hymns.db "${PKG_DIR}/opt/leiturgia/data/"
cp packaging/debian/control "${PKG_DIR}/DEBIAN/control"
cp packaging/debian/postinst "${PKG_DIR}/DEBIAN/postinst"
cp packaging/debian/prerm "${PKG_DIR}/DEBIAN/prerm"
cp packaging/leiturgia.service "${PKG_DIR}/etc/systemd/system/leiturgia.service"

sed -i "s/Version: .*/Version: ${VERSION}/" "${PKG_DIR}/DEBIAN/control"
chmod 755 "${PKG_DIR}/DEBIAN/postinst" "${PKG_DIR}/DEBIAN/prerm"

dpkg-deb --build "${PKG_DIR}"
```

---

## Project structure

```
leiturgia/
├── app.py                  # Flask server, routes, Socket.IO handlers
├── projection.py           # Per-channel projection state manager
├── timer.py                # Service timer logic
├── roles.py                # Role assignment logic
├── rundown.py              # Rundown/order-of-service helpers
├── media_manager.py        # Media file enumeration
├── scraper.py              # Hymn lyrics scraper
├── hymnal.py               # SQLite hymnal queries (695 hymns)
├── claude_helpers.py       # Claude API integration (lyric cleaning)
├── requirements.txt
├── config.example.json     # Config template (copy to config.json)
├── deploy.sh               # Staging deploy helper
├── data/
│   ├── hymns.db            # Bundled SDA hymnal database (695 hymns)
│   ├── program.json        # Current program state (seeded on first install)
│   ├── history.json        # Last 6 saved programs
│   ├── projection_state.json
│   └── lyrics/             # Cached hymn lyrics
├── media/
│   ├── images/             # Uploaded images
│   └── videos/             # Uploaded videos
├── output/                 # Generated .pptx and .odp files
├── packaging/
│   ├── leiturgia.service   # systemd unit file
│   └── debian/
│       ├── control         # Package metadata
│       ├── postinst        # Post-install script
│       └── prerm           # Pre-remove script
├── scripts/
│   ├── install.sh          # One-line installer
│   └── uninstall.sh        # Uninstaller with data backup option
├── static/
│   └── socket.io.js
└── templates/
    ├── index.html          # Operator UI
    ├── projection.html     # Projection display
    ├── remote.html         # Mobile remote control
    ├── rundown.html        # Rundown view
    ├── timer_display.html  # Timer display
    ├── announcement.html   # Announcement channel
    ├── login.html          # PIN login page
    └── themes/             # CSS themes (10 themes)
```
