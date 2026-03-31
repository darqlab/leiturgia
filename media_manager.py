"""
media_manager.py — Enumerate media files in media/images/ and media/videos/.

Only list_media() is public.
"""

import os

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
                "url":  f"/media/{subdir}/{name}",
            }
            entry.update(_file_meta(full_path))
            files.append(entry)
    return files
