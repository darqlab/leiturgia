# Leiturgia — Slide Design Guide
**Sabbath School Presentation System · v1.0**

---

## Table of Contents

1. [Overview](#1-overview)
2. [Design System](#2-design-system)
3. [Slide Types](#3-slide-types)
4. [Program Item Data Requirements](#4-program-item-data-requirements)
5. [Hymn Lyric Slides](#5-hymn-lyric-slides)
6. [Layout & Positioning](#6-layout--positioning)
7. [How the Generator Works](#7-how-the-generator-works)
8. [Adding or Modifying Slides](#8-adding-or-modifying-slides)

---

## 1. Overview

Leiturgia generates a complete Sabbath School presentation from a single web form. Each week's program produces a self-contained `.pptx` file containing all program slides and hymn lyrics — ready to open in PowerPoint, LibreOffice Impress, or Proclaim.

| Property | Value |
|---|---|
| Slide dimensions | 10 × 5.625 inches (16:9 widescreen) |
| Output format | Microsoft PowerPoint (.pptx) |
| Generator | Python · `python-pptx` library |
| Typical slide count | 12–18 slides depending on hymns |
| Target display | Full HD projection (1920×1080) |

> **Note:** All font sizes are calibrated for comfortable reading from 8–15 metres away in a sanctuary setting.

---

## 2. Design System

### 2.1 Colour Palette

The system uses a **navy and gold** palette — traditional, dignified, and highly legible on projection screens in dimly lit sanctuaries.

| Role | Hex | Usage |
|---|---|---|
| Background | `#0D1B3E` | Primary slide background — deep navy |
| Card Background | `#1A2B5C` | Participant name card backgrounds |
| Dark Background | `#091428` | Header band, title slide accents |
| Gold | `#D4A843` | Separator lines, role labels, dot indicators |
| Gold Light | `#E8C06A` | Subtitles, hymn titles |
| White | `#FFFFFF` | Main titles and primary text |
| Off-White | `#E8EAF0` | Participant names, secondary content |
| Muted | `#8C9AB5` | Supporting text, slide counters |

### 2.2 Typography

Two typefaces are used throughout:

- **Georgia** (serif) — All major titles, section headings, and hymn lyric lines. Communicates tradition and reverence.
- **Calibri** (sans-serif) — Participant names, role labels, subtitles, supporting text. Clean and legible at all sizes.

| Element | Font | Size | Style |
|---|---|---|---|
| Section title (e.g. "Call to Worship") | Georgia | 52pt | Bold, white |
| Participant name (stacked layout) | Calibri | 36pt | Bold, off-white |
| Role label (e.g. WORSHIP LEADER) | Calibri | 20pt | Regular, gold, spaced caps |
| Subtitle / hymn name | Calibri | 24pt | Italic, gold-light |
| Hymn lyric lines | Georgia | 24pt | Regular, white |
| Slide counter | Calibri | 10pt | Regular, muted |

### 2.3 Layout Constants

All measurements are in inches. Origin `(0, 0)` is the top-left corner of the slide.

| Constant | Value |
|---|---|
| Slide width | 10.0" |
| Slide height | 5.625" |
| Vertical midpoint | 2.8125" |
| Gold bottom bar — y position | 5.55" |
| Gold bottom bar — height | 0.075" |
| Standard horizontal padding | 0.5" left/right |

---

## 3. Slide Types

Every presentation contains the following slides in order.

---

### Slide 1 — Title Slide

> Displayed before the program begins.

**Visual elements:**
- Gold horizontal bars on top and bottom edges
- Gold vertical accent bar on the left edge
- Church name in muted small text, top-left
- Section name (e.g. *Sabbath School*) as large 60pt Georgia bold heading
- Gold horizontal rule separator
- Subtitle: *"Worship Program · [Date]"* in gold-light italic
- Scripture reference at the bottom in muted italic

**Data needed:**
- Church name
- Section name
- Date

---

### Slide 2 — Order of Service

> Quick-reference overview of all program items.

**Visual elements:**
- Dark header band with section label on the left and date on the right
- Gold underline separator below header
- "Order of Service" heading in 34pt Georgia
- Each program item displayed as a full-width row
  - Alternating navy / card-blue row shading
  - Gold left pip (vertical accent bar) on each row
  - Item title; subtitle appended if present (e.g. hymn name or scripture)

**Data needed:**
- All program item titles and subtitles

---

### Slides 3–N — Program Item Slides

> One slide per program section. Example: *Prelude & Welcome*, *Call to Worship*, *Opening Prayer*.

**Visual elements:**
- No header band — full slide height used for content
- Section title centred, 52pt Georgia bold, vertically centred on slide
- Gold horizontal rule separator (centred, 3" wide)
- Subtitle in 24pt italic gold-light if provided
- Participants in **stacked layout**: large name above, spaced-caps role label below
- Multiple participants stack vertically with consistent spacing
- Slide counter (e.g. `3 / 6`) bottom-right in muted text
- Gold bottom bar

**Stacked participant layout:**
```
[Participant Name]       ← 36pt Calibri bold, off-white, centred
  ROLE LABEL             ← 20pt Calibri, gold, letter-spaced, centred
```

**Data needed:**
- Item title
- Subtitle (optional)
- Participant name(s) and role(s)

---

### Slides After Opening Hymn — Hymn Lyric Slides

> One slide per verse of the Opening Hymn. See [Section 5](#5-hymn-lyric-slides) for full detail.

---

### Last Slide — Closing Slide

> Displayed at the end of Sabbath School.

**Visual elements:**
- Gold border frame on all four edges (top, bottom, left, right bars)
- Section name centred in 56pt Georgia bold
- Gold rule separator
- *"Ends Here · Divine Service Follows"* in 20pt gold italic
- Church name in 13pt muted text at bottom

**Data needed:**
- Church name
- Section name

---

## 4. Program Item Data Requirements

Each program item slide is driven by data entered in the Leiturgia web UI.

| Item | Participants | Optional Fields |
|---|---|---|
| Prelude & Welcome | Piano Ministry, Welcome Team | — |
| Call to Worship | Worship Leader | — |
| Opening Hymn | Piano, Congregation | Subtitle, Hymn Number |
| Opening Prayer | Prayer Leader | — |
| Scripture Reading | Reader | Subtitle (scripture reference) |
| Special Music | Soloist, Piano Accompaniment | Subtitle (song name) |

### Field Descriptions

| Field | Description |
|---|---|
| **Title** | The program section name shown large on the slide |
| **Subtitle** | Optional supporting text — hymn name, scripture reference, song title |
| **Hymn Number** | SDA Hymnal number — triggers automatic lyric fetch |
| **Participant Name** | The name displayed on screen (use First Name + Last Initial for privacy) |
| **Role** | The participant's role — shown as small spaced-caps label below the name |

> **Privacy note:** The system is designed for *First Name + Last Initial* format (e.g. `Sarah M.`) to comply with GDPR and data minimisation principles.

---

## 5. Hymn Lyric Slides

Hymn slides are generated automatically when a **Hymn Number** is entered for the Opening Hymn item.

### How Lyrics Are Fetched

1. The coordinator enters the hymn number in the web UI (e.g. `73`)
2. Clicking **Fetch Lyrics** calls the `/api/fetch-hymn/{number}` endpoint
3. The scraper queries `sdahymnals.com` for the SDA Hymnal text
4. Lyrics are parsed into stanzas and stored in the program data
5. On generation, one slide is created per stanza

### Lyric Slide Design

**Visual elements:**
- No header — full slide available for lyrics
- 4 lyric lines per slide, centred horizontally and vertically
- Uniform **24pt Georgia** — same size and weight for all lines
- Verse progress indicator dots at the bottom:
  - Gold dot = current verse
  - Muted dot = other verses
- Gold bottom bar

**Line layout:**
```
                    [Line 1 — lyric text]
                    [Line 2 — lyric text]
                    [Line 3 — lyric text]
                    [Line 4 — lyric text]

                         ● ○ ○ ○          ← verse dots
```

### Layout Measurements

| Constant | Value |
|---|---|
| Line height per lyric line | 0.75" |
| Gap between lines | 0.28" |
| Total 4-line block height | 3.84" |
| Block vertical start y | `(5.625 − 3.84) / 2 = 0.8925"` |
| Font size | 24pt Georgia |
| Text box width | 10" (full slide width, no padding) |
| Wrap | Off — lines never wrap |

### Manual Lyrics Entry

If the hymn is not found online, lyrics can be entered manually by editing `data/program.json` directly:

```json
{
  "lyrics": [
    {
      "number": 1,
      "lines": [
        "Holy, Holy, Holy! Lord God Almighty!",
        "Early in the morning our song shall rise to Thee;",
        "Holy, Holy, Holy! Merciful and Mighty!",
        "God in three Persons, Blessèd Trinity!"
      ]
    },
    {
      "number": 2,
      "lines": [
        "Holy, Holy, Holy! All the saints adore Thee,",
        "Casting down their golden crowns around the glassy sea;",
        "Cherubim and seraphim falling down before Thee,",
        "Who wert, and art, and evermore shalt be."
      ]
    }
  ]
}
```

---

## 6. Layout & Positioning

### Vertical Centering of Program Item Slides

Program item slides use a calculated vertical centering algorithm to ensure content always appears visually centred regardless of how many participants are listed.

**Formula:**

```
total_visible_height =
    title_visible_height
  + gap_after_title
  + subtitle_height  (if present)
  + gap_after_subtitle
  + separator_height
  + gap_after_separator
  + participant_block_height

title_box_y = SLIDE_MID - (total_visible_height / 2) - TITLE_PADDING + 0.29
```

The `+ 0.29` is an empirically measured correction for `python-pptx`'s internal text box top padding at 52pt Georgia. Without this, content appears slightly above visual centre.

### Participant Block Height

```
participant_block_height =
    (number_of_participants × STACK_ROW_HEIGHT)
  + (number_of_participants − 1) × STACK_GAP

STACK_ROW_HEIGHT = 1.1"
STACK_GAP        = 0.2"
```

**Example — 2 participants:**
```
participant_block_height = (2 × 1.1) + (1 × 0.2) = 2.4"
```

### Slide Counter Position

The slide counter (`x / total`) is always placed at:
- x: `8.5"`, y: `5.2"`, width: `1.3"`, height: `0.3"`
- 10pt Calibri, muted colour, right-aligned

---

## 7. How the Generator Works

The generator (`generator.py`) is called by the Flask app after saving the program data. Here is the full slide generation sequence:

```
generate_pptx(program, output_path)
│
├── 1. add_title_slide()
├── 2. add_overview_slide()
├── 3. for each item in program.items:
│       └── add_item_slide()
│           └── if item index == 2 (Opening Hymn) and lyrics exist:
│               └── add_hymn_slides()   ← one per stanza
└── 4. add_closing_slide()
```

### Key Files

| File | Purpose |
|---|---|
| `app.py` | Flask web server — routes, API endpoints, file serving |
| `generator.py` | python-pptx slide builder — all slide layout logic |
| `scraper.py` | Hymn lyric fetcher — scrapes sdahymnals.com |
| `templates/index.html` | Web UI — program editor, generate button |
| `data/program.json` | Saved program data — persists between sessions |
| `output/SabbathSchool.pptx` | Generated presentation file |

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI — program editor |
| `GET` | `/api/program` | Returns current program JSON |
| `POST` | `/api/program` | Saves program JSON |
| `POST` | `/api/generate` | Saves + generates the .pptx |
| `GET` | `/api/fetch-hymn/<number>` | Fetches hymn lyrics by number |
| `GET` | `/download` | Downloads the generated .pptx |
| `POST` | `/api/reset` | Resets program to defaults |

---

## 8. Adding or Modifying Slides

### Adding a New Program Item

1. Open the Leiturgia web UI
2. Edit `data/program.json` directly to add a new item, or extend the `DEFAULT_PROGRAM` in `app.py`:

```python
{
  "title": "Testimony",
  "subtitle": "",
  "participants": [
    { "role": "Speaker", "name": "" }
  ]
}
```

3. The new item will automatically appear in the Order of Service and get its own program slide.

### Adding Lyrics for a Different Hymn Position

By default, lyrics are inserted after the **Opening Hymn** (item index 2). To insert lyrics after a different item, edit `generator.py`:

```python
# Change this line in generate_pptx()
if i == 2 and item.get("lyrics"):      # ← change 2 to the correct index
    add_hymn_slides(prs, item["lyrics"])
```

### Changing the Colour Scheme

All colours are defined at the top of `generator.py` in the `C` dictionary:

```python
C = {
    "bg":       RGBColor(0x0D, 0x1B, 0x3E),  # ← change these
    "gold":     RGBColor(0xD4, 0xA8, 0x43),
    ...
}
```

### Changing Font Sizes

Font constants are also at the top of `generator.py`. For the main title size, locate the `add_item_slide()` function and change the `font_size` parameter:

```python
add_text(slide, item["title"], 0, title_box_y, 10, TITLE_BOX,
         font_size=52,   # ← adjust this
         ...)
```

> **Important:** If you change the title font size, you must also recalibrate `TITLE_PAD` (the internal top padding correction) by visually checking the output and adjusting until the content appears centred.

---

*Leiturgia — built for the Sabbath, one slide at a time.*
