# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git & GitHub

- **Personal account:** `darqlab` (arquillanodennis@gmail.com) — **default** (`github.com`)
- **Work account:** `dennisarq` (darquillano@ssd.org) — use alias `github-work`
- **Remote:** `git@github.com:darqlab/leiturgia.git`
- Global git identity is already set to personal; no per-commit override needed here.

---

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

---

## Documentation

All project documentation lives in `/home/dennis/devops/projects/leiturgia/`.

### Filename Naming Convention

Filenames follow the standard abbreviation patterns below:

| Type | Pattern | Purpose |
|------|---------|---------|
| IA  | `[Module]_Issue_Analysis.md` | Problem/issue analysis |
| RP  | `[Module]_[Feature]_Refactoring_Plan.md` | Refactoring or redesign plan |
| TM  | `[Module]_[Feature]_TM.md` | Task management / checklist |
| QA  | `[Module]_[Feature]_QA_Checklist.md` | Quality assurance checklist |
| ADR | `ADR_[Number]_[Decision].md` | Architecture decision record |
| DG  | `[System]_Deployment_Guide.md` | Deployment guide |
| DEV | `[System]_Developer_Guide_DEV.md` | Developer reference guide |
| TDD | `[Module]_[Feature]_TDD.md` | Technical design document |
| MS  | `[Module]_[Feature]_MS.md` | Module spec / reference |

### Rules

- Use `PascalCase` for module and feature names (e.g., `Generator`, `ServiceProgram`)
- No spaces — use underscores as separators
- Always include the type abbreviation suffix so purpose is clear from the filename

---

## Development Methodology

Every non-trivial change follows this four-step sequence **before any code is written**:

### 1. Plan (`IA` or `RP`)
- Analyse the problem or feature request
- Identify affected files, components, and risks
- Document as an Issue Analysis (`_IA.md`) for bug/investigation work, or a Refactoring Plan (`_RP.md`) for redesign/new features
- Get agreement before proceeding

### 2. Technical Design (`TDD`)
- Write a `_TDD.md` covering: purpose & scope, solution overview, component design, data schema, API contracts, security considerations, and open decisions
- This is **mandatory** for any feature that touches more than one file or introduces a new data type, API endpoint, or UI component
- Save to `/home/dennis/devops/projects/leiturgia/` before implementation starts

### 3. Implementation Plan
- Break the approved TDD into concrete, ordered steps
- List exactly which files change and what each change does
- Use Claude Code's plan mode (`EnterPlanMode`) so the user reviews and approves before implementation starts

### 4. Task Management (`TM`)
- Create a `_TM.md` in `/home/dennis/devops/projects/leiturgia/` to track work
- Each task maps to a step from the implementation plan
- Mark tasks `in_progress` before starting, `completed` when done
- Do not skip ahead — complete and verify each task before moving to the next

### Doc writing rule
**Claude must always write the TDD and TM before writing any code.** If the user approves a plan in conversation without explicitly asking for docs, Claude still creates both documents first. The only exception is a single-file, single-function hotfix with no schema or API changes.
