# Leiturgia

A lightweight Flask web app for generating Sabbath School PowerPoint presentations.
Designed to run on a Raspberry Pi — accessible from any device on the same network.

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

Then open a browser on any device on the same network:
```
http://<raspberry-pi-ip>:5000
```

## Auto-start on boot (systemd)

The recommended way to run Leiturgia persistently is via a systemd service.

Create `/etc/systemd/system/leiturgia.service`:

```ini
[Unit]
Description=Leiturgia Sabbath Program Builder
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/opt/yard/leiturgia
ExecStart=/opt/yard/leiturgia/.venv/bin/python3 app.py
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
sudo systemctl status leiturgia    # check status
sudo systemctl restart leiturgia   # restart after code changes
sudo journalctl -u leiturgia -f    # follow logs
```

## Project structure

```
leiturgia/
├── app.py              # Flask web server
├── generator.py        # python-pptx slide builder
├── generator_odp.py    # LibreOffice ODP slide builder
├── scraper.py          # hymn lyrics scraper
├── hymnal.py           # local hymnal index
├── claude_helpers.py   # AI-assisted utilities
├── requirements.txt
├── templates/
│   └── index.html      # Web UI
├── data/
│   ├── program.json    # saved program state
│   └── lyrics/         # cached hymn lyrics
└── output/             # generated presentation files
```
