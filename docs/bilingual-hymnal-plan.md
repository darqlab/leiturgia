# Multi-Language Hymnal — Design & Implementation Plan

**Status:** Planning complete — not yet implemented.
**Date:** 2026-06-02
**Scope:** Add non-English hymnals to Leiturgia. Tagalog is first; the architecture is extensible so adding Cebuano, Ilocano, or any future language requires only a new DB file and a new source file — no app code changes.

---

## 1. Background — the data sources

| Source | What it is | Used by app? | Git-tracked? |
|--------|------------|--------------|--------------|
| `data/hymns.db` | The **live English hymnal** — 695 hymns (+ worship aids to 920 via `Sections`). Read only by `hymnal.py`. To be renamed `hymns_en.db`. | Yes | Yes |
| `data/hymns.json` | A **separate, self-contained bilingual collection** — 474 entries = 237 English, each followed by its Tagalog translation. | No | No |

**Critical fact:** the JSON and the DB are *different books with unrelated numbering.*
Example: "O Worship the Lord" is **#6** in `hymns_en.db` but **#1** in the JSON.
Because of this, automated title-matching between them is unreliable (~174/237), so we do **not** try to pair across the two books.

### Current Tagalog JSON structure
- Each hymn: `{ number, title, verses: [{label, text}], category }`.
- Verse labels seen: `1`–`6`, `CHORUS` / `KORO` (refrain), `LAST CHORUS` / `HULING KORO` (second refrain), and `''` (empty — single-stanza responses).
- Max 6 verses per hymn.
- EN→TL adjacency reliable: **228/237** pairs match on category *and* verse count.

### Future language source files — expect different formats

Each new language source (Cebuano, Ilocano, etc.) will likely arrive in a **different format** — different JSON structure, different field names, CSV, or another layout entirely. The converter script (`build_hymns_lang.py`) must therefore support a **parser-per-source-format** approach:

- A shared core handles classification, renumbering, column mapping, and DB creation.
- A pluggable parser normalises the source file into the common internal format before the core runs.
- When a new source arrives, only a new parser is written — the core and the app are untouched.

Place all source files in `hymns_tools/sources/` for organisation.

> Note: the `sqlite3` CLI (v3.37.2) is installed; Python's `sqlite3` module is also available for DB work.

---

## 2. Decisions

1. **Independent single-language hymnals**, each with its **own numbering**.
   The operator selects a language and browses that hymnal by its own numbers.
   **No cross-language pairing / cross-reference table.**

2. **English** = `data/hymns_en.db` (renamed from `hymns.db`).
   **Each other language** = `data/hymns_<code>.db`, built by the converter.

3. **Every language DB is a schema clone of `hymns_en.db`** — identical `Hymns` table
   (`verse1`–`verse8`, `refrain`, `refrain2`, `section`, `subsection`) plus a `Sections` table.
   The projection / slide engine (`generator.py`, `_row_to_stanzas`) works **unchanged** for all languages.

4. **Identity = composite key (`lang` + `number`)**, true per-language `1..N`.
   `hymn_number` alone is the identity used by the lyrics cache, saved order-of-service items, and projection,
   so `lang` must travel alongside `number` everywhere it is stored or fetched.

5. **Cache filenames: `<lang>-<n>.json`** (e.g. `en-5.json`, `tl-5.json`, `ceb-5.json`).
   Consistent for all languages; works for any future addition without code change.

6. **Frontend language selector** (not a hardcoded EN/TL toggle).
   Populated from `/api/hymnal/languages` which scans for `data/hymns_*.db` files.
   Adding a new DB automatically adds it to the selector — no UI code change.

7. **Projection side unchanged** — bare `#number` as today; no language tag in the payload.

8. **Generic converter `build_hymns_lang.py`** with pluggable source parsers.
   One script for all languages; each new source format gets a parser, not a new script.

---

## 3. File rename

`data/hymns.db` → `data/hymns_en.db`

Touch points:
- `hymnal.py:15` — `DB_PATH` constant → replaced by `_db_path(lang)` helper (see §5.1).
- `hymns_tools/` scripts that reference `hymns.db` directly — update paths.
- `/opt/yard/leiturgia/data/` staging directory — rename on next sync.

Git: `git mv data/hymns.db data/hymns_en.db`

---

## 4. Conversion: source file → `data/hymns_<lang>.db`

Script: `hymns_tools/build_hymns_lang.py`
Sources dir: `hymns_tools/sources/`

Usage:
```bash
# Dry-run
python3 build_hymns_lang.py --lang tl --json sources/hymns.json --out ../Leiturgia/data/hymns_tl.db

# Write DB
python3 build_hymns_lang.py --lang tl --json sources/hymns.json --out ../Leiturgia/data/hymns_tl.db --apply
```

**Steps (same for every language):**
1. Select parser based on source format (auto-detect or `--format` flag).
2. Parse source → normalised list of `{ title, verses, category }` for the target language.
3. Renumber `1..N` in source order.
4. Map verse labels → DB columns:
   - `1`–`6` → `verse1`–`verse6`
   - `CHORUS` / `KORO` → `refrain`
   - `LAST CHORUS` / `HULING KORO` → `refrain2`
   - `''` (empty) → `verse1`
5. Build `Sections` table from distinct categories in order; compute `FirstHymn`/`LastHymn`.
6. Create `hymns_<lang>.db` with identical schema to `hymns_en.db`.
7. Print flagged entries report for human review.

### Adding a new language (future reference)

1. Place source file in `hymns_tools/sources/`.
2. Write a parser if the format is new (one Python function / class).
3. Run the converter dry-run, review output.
4. Run with `--apply`, add DB to git, sync to staging.
5. Language appears in the operator selector automatically.

### Tagalog — entries flagged for human review (~28)

These cluster in the **Responses/Sentences** section (#455–470) where EN→TL alternation is irregular.

**A) Adjacency irregularities (12):**

| JSON # | Lang | Title |
|--------|------|-------|
| 17  | EN | Lord, in the Morning |
| 20  | TL | Napakasaya't Kay-inam |
| 141 | EN | Holy Spirit, Light Divine |
| 144 | TL | O Banal na Espiritu |
| 199 | EN | O, for a Closer Walk! |
| 202 | TL | Sasarilinin Ba Niya? |
| 235 | EN | Blest Be the Tie That Binds |
| 238 | TL | Bata'y Aming Alay |
| 267 | EN | Welcome, Welcome, Day of Rest |
| 270 | TL | Sanlinggo na Nama'y Nanaw |
| 463 | EN | Hear Our Prayer, O Lord |
| 466 | TL | Ang Ama ay Papurihan |

**B) Empty-label verses (16) — single-stanza responses, map to `verse1`:**

| JSON # | Lang | Title |
|--------|------|-------|
| 455 | EN | Cast Thy Burden Upon the Lord |
| 456 | TL | Sa Panginoon Ilagay |
| 457 | EN | O Thou Who Hearest |
| 458 | TL | Ikaw na Dumirinig ng Hibik |
| 459 | EN | The Lord Bless You |
| 460 | TL | Kayo Nawa'y Ingatan at Pagpalain ng Panginoon |
| 461 | EN | As We Come To You In Prayer |
| 462 | TL | Kami'y Lumalapit sa Iyo |
| 463 | EN | Hear Our Prayer, O Lord |
| 464 | EN | Praise God, From Whom All Blessings |
| 465 | TL | Dinggin, Pangino'n, ang Panalangin |
| 466 | TL | Ang Ama ay Papurihan |
| 467 | EN | Dismiss Us, Lord, With Blessings |
| 468 | TL | Panginoon, 'Yong Pagpalain |
| 469 | EN | The Lord is in His Holy Temple |
| 470 | TL | Ang Panginoo'y Nasa Templo |

---

## 5. Application changes (`lang` flow)

### 5.1 Data layer — `hymnal.py`
- Replace `DB_PATH` with `_db_path(lang)` → `f"data/hymns_{lang}.db"`. Works for any language code.
- Add `lang="en"` parameter to: `get_by_number`, `get_by_title`, `search_titles`, `search_by_number_prefix`.
- Default `"en"` keeps every existing caller working. No changes needed when a new language is added.

### 5.2 Lyrics cache — `app.py`
- Cache key: `<lang>-<n>.json` for all languages. (`en-5.json`, `tl-5.json`, `ceb-5.json`, …)
- `_load_lyrics` stores `lang` in the cached JSON.

### 5.3 API routes — `app.py`
- `/api/hymnal/search`, `/api/fetch-hymn/<int:number>`, `/api/fetch-lyrics` accept `lang`; results carry `lang`.
- `/api/lyrics/<key>` unchanged — key-based, prefix flows through naturally.
- New: `GET /api/hymnal/languages` — scans `data/hymns_*.db`, returns available language list. No code change when a new DB is added.

### 5.4 Order-of-service items
- Item schema gains `hymn_lang` (default `"en"` → old saved services stay valid).
- Serialize in public-item block (~`app.py:134–140`).
- Use in lyrics-resolution block (~`app.py:268–278`) to pick the correct DB and cache key.

### 5.5 Frontend — `templates/index.html`
- **Language selector** near the hymn search box, populated from `/api/hymnal/languages`.
- Append `&lang=<selected>` to search (~L3619) and fetch-hymn (~L3431) calls.
- Hidden `.item-hymn-lang` input per item, persisted on add/update (~L2395–2457, ~L4281–4322).
- No code change when a new language is added — selector renders from the API response.

### 5.6 No change needed
- `generator.py` — operates on stanzas; language-agnostic.
- `templates/projection.html` — bare `#number` as today; no language tag.

---

## 6. Build / sync notes
- `git mv data/hymns.db data/hymns_en.db` and rename in staging.
- Each language DB must be git-tracked and synced via the standard `git ls-files | rsync` flow.
- Per project convention, the implementation (rename + converter + multi-file app changes) is handed to a `general-purpose` agent once this plan is approved.

---

## 7. Open items before build
1. Review the ~28 flagged Tagalog entries in §4 above.
2. Decide branch name for this feature.
