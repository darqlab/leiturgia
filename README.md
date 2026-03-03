# Sabbath Program Builder

A lightweight Flask web app for generating Sabbath School PowerPoint presentations.
Designed to run on a Raspberry Pi — accessible from any device on the same network.

## Setup

```bash
# 1. Clone / copy this folder to your Raspberry Pi

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python app.py
```

Then open a browser on any device on the same network:
```
http://<raspberry-pi-ip>:5000
```

## Auto-start on boot (optional)

Add to crontab (`crontab -e`):
```
@reboot cd /home/pi/sabbath_app && python app.py &
```

## Weekly auto-generate (optional)

Add to crontab to auto-generate every Saturday at 7 AM:
```
0 7 * * 6 cd /home/pi/sabbath_app && python -c "from generator import generate_pptx; from app import load_program; generate_pptx(load_program(), 'output/SabbathSchool.pptx')"
```

## Project structure

```
sabbath_app/
├── app.py          # Flask web server
├── generator.py    # python-pptx slide builder
├── scraper.py      # hymn lyrics scraper
├── requirements.txt
├── templates/
│   └── index.html  # Web UI
├── data/
│   └── program.json  # saved program data
└── output/
    └── SabbathSchool.pptx  # generated file
```
