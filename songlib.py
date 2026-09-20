"""
songlib.py — Song library stored as plain JSON files under songs/<collection>/<slug>.json.

Discovery is glob-at-call-time, no persistent index: staleness matters more than speed here,
since the premise of the feature is that files are hand-edited and `git pull`ed onto a running
box. A metadata memo (title, language only) keyed by (path, mtime_ns, size) is used for search so
repeated listings don't re-parse every file; it self-invalidates on any edit. Full song loads
(get_song) are never cached.

Song file shape: {"schema":1,"title":str,"language":str,"author":str,"copyright":str,"ccli":str,
"stanzas":[{"number":int,"type":"verse"|"chorus"|"refrain"|"bridge","lines":[str,...]}]}
Only "title" and "stanzas" are required.
"""
import glob
import hashlib
import json
import logging
import os
import re
import unicodedata

from jsonio import atomic_write_json

logger = logging.getLogger('leiturgia.songlib')

SONGS_DIR = os.path.join(os.path.dirname(__file__), "songs")

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Metadata memo: {(path, mtime_ns, size): {"title": ..., "language": ...}}
_meta_cache: dict = {}


def _is_hidden(basename: str) -> bool:
    return basename.startswith(".") or basename.startswith(".tmp-")


def _collection_dirs() -> list[str]:
    if not os.path.isdir(SONGS_DIR):
        return []
    return sorted(
        d for d in os.listdir(SONGS_DIR)
        if not _is_hidden(d) and os.path.isdir(os.path.join(SONGS_DIR, d))
    )


def _song_paths(collection: str) -> list[str]:
    pattern = os.path.join(SONGS_DIR, collection, "*.json")
    return sorted(
        p for p in glob.glob(pattern)
        if not _is_hidden(os.path.basename(p))
    )


def _load_meta(path: str) -> dict | None:
    """Return {"title","language"} for a song file, memoized by (path, mtime_ns, size)."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    cache_key = (path, st.st_mtime_ns, st.st_size)
    cached = _meta_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        logger.warning("songlib: failed to read/parse %s", path, exc_info=True)
        return None

    meta = {
        "title": data.get("title") or os.path.splitext(os.path.basename(path))[0],
        "language": data.get("language") or "en",
    }
    # Keep the memo from growing unbounded across stale keys for the same path.
    for k in [k for k in _meta_cache if k[0] == path and k != cache_key]:
        del _meta_cache[k]
    _meta_cache[cache_key] = meta
    return meta


def list_collections() -> list[dict]:
    """Return [{"slug","name","count"}] for each directory under songs/."""
    result = []
    for slug in _collection_dirs():
        count = len(_song_paths(slug))
        result.append({"slug": slug, "name": slug.title(), "count": count})
    return result


def list_songs(collection: str | None = None) -> list[dict]:
    """Return [{"collection","slug","title","language"}] across one or all collections."""
    collections = [collection] if collection else _collection_dirs()
    rows = []
    for c in collections:
        for path in _song_paths(c):
            meta = _load_meta(path)
            if meta is None:
                continue
            slug = os.path.splitext(os.path.basename(path))[0]
            rows.append({
                "collection": c,
                "slug": slug,
                "title": meta["title"],
                "language": meta["language"],
            })
    return rows


def search_titles(query: str, limit: int = 10, collection: str | None = None) -> list[dict]:
    """Case-insensitive substring match on title, capped by limit. Rows include a 'key'."""
    q = (query or "").strip().lower()
    if not q:
        return []
    rows = []
    for row in list_songs(collection=collection):
        if q in row["title"].lower():
            rows.append({**row, "key": f"lib:{row['collection']}:{row['slug']}"})
            if len(rows) >= limit:
                break
    return rows


def _safe_path(collection: str, slug: str) -> str | None:
    """Reject anything that isn't a bare slug before it can become a path component."""
    if not _SLUG_RE.match(collection or "") or not _SLUG_RE.match(slug or ""):
        return None
    return os.path.join(SONGS_DIR, collection, f"{slug}.json")


def get_song(collection: str, slug: str) -> dict | None:
    """Full song dict, or None if missing/malformed. Never cached, never raises."""
    path = _safe_path(collection, slug)
    if path is None:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        logger.warning("songlib: malformed song file %s", path, exc_info=True)
        return None

    if not isinstance(data, dict) or "title" not in data or "stanzas" not in data:
        logger.warning("songlib: song file missing required keys %s", path)
        return None

    return data


def save_song(collection: str, slug: str, data: dict) -> str:
    """Write a song file via atomic_write_json, creating the collection dir if needed."""
    path = _safe_path(collection, slug)
    if path is None:
        raise ValueError(f"invalid collection/slug: {collection!r}/{slug!r}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    atomic_write_json(path, data)
    return path


def slugify(title: str, existing=None) -> str:
    """NFKD-normalize, strip to [a-z0-9-], collapse/trim dashes; suffix -2/-3 vs `existing`."""
    normalized = unicodedata.normalize("NFKD", title or "")
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    if not slug:
        slug = hashlib.sha1((title or "").encode("utf-8")).hexdigest()[:8]

    existing = existing or ()
    if slug not in existing:
        return slug
    n = 2
    while f"{slug}-{n}" in existing:
        n += 1
    return f"{slug}-{n}"


def parse_ref(key: str):
    """"lib:praise-english:days-of-elijah" -> ("praise-english","days-of-elijah"); else None. Validates both parts."""
    if not isinstance(key, str) or not key.startswith("lib:"):
        return None
    parts = key.split(":")
    if len(parts) != 3:
        return None
    _, collection, slug = parts
    if not _SLUG_RE.match(collection) or not _SLUG_RE.match(slug):
        return None
    return (collection, slug)
