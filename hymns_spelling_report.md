# Hymns Spelling & Formatting Analysis Report

**Scope:** Hymns 1–50 in `data/hymns.db`  
**Fields checked:** title, refrain, refrain2, verse1–verse7  
**Total hymns checked:** 50  
**Date:** 2026-05-17  
**Status:** Read-only — no database changes made

---

## Summary

| Category | Count |
|---|---|
| Confirmed typos / spelling errors | 5 |
| Formatting / encoding issues | 2 |
| British English spellings (not errors) | 2 fields across 1 hymn |
| Archaic -eth / -est verb forms (intentional) | ~12 instances across 7 hymns |
| Poetic contractions (intentional) | ~15 instances across 8 hymns |
| Valid compound / archaic words | ~6 instances across 6 hymns |

---

## Section 1 — Confirmed Errors (Action Required)

### Hymn 22 — "God Is Our Song" | verse1
**Error:** `widom` (appears **twice** in the same verse)  
**Should be:** `wisdom`

```
Give back to us the widom we destroy,
Give back to us the widom we destroy.
```
→ Repeated duplicate line with the same typo. Fix both occurrences.

---

### Hymn 34 — "Wake the Song" | verse1
**Error:** `Bannish` (double 'n')  
**Should be:** `Banish`

```
Bannish every thought of sadness,
```

---

### Hymn 49 — "Savior, Breathe an Evening Blessing" | verse4
**Error:** `o're` (apostrophe in wrong position)  
**Should be:** `o'er` (standard poetic contraction of "over")

```
Should swift death this night o're-take us,
```

---

### Hymn 38 — "Arise, My Soul, Arise!" | verse2
**Error 1:** `amenResound` — missing line break or space between "amen" and "Resound"  
**Should be:** `amen\nResound` (two separate lines)

```
And let the great amenResound through heav'n again.
```
→ Should read as two lines:
```
And let the great Amen
Resound through heav'n again.
```

**Error 2:** `ever lasting` — split compound word  
**Should be:** `everlasting`

```
To Him be ever lasting pow'r and victory.
```

---

## Section 2 — Formatting Issues (Minor)

### Hymn 18 — "O Morning Star, How Fair and Bright" | verse2
**Issue:** `heav-'nly` uses a hyphen before the apostrophe, making the token `'nly` appear as a truncated word.  
**Should be:** `heav'nly` (no hyphen)

```
Refresh our souls with heav-'nly food.
```

---

## Section 3 — British English Spellings (Not Errors)

These are correct British/Commonwealth spellings. Flag only if the project targets a US-English standard.

| Hymn | Field | Word | US Equivalent |
|---|---|---|---|
| 3 — "God Himself Is With Us" | verse2 | `honour` | honor |
| 3 — "God Himself Is With Us" | verse3 | `endeavour` | endeavor |

---

## Section 4 — Archaic Verb Forms (Intentional — Not Errors)

These are archaic English third-person singular present endings (`-eth`, `-est`) standard in traditional hymnody. They are **not** spelling errors.

| Hymn | Field | Word |
|---|---|---|
| 1 — "Praise to the Lord" | verse2 | `Shieldeth`, `sustaineth`, `ordaineth` |
| 5 — "All My Hope on God is Founded" | verse2 | `buildeth` |
| 5 — "All My Hope on God is Founded" | verse3 | `endureth`, `springeth` |
| 21 — "Immortal, Invisible, God Only Wise" | verse2 | `Unresting`, `unhasting`, `rulest` |
| 21 — "Immortal, Invisible, God Only Wise" | verse3 | `givest` |
| 21 — "Immortal, Invisible, God Only Wise" | verse3 | `changeth` |
| 21 — "Immortal, Invisible, God Only Wise" | verse4 | `hideth` |
| 29 — "Sing Praise to God" | verse2 | `sleepeth` |
| 49 — "Savior, Breathe an Evening Blessing" | verse2 | `Watchest` |
| 50 — "Abide With Me" | verse2 | `changest` |

---

## Section 5 — Poetic Contractions (Intentional — Not Errors)

Contracted syllables are a standard literary device in hymnody used to preserve meter.

| Hymn | Field | Contraction | Full Form |
|---|---|---|---|
| 12 — "Joyful, Joyful, We Adore Thee" | verse1 | `flow'rs` | flowers |
| 12 — "Joyful, Joyful, We Adore Thee" | verse2 | `heav'n` | heaven |
| 12 — "Joyful, Joyful, We Adore Thee" | verse2 | `Bloss'ming` | Blossoming |
| 31 — "Tell Out, My Soul" | verse3 | `Pow'rs` | Powers |
| 37 — "O Sing, My Soul, Your Maker's Praise" | verse1, verse3 | `heav'nly` | heavenly |
| 38 — "Arise, My Soul, Arise!" | verse2 | `heav'n`, `giv'n`, `pow'r` | heaven, given, power |
| 42 — "Now That the Daylight Fills the Sky" | verse3 | `vict'ry` | victory |
| 45 — "Open Now Thy Gates of Beauty" | verse1 | `bless'd` | blessed |
| 45 — "Open Now Thy Gates of Beauty" | verse2 | `heav'n` | heaven |
| 45 — "Open Now Thy Gates of Beauty" | verse4 | `Howsoe'er` | Howsoever |
| 47 — "God, Who Made the Earth and Heaven" | verse2 | `pow'r` | power |

---

## Section 6 — Valid Compound / Archaic Words (Not Errors)

The spell-checker flagged these but they are legitimate words.

| Hymn | Field | Word | Notes |
|---|---|---|---|
| 20 — "O Praise Ye the Lord" | verse4 | `outpoured` | valid compound verb |
| 21 — "Immortal, Invisible, God Only Wise" | verse2 | `Unresting`, `unhasting` | coined theological adjectives; original Watts text |
| 23 — "Now the Joyful Bells A-Ringing" | verse3 | `abearing` | archaic participial form, intentional |
| 38 — "Arise, My Soul, Arise!" | verse2 | `neverending` | valid compound |
| 41 — "O Splendor of God's Glory Bright" | verse3 | `unshadowed` | valid compound adjective |
| 44 — "Morning Has Broken" | verse2 | `dewfall` | valid compound noun |

---

## Action Summary

| Priority | Hymn | Field | Fix |
|---|---|---|---|
| High | 22 | verse1 | `widom` × 2 → `wisdom` |
| High | 34 | verse1 | `Bannish` → `Banish` |
| High | 38 | verse2 | `amenResound` → `Amen\nResound` (add line break) |
| High | 38 | verse2 | `ever lasting` → `everlasting` |
| Medium | 49 | verse4 | `o're` → `o'er` |
| Low | 18 | verse2 | `heav-'nly` → `heav'nly` (remove hyphen) |
