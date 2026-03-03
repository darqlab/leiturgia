# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

**Leiturgia** (formerly "Sabbath Program Builder") is a lightweight Flask web app for generating Sabbath School PowerPoint presentations. It runs on a Raspberry Pi and is accessible from any device on the same network.

## Running the app

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
# Accessible at http://<host-ip>:5000
```

The app creates `data/` and `output/` directories on first run. Program state is persisted in `data/program.json`. The generated file is saved to `output/SabbathSchool.pptx`.

## Architecture

Three Python modules with clear separation of concerns:

- **`app.py`** — Flask server. Defines routes and the `DEFAULT_PROGRAM` structure (the canonical schema for program data). Loads/saves `data/program.json`. The `/api/generate` route fetches hymn lyrics for any item with a `hymn_number` before calling `generate_pptx`.

- **`generator.py`** — Builds the `.pptx` file using `python-pptx`. Slide sequence is always: title → overview → one item slide per program item (with hymn lyric slides injected after index 2 if lyrics exist) → closing. All colors are defined in the `C` dict (dark navy/gold theme). `add_text` and `add_rect` are the core primitives used by every slide builder.

- **`scraper.py`** — Fetches hymn lyrics from `sdahymnals.com` (primary) with fallback to `hymnary.org`. `_parse_lyrics_text` splits raw text into stanzas by blank lines. Only `fetch_hymn_lyrics(hymn_number)` and `fetch_program(url)` are public.

**Frontend** (`templates/index.html`): Single-page Jinja2 template with all CSS inline. JavaScript `collectProgram()` serializes the form into the program JSON schema and POSTs to `/api/program`. The date input auto-advances to the next Saturday on page load if no date is set.

## Program data schema

```json
{
  "church": "string",
  "section": "string",
  "date": "YYYY-MM-DD",
  "items": [
    {
      "title": "string",
      "subtitle": "string (optional)",
      "hymn_number": 123,
      "participants": [
        { "role": "string", "name": "string" }
      ],
      "lyrics": [ { "number": 1, "lines": ["..."] } ]
    }
  ]
}
```

`lyrics` is never stored in `program.json` — it's fetched at generation time and added transiently.

## Slide layout constants (generator.py)

Slide dimensions: 10" × 5.625" (16:9). All coordinates use inches. The `add_item_slide` function has detailed layout math to vertically center content based on whether a subtitle and how many participants are present — take care when modifying those calculations.
