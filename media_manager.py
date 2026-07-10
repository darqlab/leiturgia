"""
media_manager.py — Enumerate media files in media/images/ and media/videos/,
and compute storage-budget usage against them.

Public: list_media(), usage(), referenced_media().
"""

import json
import logging
import os
import shutil
from urllib.parse import quote as _quote, unquote as _unquote

logger = logging.getLogger('leiturgia.media')

try:
    from mutagen.mp4 import MP4 as _MP4
    _MUTAGEN_OK = True
except ImportError:
    _MUTAGEN_OK = False

MEDIA_ROOT   = "media"
IMAGES_DIR   = os.path.join(MEDIA_ROOT, "images")
VIDEOS_DIR   = os.path.join(MEDIA_ROOT, "videos")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".mov", ".avi"}

CONFIG_FILE = "config.json"
DATA_FILE   = os.path.join("data", "program.json")


def list_media() -> dict:
    """Return { "images": [...], "videos": [...] } with filename, URL, and metadata."""
    return {
        "images": _scan(IMAGES_DIR, IMAGE_EXTS, "images"),
        "videos": _scan(VIDEOS_DIR, VIDEO_EXTS, "videos"),
    }


def _fmt_size(n: int) -> str:
    for unit in ("KB", "MB", "GB"):
        n /= 1024
        if n < 1024:
            return f"{n:.1f} {unit}"
    return f"{n:.1f} GB"


def _fmt_duration(s: float) -> str:
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


def _file_meta(path: str) -> dict:
    size = os.path.getsize(path)
    duration = None
    duration_label = None
    if _MUTAGEN_OK and path.lower().endswith((".mp4", ".m4v")):
        try:
            duration = _MP4(path).info.length
            duration_label = _fmt_duration(duration)
        except Exception:
            pass
    return {
        "size":           size,
        "size_label":     _fmt_size(size),
        "duration":       duration,
        "duration_label": duration_label,
    }


def _scan(directory: str, allowed_exts: set, subdir: str) -> list:
    if not os.path.isdir(directory):
        return []
    files = []
    for name in sorted(os.listdir(directory)):
        ext = os.path.splitext(name)[1].lower()
        if ext in allowed_exts:
            full_path = os.path.join(directory, name)
            entry = {
                "name": name,
                "url":  f"/media/{subdir}/{_quote(name, safe='')}",
            }
            entry.update(_file_meta(full_path))
            files.append(entry)
    return files


def _load_config() -> dict:
    """Ad-hoc config.json read, same convention app.py uses elsewhere (no caching,
    changes apply without restart). Missing file/keys degrade to defaults."""
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _dir_used_bytes(directory: str) -> int:
    if not os.path.isdir(directory):
        return 0
    return sum(
        e.stat().st_size for e in os.scandir(directory) if e.is_file()
    )


def usage() -> dict:
    """Compute video/image storage usage against the configured budgets and the
    hard filesystem reserve. See development/tdd/modules/media-storage-budget.md
    §5.2 for the full spec."""
    cfg = _load_config()

    video_budget_bytes = int(float(cfg.get('media_video_budget_gb', 2)) * 1024 ** 3)
    image_budget_bytes = int(float(cfg.get('media_image_budget_gb', 1)) * 1024 ** 3)
    reserve_bytes       = int(float(cfg.get('media_disk_reserve_gb', 1)) * 1024 ** 3)
    warn_percent        = float(cfg.get('media_warn_percent', 80))

    used_bytes = _dir_used_bytes(VIDEOS_DIR)

    # shutil.disk_usage needs an existing path — fall back to MEDIA_ROOT, then cwd,
    # if VIDEOS_DIR doesn't exist yet (fresh install, no media uploaded).
    du_path = VIDEOS_DIR if os.path.isdir(VIDEOS_DIR) else (
        MEDIA_ROOT if os.path.isdir(MEDIA_ROOT) else "."
    )
    fs_free_bytes = shutil.disk_usage(du_path).free

    fs_room = fs_free_bytes - reserve_bytes
    if video_budget_bytes == 0:
        remaining_bytes = fs_room
        # Unlimited budget: percent/warn track the fs-reserve term instead — the
        # "effective budget" is whatever's already used plus the room still free
        # within the reserve floor.
        percent = _safe_percent(used_bytes, used_bytes + fs_room)
        # No budget term exists to compare against — warn is driven by percent
        # (against the reserve-derived "effective budget") alone.
        fs_reserve_binding = False
    else:
        remaining_bytes = min(video_budget_bytes - used_bytes, fs_room)
        percent = _safe_percent(used_bytes, video_budget_bytes)
        # The fs-reserve term is "binding" when it's the tighter of the two candidates.
        fs_reserve_binding = fs_room < (video_budget_bytes - used_bytes)

    full = remaining_bytes <= 0
    warn = full or percent >= warn_percent or fs_reserve_binding

    images_used_bytes = _dir_used_bytes(IMAGES_DIR)
    if image_budget_bytes == 0:
        images_remaining = fs_room
    else:
        images_remaining = min(image_budget_bytes - images_used_bytes, fs_room)
    images = {
        "used_bytes":    images_used_bytes,
        "budget_bytes":  image_budget_bytes,
        "full":          images_remaining <= 0,
        "used_label":    _fmt_size(images_used_bytes),
        "budget_label":  "Unlimited" if image_budget_bytes == 0 else _fmt_size(image_budget_bytes),
    }

    return {
        "used_bytes":      used_bytes,
        "budget_bytes":    video_budget_bytes,
        "remaining_bytes": remaining_bytes,
        "percent":         percent,
        "fs_free_bytes":   fs_free_bytes,
        "reserve_bytes":   reserve_bytes,
        "warn":            warn,
        "full":            full,
        "used_label":      _fmt_size(used_bytes),
        "budget_label":    "Unlimited" if video_budget_bytes == 0 else _fmt_size(video_budget_bytes),
        "images":          images,
    }


def _safe_percent(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round(part / whole * 100, 1)


def referenced_media() -> dict:
    """Scan data/program.json for items whose url points at a media/{videos,images}
    file, mapping basename -> [{program, item}, ...]. Read-only informational scan —
    a plain json.load is fine here (no migration/retry logic needed).
    See development/tdd/modules/media-storage-budget.md §5.3a."""
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        logger.warning("referenced_media: could not read %s", DATA_FILE, exc_info=True)
        return {}

    refs: dict = {}
    for sp in data.get("service_programs", []):
        program_label = sp.get("name", sp.get("id", ""))
        for item in sp.get("items", []):
            t = item.get('type', 'participant')
            is_video = (t == 'video') or (t == 'media' and item.get('media_type') == 'video')
            is_image = (t == 'image') or (t == 'media' and item.get('media_type') != 'video')
            if not (is_video or is_image):
                continue
            url = item.get('url', '')
            if not url:
                continue
            basename = _unquote(os.path.basename(url))
            item_label = item.get("title", item.get("part", ""))
            refs.setdefault(basename, []).append({
                "program": program_label,
                "item":    item_label,
            })
    return refs
