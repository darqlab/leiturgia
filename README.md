# Leiturgia

A Flask web app for managing church service programs — live editing, real-time projection
to external displays, and PowerPoint/LibreOffice slide generation. Runs on a Raspberry Pi
and is accessible from any device on the same network.

---

## Features

- **Program editor** — build and edit multi-program service orders (Sabbath School, Divine Service, AY, etc.)
- **Live projection** — send slides, songs, media, announcements, and timers to a projector/TV in real time via WebSockets
- **Slide generation** — export programs as `.pptx` (PowerPoint) or `.odp` (LibreOffice) files
- **Hymn lyrics** — fetch and cache lyrics by hymn number or title; offline SQLite fallback (695 hymns)
- **10 projection themes** — switchable color themes for the projection display
- **Media support** — upload images/videos or paste URLs; send directly to projection
- **Program history** — rolling view of the last 6 saved programs

---

## Setup

```bash
# 1. Clone this repo onto your Raspberry Pi

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py
```

Open the operator UI on any device on the same network:
```
http://<raspberry-pi-ip>:5000
```

Open a projection channel on the TV/projector browser:
```
http://<raspberry-pi-ip>:5000/ch1
```

Channels `/ch1` through `/ch5` are available for multi-display setups.

---

## Auto-start on boot (systemd)

Create `/etc/systemd/system/leiturgia.service`:

```ini
[Unit]
Description=Leiturgia Church Program App
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/home/<your-user>/MyProjects/Leiturgia
ExecStart=/home/<your-user>/MyProjects/Leiturgia/.venv/bin/python3 app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable leiturgia
sudo systemctl start leiturgia
```

Useful commands:

```bash
sudo systemctl status leiturgia     # check status
sudo systemctl restart leiturgia    # restart after code changes
sudo journalctl -u leiturgia -f     # follow logs
```

---

## Project structure

```
leiturgia/
├── app.py                  # Flask server, routes, Socket.IO handlers
├── generator.py            # PPTX slide builder (python-pptx)
├── generator_odp.py        # ODP slide builder (odfpy)
├── projection.py           # Per-channel projection state manager
├── timer.py                # Service timer logic
├── media_manager.py        # Media file management helpers
├── scraper.py              # Hymn lyrics scraper
├── hymnal.py               # SQLite hymnal queries (695 hymns)
├── claude_helpers.py       # Claude API integration (lyric cleaning)
├── requirements.txt
├── data/
│   ├── program.json        # Current program state
│   ├── history.json        # Last 6 saved programs
│   ├── projection_state.json # Per-channel state (for TV reconnect)
│   ├── hymns.db            # Local SDA hymnal database
│   ├── lyrics/             # Cached hymn lyrics (one JSON per song)
│   └── media/              # Uploaded images and videos
├── output/                 # Generated .pptx and .odp files
├── static/
│   └── socket.io.js        # Socket.IO client library
└── templates/
    ├── index.html          # Operator UI (single-page)
    ├── projection.html     # Projection display page
    └── themes/             # CSS themes: default, midnight, dawn, forest,
                            #   slate, ivory, ocean, ember, pearl, royal
```
