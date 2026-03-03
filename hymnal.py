"""
hymnal.py — Query the SDA Hymnal SQLite database (695 hymns).

DB schema (Hymns table):
  _id, number, title, refrain, refrain2,
  verse1 … verse7, section, subsection

Returns stanzas as: [{"number": N, "type": "verse"|"refrain", "lines": [...]}]
The refrain appears once; _hymn_slide_sequence() in generator.py handles interleaving.
"""
import sqlite3
import os
import re

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "hymns.db")
VERSE_COLS = ["verse1", "verse2", "verse3", "verse4", "verse5", "verse6", "verse7"]


def _row_to_stanzas(row: sqlite3.Row) -> list[dict]:
    """Convert a DB row into our stanza list format."""
    stanzas = []

    # Verses
    for i, col in enumerate(VERSE_COLS, start=1):
        text = row[col]
        if not text:
            continue
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        stanzas.append({"number": i, "type": "verse", "lines": lines})

    # Refrain(s) — stored once, interleaved by the generator
    for i, col in enumerate(["refrain", "refrain2"], start=1):
        text = row[col]
        if not text:
            continue
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        stanzas.append({"number": i, "type": "refrain", "lines": lines})

    return stanzas


def _connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def get_by_number(number: int) -> dict | None:
    """
    Fetch a hymn by its number (1–695).
    Returns {"number": N, "title": "...", "stanzas": [...]} or None.
    """
    with _connect() as con:
        row = con.execute(
            "SELECT * FROM Hymns WHERE number = ?", (number,)
        ).fetchone()
    if not row:
        return None
    return {"number": row["number"], "title": row["title"],
            "stanzas": _row_to_stanzas(row)}


def get_by_title(title: str) -> dict | None:
    """
    Search hymns by title using progressively looser matching:
      1. Exact (case-insensitive)
      2. Starts-with
      3. Contains all words
      4. Contains any word (picks closest by word-overlap score)
    Returns the best match or None.
    """
    q = title.strip().lower()
    with _connect() as con:
        rows = con.execute("SELECT * FROM Hymns ORDER BY number").fetchall()

    # Score each hymn title against the query
    def score(row):
        t = row["title"].lower()
        if t == q:
            return 100
        if t.startswith(q):
            return 80
        words = re.findall(r'\w+', q)
        if all(w in t for w in words):
            return 60
        matched = sum(1 for w in words if w in t)
        return matched / max(len(words), 1) * 40

    best = max(rows, key=score)
    if score(best) < 1:
        return None
    return {"number": best["number"], "title": best["title"],
            "stanzas": _row_to_stanzas(best)}


def search_titles(query: str, limit: int = 10) -> list[dict]:
    """
    Return up to `limit` hymns whose title contains the query string.
    Each result: {"number": N, "title": "..."}
    """
    q = f"%{query.strip()}%"
    with _connect() as con:
        rows = con.execute(
            "SELECT number, title FROM Hymns WHERE LOWER(title) LIKE LOWER(?) ORDER BY number LIMIT ?",
            (q, limit)
        ).fetchall()
    return [{"number": r["number"], "title": r["title"]} for r in rows]
