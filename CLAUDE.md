# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git & GitHub

- **Personal account:** `darqlab` (arquillanodennis@gmail.com) — **default** (`github.com`)
- **Work account:** `dennisarq` (darquillano@ssd.org) — use alias `github-work`
- **Remote:** `git@github.com:darqlab/leiturgia.git`
- Global git identity is already set to personal; no per-commit override needed here.

---

## What this project is

**Leiturgia** is a Flask web app for managing church service programs. It provides a
live-editing UI, real-time projection to external displays via WebSockets, and
PPTX/ODP slide generation. It runs on a Raspberry Pi and is accessible from any
device on the same network.

## Directories

| Path | Role |
|---|---|
| `/home/dennis/Projects/Leiturgia/` | **Source of truth** — all code changes go here, committed to git |
| `/opt/yard/leiturgia/` | **Test deployment** — running instance used for manual testing |

**Workflow:** edit files in `/home/dennis/Projects/Leiturgia/`, sync changed files to `/opt/yard/leiturgia/`, then run and test from there. Never edit `/opt/yard/` directly without syncing back.

### Sync and test

After editing source files, sync them and run tests from the deployment directory:

```bash
# Sync individual files
cp /home/dennis/Projects/Leiturgia/<file> /opt/yard/leiturgia/<file>

# Sync multiple files at once
cp /home/dennis/Projects/Leiturgia/{roles.py,timer.py,app.py} /opt/yard/leiturgia/

# Run verification or ad-hoc tests from the deployment dir
cd /opt/yard/leiturgia && source .venv/bin/activate && python3 -c "..."
```

## Running the app

```bash
# Development (from project root)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
# Operator UI:      http://<host-ip>:5000
# Projection display: http://<host-ip>:5000/ch1

# Test deployment (already running)
# Files at: /opt/yard/leiturgia/
# Logs:     /tmp/leiturgia.log
# Run from: cd /opt/yard/leiturgia && source .venv/bin/activate
```

Program state is persisted in `data/program.json`. Generated slides go to `output/{id}.pptx`.

## Architecture

Key modules:

- **`app.py`** — Flask server + Flask-SocketIO. All HTTP routes and Socket.IO event
  handlers. Defines `DEFAULT_PROGRAM` (canonical schema). Loads/saves `data/program.json`
  and `data/history.json`. The `/api/generate/<id>` route fetches lyrics transiently
  before calling the generators.

- **`generator.py`** — Builds `.pptx` files using python-pptx. Navy/gold theme.
  Slide sequence: title → overview → item slides (with lyric slides injected for songs)
  → closing. `add_text` and `add_rect` are the core layout primitives.

- **`generator_odp.py`** — Mirrors `generator.py` for LibreOffice `.odp` output.

- **`scraper.py`** — Fetches hymn lyrics from `sdahymnals.com` (primary) with fallback
  to `hymnary.org`. Only `fetch_hymn_lyrics()` and `fetch_lyrics_by_title()` are public.

- **`projection.py`** — `ProjectionStateManager`: per-channel in-memory state dict,
  persisted to `data/projection_state.json` for TV reconnect.

- **`timer.py`** — Server-side countdown timer state (start/pause/reset).

- **`media_manager.py`** — Enumerates `data/media/images/` and `data/media/videos/`.

- **`claude_helpers.py`** — Calls the Anthropic API to clean scraped lyric stanzas.
  Fails gracefully if `ANTHROPIC_API_KEY` is not set.

- **`hymnal.py`** — SQLite queries against `data/hymns.db` (695 SDA hymns).

**Frontend** (`templates/index.html`): Single-page Jinja2 template. `collectProgram()`
serialises the DOM into program JSON and POSTs to `/api/program`. Auto-save is debounced
at 800ms. Socket.IO events are emitted via the `socket` global for live projection.

**Projection display** (`templates/projection.html`): Fullscreen page opened on the
TV/projector. Listens for Socket.IO events and renders slides, media, timers, and
announcements. Loads a CSS theme from `templates/themes/` via `applyTheme()`.

## Program data schema

See `data-schemas.md` in the docs folder for the full schema. Summary:

```json
{
  "church": "string",
  "date": "YYYY-MM-DD",
  "service_programs": [
    {
      "id": "sabbath-school",
      "name": "Sabbath School",
      "time": "9:00 a.m.",
      "items": [ { "item_id": "...", "type": "participant|song|content|media", "..." : "..." } ]
    }
  ],
  "service_team": []
}
```

`lyrics` is never stored in `program.json` — fetched transiently at generation time.

## Slide layout (generator.py)

Slide dimensions: 10" × 5.625" (16:9). All coordinates in inches. `add_item_slide`
has detailed vertical-centering math based on item type — take care when modifying.

---

## Documentation

- **Project-level docs** (README, system TDD, architecture, API reference, etc.): `/home/dennis/devops/projects/leiturgia/`
  - See [`README.md`](file:///home/dennis/devops/projects/leiturgia/README.md) for the full index.
- **Feature-specific dev docs** (TDD, TM, RP, IA per feature): `/home/dennis/devops/projects/leiturgia/dev/`

### Directory structure

```
/home/dennis/devops/projects/leiturgia/
├── README.md               Project overview and layout
├── DEVELOPER_GUIDE.md      Start here — onboarding, workflow, conventions
├── CURRENT_STATE.md        What's done, in progress, and pending right now
├── env.example             Required environment variables
├── Leiturgia_System_TDD.md Full system technical design document
├── architecture.md         Component map and data flows
├── data-schemas.md         All JSON data structures
├── api-reference.md        All HTTP routes and Socket.IO events
├── deployment.md           Setup and systemd autostart
├── ref/                    Deep reference docs (modules, slide layout, sheets)
├── dev/                    Planning docs: TDDs, TMs, IPs, analysis (per feature)
└── exports/                Generated output files (.odt, .pdf)
```

### Filename naming convention

| Visibility | Convention | Examples |
|------------|-----------|---------|
| Meta / entry-point docs | `ALL_CAPS.md` | `README.md`, `DEVELOPER_GUIDE.md`, `CURRENT_STATE.md` |
| Reference docs (root) | `kebab-case.md` | `architecture.md`, `data-schemas.md`, `api-reference.md` |
| Feature docs (dev/) | `[Module]_[Feature]_[Type].md` | `Projection_ThemeSystem_TDD.md`, `Program_MediaItem_TM.md` |

#### Type suffixes for `dev/` files

| Type | Pattern | Purpose |
|------|---------|---------|
| IA  | `[Module]_Issue_Analysis.md` | Problem / issue analysis |
| RP  | `[Module]_[Feature]_Refactoring_Plan.md` | Redesign / new feature plan |
| TDD | `[Module]_[Feature]_TDD.md` | Technical design document |
| IP  | `[Module]_[Feature]_IP.md` | Implementation plan (ordered steps) |
| TM  | `[Module]_[Feature]_TM.md` | Task management / checklist |
| QA  | `[Module]_[Feature]_QA_Checklist.md` | Quality assurance checklist |
| MS  | `[Module]_[Feature]_MS.md` | Module spec / reference |
| ADR | `ADR_[Number]_[Decision].md` | Architecture decision record |

#### Rules
- Use `PascalCase` for module and feature names in `dev/` filenames
- No spaces — use underscores as separators within `dev/` filenames
- `CURRENT_STATE.md` must have its `Last updated` date updated on every commit that
  changes feature status, adds a bug fix, or completes a pending item

---

## Development Methodology

Every non-trivial change follows this four-step sequence **before any code is written**:

### 1. Plan (`IA` or `RP`)
- Analyse the problem or feature request
- Identify affected files, components, and risks
- Document as an Issue Analysis (`_IA.md`) for bugs, or a Refactoring Plan (`_RP.md`)
  for new features or redesigns
- Save to `dev/` — get agreement before proceeding

### 2. Technical Design (`TDD`)
- Write a `_TDD.md` covering: purpose & scope, solution overview, component design, data schema, API contracts, security considerations, and open decisions
- This is **mandatory** for any feature that touches more than one file or introduces a new data type, API endpoint, or UI component
- Save to `/home/dennis/devops/projects/leiturgia/dev/` before implementation starts

### 3. Implementation Plan
- Break the approved TDD into concrete, ordered steps
- List exactly which files change and what each change does
- Use Claude Code's plan mode (`EnterPlanMode`) so the plan is reviewed before coding

### 4. Task Management (`TM`)
- Create a `_TM.md` in `/home/dennis/devops/projects/leiturgia/dev/` to track work
- Each task maps to a step from the implementation plan
- Mark tasks `in_progress` before starting, `completed` when done
- Do not skip ahead — complete and verify each task before moving to the next

### Doc writing rule
**Claude must always write the TDD and TM before writing any code.** If the user
approves a plan in conversation without explicitly asking for docs, Claude still
creates both documents first. The only exception is a single-file, single-function
hotfix with no schema or API changes.
