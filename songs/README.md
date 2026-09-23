# Contributing a Song

This folder is Leiturgia's **song library** — songs that are *not* in the SDA hymnal
(short choruses, praise songs, seasonal pieces). Hymns already live in the bundled hymnal
databases and must **not** be added here.

Songs ship with the app. Once your song is merged, it reaches every Leiturgia installation
with the next update — the same way the code does. That is the point of this folder.

You do not need to know how to program. A song is one small text file.

---

## 1. Where the file goes

```
songs/<collection>/<song-name>.json
```

- **Put your song in `songs/praise-english/`** if the lyrics are English, or
  `songs/praise-tagalog/` if they are Tagalog. That is the whole rule.
- **One song per file.** Never put two songs in one file.

**The folder is the collection**, and collections appear as separate entries in the app's song
picker so the operator can narrow a long list. **Collections are split by language** —
`praise-english/`, `praise-tagalog/`, and so on. There will never be a collection you have to
make a stylistic judgment about, like "chorus" versus "praise song", because two people would
sort the same song differently and it would then be missing from wherever the other person
looked. Language is not a judgment call.

A translation is a **separate song file** in its own language collection, not extra stanzas
added to the English one. Give it the title it is actually sung under, and set `language` to
match the folder.

**Do not create a new collection yourself.** Ask first — a new language is the only likely
reason to need one. A song's collection becomes part of the reference stored in saved service
programs, so moving a song between collections later breaks every program that used it.

### Naming the file

All lowercase, words joined by hyphens, `.json` at the end. Letters, numbers and hyphens only.

| Song title | File name |
|---|---|
| Alleluia | `alleluia.json` |
| Praise God From Whom All Blessings Flow | `praise-god-from-whom-all-blessings-flow.json` |
| Sa Iyong Tabi | `sa-iyong-tabi.json` |

No spaces, no capital letters, no apostrophes, no accents in the **file name** — accents are
fine inside the file.

---

## 2. Copy a template

- **`_template.json`** — a short chorus. **Use this one unless the song has verses.**
- **`_template-with-verses.json`** — a song with verses and a chorus.

Files beginning with `_` are templates and are ignored by the app.

## 3. Fill it in

```json
{
  "schema": 1,
  "title": "Alleluia",
  "language": "en",
  "author": "Traditional",
  "copyright": "Public Domain",
  "ccli": "",
  "stanzas": [
    {
      "number": 1,
      "type": "chorus",
      "lines": [
        "Alleluia, alleluia",
        "Alleluia, alleluia"
      ]
    }
  ]
}
```

| Field | Required | What it is |
|---|:--:|---|
| `schema` | ✅ | Always `1`. Do not change it. |
| `title` | ✅ | Exactly as it should appear on the title slide. |
| `stanzas` | ✅ | The lyrics. See below. |
| `language` | | `en` (English), `tl` (Tagalog), `ceb`, `ilo`. Defaults to `en`. |
| `author` | | Writer or composer. `"Traditional"` if unknown. |
| `copyright` | ✅ | See §5. Must not be empty. |
| `ccli` | | CCLI song number if you know it, otherwise `""`. |

### Stanzas

Each stanza is one block of lyrics:

```json
{ "number": 1, "type": "chorus", "lines": ["Line one", "Line two"] }
```

- **`type`** — one of `verse`, `chorus`, `refrain`, `bridge`. Nothing else.
- **`number`** — verses count up `1, 2, 3…`. A chorus is normally `1`.
- **`lines`** — one entry per line **as it should appear on the slide**.

---

## 4. The five rules that matter

**1. A short chorus is one stanza. That is a complete, valid song.**
Most songs here are a single chorus. You do not need verses, and you do not need to pad it.

**2. Write the chorus ONCE.**
If the song has verses, put the chorus in the file a single time. The app repeats it after
every verse automatically. Writing it out after each verse makes it appear **twice in a row**
during the service.

**3. One line per projected line — keep stanzas to 5 lines or fewer.**
Each entry in `lines` is one line on the screen. A stanza longer than 5 lines is split
across two slides automatically, and the split may land somewhere awkward. Break it into
two stanzas yourself instead, so you control where the slide changes.

**4. Do not include labels in the lyrics.**
No `Verse 1:`, no `Chorus:`, no `(x2)`, no chord names. Those would be projected literally.
If a chorus is sung twice and you want it shown twice, add the stanza a second time.

**5. Type the words, don't paste formatting.**
No blank-line entries, no trailing spaces, no `\n` inside a line. Accented and non-English
characters (á, ñ, ü) are fine — write them normally, not as escape codes.

---

## 5. Copyright — read this before you submit

**This repository is public.** Anything merged here is published to the open internet.

A church's CCLI licence covers *projecting* lyrics during worship. It does **not** cover
publishing the lyrics publicly, which is what merging your file does. These are different
things, and this is the single most common reason a song submission is rejected.

**Current policy: public domain only.** Set `"copyright": "Public Domain"` and only submit
songs where that is actually true — generally traditional material, or anything published
before 1929. If you are not certain a song is public domain, **ask before opening a pull
request** rather than submitting and hoping.

For in-copyright songs your church is licensed to project, add them to your own installation
locally instead of submitting them here.

---

## 6. Check your work

Before opening a pull request:

- [ ] File is in the right collection folder, named in `lowercase-with-hyphens.json`
- [ ] It is one song, not several
- [ ] `title`, `stanzas` and `copyright` are all filled in
- [ ] Every `type` is `verse`, `chorus`, `refrain` or `bridge`
- [ ] The chorus appears **once**
- [ ] No stanza is longer than 5 lines
- [ ] No `Verse 1:` / `Chorus:` / `(x2)` labels in the lyrics
- [ ] The song is public domain, and `copyright` says so
- [ ] The lyrics are correct — read them once more against a reliable source

If your editor shows an error or a red squiggle in the file, the JSON is malformed — usually
a missing comma or a missing `"`. Fix it before submitting; the app cannot read a broken file.

---

## 7. What the review looks at

This document is the reference. Review asks two questions:

1. **Is it in the right format?** — the checklist above. Most of this is checked automatically.
2. **Is it correct?** — are these the right lyrics, in the right collection, and is the
   copyright status acceptable? That part is read by a human.

A formatting problem will be pointed out and is easy to fix. Do not be discouraged by one.
